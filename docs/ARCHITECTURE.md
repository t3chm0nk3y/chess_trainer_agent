# Architecture
# Chess Trainer Agent

---

## Overview

The application follows a layered backend architecture with a planned React frontend. All chess analysis is performed server-side. The backend exposes a REST API consumed by the frontend.

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
│   │   ├── patterns.py      # Pattern CRUD
│   │   ├── progress.py      # Progress snapshots
│   │   └── workflows.py     # Workflow execution
│   ├── services/            # Business logic
│   │   ├── engine.py        # Stockfish integration
│   │   ├── pgn_parser.py    # PGN -> structured data
│   │   ├── classifier.py    # Move classification + phase detection
│   │   ├── claude_agent.py  # Claude API for annotation/synthesis
│   │   ├── pattern_engine.py # Pattern orchestration
│   │   ├── opening_analyzer.py # Opening stats computation
│   │   ├── lichess_api.py   # Lichess game fetching
│   │   └── mcp_client.py    # MCP abstraction (stubbed)
│   └── tasks/
│       └── analysis_worker.py # Background game analysis
├── workflow-mcp/
│   ├── server.py            # FastMCP server with tools
│   ├── models.py            # Workflow/WorkflowRun dataclasses
│   ├── store.py             # In-memory store + YAML loader
│   └── workflows/           # YAML workflow definitions
├── frontend/                # React app (dependencies only, no implementation)
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
  │    └─ Return {imported, skipped}
  │
  ├─ (Background) analysis_worker.analyze_game(game_id)
  │    │
  │    ├─ Fetch Game + Moves from DB
  │    ├─ For each move:
  │    │    ├─ engine.analyze_position(fen)  ← Stockfish eval
  │    │    ├─ classifier.detect_phase(fen)  ← Phase heuristic
  │    │    └─ classifier.classify_move(delta) ← best/good/inaccuracy/mistake/blunder
  │    ├─ Store evals + classifications on Move rows
  │    └─ Mark Game.analysis_status = "analyzed"
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

---

## Key Design Decisions

### Direct Stockfish vs MCP
The original design intended to use ChessAgine MCP for engine analysis. Phase 1 pivoted to direct Stockfish integration via `python-chess`'s `SimpleEngine` for simplicity. The `mcp_client.py` stub remains for future MCP-based features (themes, cloud eval).

### Synchronous Engine Analysis
`analysis_worker.py` runs Stockfish evaluations synchronously in a `ThreadPoolExecutor` (2 workers). This avoids async Stockfish complexity while keeping the FastAPI event loop unblocked.

### Two-Pass AI Analysis
Claude is used in two distinct passes:
1. **Per-game annotation** (`annotate_game_mistakes`) -- explains individual mistakes
2. **Cross-game synthesis** (`synthesize_patterns`) -- groups similar mistakes into named patterns

### Eval Delta Convention
`Move.eval_delta` stores the absolute centipawn loss (always >= 0). Higher values mean worse moves. The analysis worker computes this relative to the moving side's perspective.

---

## External Dependencies

| Dependency | Purpose | Connection |
|------------|---------|------------|
| Stockfish 18 | Position evaluation | Local binary via python-chess UCI |
| Claude API | Mistake annotation + pattern synthesis | HTTP via anthropic SDK |
| Lichess API | Game import | HTTP via httpx |
| SQLite | Data persistence | Local file via SQLAlchemy |

---

## Startup Sequence

`backend/main.py` defines a `lifespan` context manager that runs on app startup:

1. `init_db()` -- Create all tables via `Base.metadata.create_all()`
2. `seed_mistake_categories()` -- Populate `MistakeCategory` table if empty (2 top-level + 8 children)
3. On shutdown: `stockfish.close()` -- Terminate the Stockfish process
