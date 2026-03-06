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

Three Claude API call patterns for chess analysis.

### Functions

- **`annotate_game_mistakes(pgn, mistakes)`** -> `list[dict]`
  - Pass 1: Per-game annotation. Explains each mistake in context.
  - Input: Game PGN + list of mistake dicts (fen, san, best_move, eval_delta, phase)
  - Output: List of `{ply, annotation}` dicts
  - System prompt: Expert chess coach perspective

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
- Uses synchronous `client.messages.create()` (not async)
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

### Planned Integrations
- **ChessAgine MCP** -- Engine analysis with positional themes
- **Lichess MCP** -- Game import via MCP instead of direct API
- **Chess.com MCP** -- Game import
- **Memory MCP** -- Coaching context storage

### Notes
- This was the original design before direct Stockfish integration was chosen for Phase 1
- May be revisited for theme analysis or if MCP servers become available
