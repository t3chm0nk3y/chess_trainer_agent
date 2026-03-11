# Services
# Chess Trainer Agent

All services live in `backend/services/`. They contain business logic called by routers and tasks.

---

## engine.py -- Stockfish Integration

**Status: Complete**

Manages a persistent Stockfish process via `python-chess`'s `SimpleEngine.popen_uci()`.

### Key Components

- **`StockfishEngine`** -- Singleton class wrapping the engine process
  - `analyze_position(fen, depth)` -> `EngineEval` -- Analyze one position
  - `analyze_game_positions(fens, depth)` -> `list[EngineEval]` -- Batch analysis
  - `close()` -- Terminate the process

- **`EngineEval`** -- Dataclass result
  - `score_cp`: Float centipawns from white's perspective
  - `best_move`: UCI string of best move
  - `mate_in`: Moves to mate (if applicable)
  - `pv`: Principal variation (up to 5 moves)

### Configuration
- `STOCKFISH_PATH` env var (default: "stockfish")
- `ENGINE_DEPTH` env var (default: 20)

### Notes
- Engine is lazily initialized on first use
- Mate scores are represented as +/- 10000 centipawns
- Errors on individual positions return `EngineEval(score_cp=0.0)` rather than failing the batch

---

## pgn_parser.py -- PGN Parsing

**Status: Complete**

Parses PGN text into structured `ParsedGame` / `ParsedMove` objects using `python-chess`.

### Key Functions

- **`parse_pgn(pgn_text)`** -> `list[ParsedGame]` -- Parse multi-game PGN text
- **`_parse_single_game(game, raw_pgn)`** -> `ParsedGame` -- Parse one game

### Data Structures

- **`ParsedGame`**: pgn, white, black, result, date_played, opening_eco, opening_name, moves
- **`ParsedMove`**: move_number, ply, san, uci, fen_before, fen_after

### Notes
- Handles the standard PGN date format `YYYY.MM.DD` including partial dates
- Exports clean PGN (no variations or comments) via `StringExporter`
- Ply is 0-indexed; move_number is 1-indexed chess convention

---

## classifier.py -- Move Classification

**Status: Complete**

Classifies moves based on engine eval delta and detects game phase from board state.

### Key Functions

- **`classify_move(eval_delta)`** -> `str | None` -- Classify by centipawn loss
- **`detect_phase(fen)`** -> `str` -- Determine opening/middlegame/endgame

### Thresholds (centipawns)
| Classification | Max Delta |
|----------------|-----------|
| best | 10 |
| good | 30 |
| inaccuracy | 70 |
| mistake | 150 |
| blunder | > 150 |

### Phase Detection Heuristic
Counts non-pawn, non-king pieces (RNBQ) in the FEN:
- **Opening**: move_number <= 15 AND pieces >= 10
- **Endgame**: pieces <= 6
- **Middlegame**: everything else

---

## claude_agent.py -- Claude AI Integration

**Status: Complete**

Four Claude API call patterns for chess analysis.

### Functions

- **`annotate_game_mistakes(pgn, mistakes)`** -> `list[dict]`
  - Pass 1: Per-game annotation. Explains each mistake in context.
  - Input: Game PGN + list of mistake dicts (fen, san, best_move, eval_delta, phase)
  - Output: List of `{ply, annotation}` dicts
  - System prompt: Expert chess coach perspective

- **`classify_mistakes_batch(mistakes)`** -> `list[str | None]`
  - Batch classification: classifies multiple mistakes in a single Claude call.
  - Input: List of dicts with keys: fen, san, best_move_uci, eval_delta, phase
  - Output: List of "tactical" | "strategic" | None, one per input
  - Synchronous (not async)

- **`classify_mistake_type(fen, san, best_move_uci, eval_delta, phase)`** -> `str | None`
  - Single-move classification (tactical/strategic). Synchronous.

- **`synthesize_patterns(game_mistakes, existing_patterns)`** -> `list[dict]`
  - Pass 2: Cross-game synthesis. Groups similar mistakes into named patterns.
  - Input: All mistakes across analyzed games + existing patterns for diffing
  - Output: List of pattern dicts (label, description, category, severity_score, frequency, example_game_ids, training_recommendation)
  - Max tokens: 8192

- **`compare_new_game(new_game_mistakes, known_patterns)`** -> `dict`
  - Matches a new game's mistakes against existing patterns.
  - Output: `{matched_patterns, new_patterns, delta_summary}`

### Configuration
- `ANTHROPIC_API_KEY` env var
- `CLAUDE_MODEL` env var (default: "claude-sonnet-4-20250514")

### Notes
- Uses synchronous `client.messages.create()` for classification
- All responses are expected as JSON; parse failures return empty results
- The anthropic SDK is initialized at module level as a singleton

---

## pattern_engine.py -- Pattern Orchestration

**Status: Complete**

Coordinates pattern synthesis and matching workflows.

### Functions

- **`gather_game_mistakes(db, game_id=None)`** -> `list[dict]`
  - Collects all moves classified as inaccuracy/mistake/blunder
  - Optional game_id filter for single-game queries

- **`run_pattern_synthesis(db, min_games=5)`** -> `list[dict]`
  - Requires at least `min_games` analyzed games before running
  - Gathers all mistakes, fetches existing unresolved patterns, calls Claude synthesis
  - Returns new/updated pattern dicts

- **`match_game_to_patterns(db, game_id)`** -> `dict`
  - Compares one game's mistakes against all active patterns via Claude

- **`create_progress_snapshot(db)`** -> `ProgressSnapshot`
  - Creates a point-in-time snapshot of accuracy and pattern data
  - Accuracy = % of classified moves that are "best" or "good"

---

## opening_analyzer.py -- Opening Statistics

**Status: Complete**

Computes per-opening win/loss/draw stats with divergence detection.

### Functions

- **`compute_opening_stats(db)`** -> `list[OpeningStats]`
  - Aggregates all analyzed games by ECO code + opening name + variation
  - Computes wins/losses/draws, average centipawn loss, divergence move
  - Clears and rebuilds all OpeningStats rows on each call

- **`get_opening_stats_ranked(db, sort_by)`** -> `list[dict]`
  - Returns stats sorted by loss_pct, total_games, or avg_cp_loss

- **`get_opening_detail(db, eco_code)`** -> `dict | None`
  - Drill-down: all variation lines for an ECO code with game lists

### Helper Functions
- `_player_result(game)` -- Determine win/loss/draw from player's perspective
- `_extract_opening_key(game)` -- Parse "Opening: Variation" into components
- `_get_opening_moves(db, game_id)` -- Get SAN moves from opening phase
- `_compute_opening_cp_loss(db, game_id, player_color)` -- Average CP loss for player's opening moves
- `_longest_common_prefix(sequences)` -- Find common opening move sequence
- `_find_divergence_move(db, games, move_sequences)` -- Compare won vs lost game move sequences

---

## mistake_reporter.py -- Mistake Reporting

**Status: Complete**

Categorized mistake analysis and trend computation.

### Functions

- **`get_mistake_matrix(db, game_id=None)`** -> `dict`
  - Builds a phase x type matrix: `[phase][type] -> {count, examples}`
  - Phases: opening, middlegame, endgame
  - Types: tactical, strategic, unclassified
  - Returns matrix, phase_totals, type_totals, total_mistakes

- **`get_repeated_mistakes(db, min_frequency=2)`** -> `list[dict]`
  - Returns unresolved patterns with frequency >= min_frequency, ordered by frequency desc
  - Includes acknowledgment_status: "new", "acknowledged", or "recurring"

- **`get_mistake_trends(db, period_games=10)`** -> `dict`
  - Compares accuracy of the most recent `period_games` vs older games
  - Per-phase breakdown with delta and improving flag

---

## workflow_executor.py -- Workflow Engine

**Status: Complete**

Loads YAML workflow definitions from `workflow-mcp/workflows/`, resolves templates, and executes steps sequentially via a tool registry.

### Key Functions

- **`get_workflows()`** -> `dict[str, dict]` -- Cached YAML definitions
- **`execute_workflow(db, workflow_name, params)`** -> `dict` -- Execute a full workflow
- **`resolve_template(template, params, step_results)`** -- Resolve `{{ variable }}` and `{{ step_N.field }}` templates

### Architecture
- YAML files loaded from `workflow-mcp/workflows/` at startup (cached)
- `{{ variable }}` syntax for parameter interpolation
- `{{ step_N.field }}` syntax for referencing previous step results
- Creates a `WorkflowRun` DB record to persist execution history

### Tool Registry (28 handlers)
Maps YAML tool names to Python handler functions. Categories:
- `database.*` -- DB fetch/store operations (fetch_game, fetch_patterns, store_analysis, etc.)
- `chessagine.analyze_game` -- Delegates to analysis_worker
- `classifier.*` -- Move classification (passthrough, handled by analysis_worker)
- `claude.*` -- Claude API calls (annotate, compare, synthesize)
- `pattern_engine.*` -- Pattern aggregation and diffing
- `progress.*` -- Accuracy calculation, snapshot creation, trend identification
- `workflow.execute` -- Sub-workflow composition
- `lichess_mcp.export_games` -- Lichess API fetch
- `pgn_parser.parse` -- PGN parsing

---

## chat_service.py -- Chat Agent

**Status: Complete**

Agentic chat loop using Claude's tool-use API with SSE streaming.

### Key Function

- **`chat_stream(messages, db)`** -- Generator yielding SSE event dicts

### Architecture
- Uses `client.messages.stream()` for real-time text streaming
- Agentic loop: up to 10 tool-use rounds per request
- System prompt: Expert chess coach persona
- Event types: `text_delta`, `tool_call`, `tool_result`, `done`, `error`

---

## chat_tools.py -- Chat Tool Registry

**Status: Complete**

Registers 13 tools that the chat agent can call to query the database.

### Registration Pattern
```python
register_tool(name, description, input_schema, handler)
```

### Registered Tools
| Tool | Description |
|------|-------------|
| `list_games` | List analyzed games with filters (source, opening, color, result) |
| `get_game_detail` | Full game with all moves and evals |
| `get_openings_ranked` | Openings ranked by loss percentage |
| `get_opening_detail` | Drill-down by ECO code |
| `get_patterns` | Active weakness patterns |
| `get_pattern_detail` | Pattern with all instance moves |
| `get_mistake_matrix` | Phase x type mistake breakdown |
| `get_repeated_mistakes` | Recurring patterns by frequency |
| `get_accuracy_trends` | Recent vs older accuracy by phase |
| `get_progress_summary` | Overall stats and pattern counts |
| `get_sessions` | Play sessions grouped by date |
| `get_progress_comparison` | Recent vs older game comparison |
| `get_recent_notifications` | Latest game's pattern matches |

---

## lichess_api.py -- Lichess Game Import

**Status: Complete**

Direct HTTP client for the Lichess API using httpx.

### Functions

- **`fetch_games(username, since, max_games, color, rated, time_control)`** -> `str`
  - Fetches games as PGN text from `https://lichess.org/api/games/user/{username}`
  - Supports filtering by date, color, rated status, time control
  - Returns raw PGN text
  - Timeout: 300 seconds (for large game histories)

### Notes
- Uses `LICHESS_TOKEN` for authentication (optional but recommended)
- Requests opening tags in PGN headers
- Does not request clock data or server-side evals

---

## mcp_client.py -- MCP Abstraction Layer

**Status: Stubbed**

Intended abstraction for MCP server communication. All methods raise `NotImplementedError` or return `None`.

### Notes
- This was the original design before direct Stockfish integration was chosen for Phase 1
- May be revisited for theme analysis or if MCP servers become available
