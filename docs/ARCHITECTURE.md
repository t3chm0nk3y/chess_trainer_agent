# Architecture
# Chess Trainer Agent

---

## Overview

The application follows a layered backend architecture with a React 19 frontend. All chess analysis is performed server-side. The backend exposes a REST API consumed by the frontend.

---

## Directory Structure

```
chess_trainer_agent/
├── backend/
│   ├── main.py              # FastAPI app, lifespan, router mounting
│   ├── config.py            # Settings from environment variables
│   ├── database.py          # SQLAlchemy engine, session factory, Base
│   ├── models.py            # ORM models (9 tables)
│   ├── seed.py              # Initial mistake taxonomy seeder
│   ├── routers/             # API endpoint handlers
│   │   ├── games.py         # Game CRUD, import, PGN upload
│   │   ├── openings.py      # Opening line statistics
│   │   ├── analysis.py      # Analysis job management
│   │   ├── patterns.py      # Pattern CRUD + acknowledgment
│   │   ├── reports.py       # Mistake matrix, repeated, trends
│   │   ├── notifications.py # Game-level pattern notifications
│   │   ├── progress.py      # Progress snapshots, sessions, compare
│   │   ├── workflows.py     # Workflow execution
│   │   └── chat.py          # Chat agent SSE endpoint
│   ├── services/            # Business logic
│   │   ├── engine.py        # Stockfish integration
│   │   ├── pgn_parser.py    # PGN -> structured data
│   │   ├── classifier.py    # Move classification + phase detection
│   │   ├── claude_agent.py  # Claude API for annotation/synthesis/classification
│   │   ├── pattern_engine.py # Pattern orchestration
│   │   ├── opening_analyzer.py # Opening stats computation
│   │   ├── mistake_reporter.py # Mistake matrix, repeated, trends
│   │   ├── workflow_executor.py # YAML workflow engine
│   │   ├── chat_service.py  # Agentic chat loop with tool-use
│   │   ├── chat_tools.py    # 13 registered chat tools
│   │   ├── lichess_api.py   # Lichess game fetching
│   │   └── mcp_client.py    # MCP abstraction (stubbed)
│   └── tasks/
│       └── analysis_worker.py # Background game analysis
├── workflow-mcp/
│   ├── server.py            # FastMCP server with tools
│   ├── models.py            # Workflow/WorkflowRun dataclasses
│   ├── store.py             # In-memory store + YAML loader
│   └── workflows/           # YAML workflow definitions
├── frontend/                # React 19 + Vite app
│   └── src/
│       ├── App.jsx          # Main app with tab navigation
│       ├── api/client.js    # API client
│       ├── components/      # ChessBoard, EvalBar, MoveList, etc.
│       └── pages/           # AnalysisTab, ReportTab, OpeningsTab, etc.
├── tests/                   # pytest test suite
├── docs/                    # Project documentation
├── pyproject.toml           # Build config and dependencies
└── requirements.txt         # Flat dependency list
```

---

## Component Relationships

### Request Flow: Game Import + Analysis

```
Client
  │
  ├─ POST /api/games/import/lichess?username=X
  │    │
  │    ├─ lichess_api.fetch_games()     ← HTTP to Lichess API
  │    ├─ pgn_parser.parse_pgn()        ← python-chess PGN parsing
  │    ├─ games._store_parsed_games()   ← Deduplicate + persist to DB
  │    ├─ queue_analysis(game_id)       ← Auto-queue each new game
  │    └─ Return {imported, skipped}
  │
  ├─ (Background) analysis_worker._analyze_game_sync(game_id)
  │    │
  │    ├─ 1. Fetch Game + Moves from DB
  │    ├─ 2. For each move:
  │    │    ├─ engine.analyze_position(fen)  ← Stockfish eval
  │    │    ├─ classifier.detect_phase(fen)  ← Phase heuristic
  │    │    └─ classifier.classify_move(delta) ← best/good/inaccuracy/mistake/blunder
  │    ├─ 3. Store evals + classifications on Move rows
  │    ├─ 4. classify_mistakes_batch()      ← Claude: tactical/strategic
  │    ├─ 5. _match_patterns()              ← Link moves to known patterns
  │    ├─ 6. _auto_resolve_patterns()       ← Resolve old patterns
  │    └─ 7. Mark Game.analysis_status = "analyzed"
  │
  └─ GET /api/games/{id}
       └─ Return game with annotated moves
```

### Request Flow: Pattern Synthesis

```
Client
  │
  ├─ POST /api/patterns/refresh
  │    │
  │    ├─ pattern_engine.run_pattern_synthesis()
  │    │    ├─ gather_game_mistakes()     ← Query Moves where classification in (mistake, blunder)
  │    │    ├─ claude_agent.synthesize_patterns()  ← Claude API call
  │    │    └─ Return pattern dicts
  │    └─ Store/update Pattern rows
  │
  └─ GET /api/patterns
       └─ Return patterns sorted by severity
```

### Request Flow: Chat Agent

```
Client
  │
  └─ POST /api/chat/stream  (SSE)
       │
       ├─ chat_service.chat_stream()
       │    ├─ Claude messages.stream() with 13 tools
       │    ├─ Agentic loop (up to 10 rounds):
       │    │    ├─ Stream text deltas to client
       │    │    ├─ Execute tool calls (chat_tools.execute_tool)
       │    │    └─ Feed results back to Claude
       │    └─ Return final response
       │
       └─ Tools query DB directly:
            list_games, get_game_detail, get_openings_ranked,
            get_opening_detail, get_patterns, get_pattern_detail,
            get_mistake_matrix, get_repeated_mistakes,
            get_accuracy_trends, get_progress_summary,
            get_sessions, get_progress_comparison,
            get_recent_notifications
```

---

## Key Design Decisions

### Direct Stockfish vs MCP
The original design intended to use ChessAgine MCP for engine analysis. Phase 1 pivoted to direct Stockfish integration via `python-chess`'s `SimpleEngine` for simplicity. The `mcp_client.py` stub remains for future MCP-based features (themes, cloud eval).

### Synchronous Engine Analysis
`analysis_worker.py` runs Stockfish evaluations synchronously in a `ThreadPoolExecutor` (2 workers). This avoids async Stockfish complexity while keeping the FastAPI event loop unblocked.

### Three-Pass AI Analysis
Claude is used in three distinct passes:
1. **Per-game annotation** (`annotate_game_mistakes`) -- explains individual mistakes
2. **Batch classification** (`classify_mistakes_batch`) -- classifies each mistake as tactical/strategic
3. **Cross-game synthesis** (`synthesize_patterns`) -- groups similar mistakes into named patterns

### Workflow Executor (not MCP Client)
Rather than connecting to the workflow MCP server as a client, the backend implements its own `workflow_executor.py` that loads YAML definitions directly, resolves `{{ }}` templates, and dispatches steps via a tool registry of 28 handlers. This avoids MCP transport complexity.

### Chat Agent
The chat endpoint uses Claude's tool-use API in an agentic loop. 13 registered tools give the agent read-only access to all data sources (games, openings, patterns, reports, progress). Responses stream via SSE.

### Chess.com Import Dropped
Chess.com import (task 6.2) was dropped in favor of Lichess-only focus.

### Auto-Resolution of Patterns
Patterns not seen in the last N analyzed games (configurable via `AUTO_RESOLVE_GAMES`, default 10) are automatically marked as resolved.

### Eval Delta Convention
`Move.eval_delta` stores the absolute centipawn loss (always >= 0). Higher values mean worse moves. The analysis worker computes this relative to the moving side's perspective.

---

## External Dependencies

| Dependency | Purpose | Connection |
|------------|---------|------------|
| Stockfish 18 | Position evaluation | Local binary via python-chess UCI |
| Claude API | Annotation, classification, synthesis, chat | HTTP via anthropic SDK |
| Lichess API | Game import | HTTP via httpx |
| SQLite | Data persistence | Local file via SQLAlchemy |

---

## Startup Sequence

`backend/main.py` defines a `lifespan` context manager that runs on app startup:

1. `init_db()` -- Create all tables via `Base.metadata.create_all()`
2. `seed_mistake_categories()` -- Populate `MistakeCategory` table if empty (2 top-level + 8 children)
3. Mount 9 routers with CORS middleware (origins: localhost:5173, localhost:3000)
4. On shutdown: `stockfish.close()` -- Terminate the Stockfish process
