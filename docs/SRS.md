# Software Requirements Specification
# Chess Trainer Agent — v2.0
**Date:** 2026-03-10
**Status:** Authoritative — supersedes all prior SRS versions and addenda

---

## 0. Instructions for Claude Code

1. Read this document fully before writing a single line of code
2. Implement phases in order — do not begin Phase N+1 until Phase N is verified complete
3. Implement only what is specified here — no extra features, no assumptions
4. When in doubt: do less, not more
5. Consult `reference/` for reusable UI components (chessboard, opening row display) but start the backend and data model completely fresh
6. The YAML pattern registry is the single source of truth for all pattern definitions — never hardcode pattern names, IDs, or descriptions in application logic

---

## 1. Problem Statement

The player wants to understand why they keep losing. The app must answer three questions:

1. **What mistakes did I make in this game, and have I made them before?**
2. **Which opening lines keep costing me games, and where do they go wrong?**
3. **What recurring game situations am I consistently losing from?**

All three require a reliable foundation: every game fully analyzed, every mistake classified against a known registry, every pattern tracked across time. **Data completeness and registry consistency are the primary design constraints.**

---

## 2. Core Architectural Principles

These principles govern every design decision in this document.

### 2.1 The Registry Is the Contract
Every tactic, pattern, and game condition the system is capable of detecting is defined in `registry/patterns.yaml`. Nothing is detected that isn't in the registry. Nothing in the registry is hardcoded in application logic. When a new pattern is added to the registry, the system can find it in historical games without re-running the chess engine.

### 2.2 The Game Object Grows Over Time
A game record is not a snapshot — it is a persistent, enriched object that accumulates analysis layers. Engine evaluation runs once and is stored permanently. All classification and pattern matching is derived from stored engine data and can be re-run at any time against current registry contents.

### 2.3 Engine Data Is Immutable
Once Stockfish has evaluated a game, that data (cp_eval, cp_loss, best_move, mistake_severity per move) is never modified or deleted. It is the raw material all other analysis is derived from.

### 2.4 Classification Is Append-Only
When new patterns are added to the registry, only unmatched moves are re-scanned. Existing pattern matches on a move are never removed or replaced. A move can accumulate multiple pattern matches over time.

### 2.5 Scan Tracking Enables Targeted Re-analysis
For every (game, registry_pattern_id) pair, the system maintains a record of whether that game has been scanned for that pattern. When a new pattern is added, only games with no scan record for that pattern are queued for re-analysis — no full pipeline restart required.

---

## 3. Scope — v1

### In Scope
- Lichess game import (full history, deduplicated)
- Local Stockfish engine analysis (every move, runs once, stored permanently)
- Pattern registry (YAML, human-editable, version-controlled)
- Append-only move-level mistake classification (engine + Claude AI)
- Game condition detection (structural patterns, runs once per game per condition)
- Scan log tracking (per game per pattern)
- Opening line statistics with divergence move detection
- Analysis pipeline with stage tracking, retry on failure
- Targeted re-analysis when registry changes (no engine re-run)
- REST API (FastAPI, JSON)
- React frontend — three pages: Game View, Openings, Patterns
- SQLite database

### Out of Scope — v1
- Chess.com import
- Acknowledgment / resolution system
- Progress tracking over time
- User authentication
- MCP integration of any kind

---

## 4. Project Structure

```
chess-trainer/
├── main.py                        # FastAPI app, router registration, scheduler startup
├── config.py                      # All configuration via environment variables
├── database.py                    # SQLAlchemy async setup, session factory
├── models.py                      # All ORM models — single file
│
├── registry/
│   └── patterns.yaml              # THE pattern registry — only place patterns are defined
│
├── services/
│   ├── lichess.py                 # Lichess API client — game import
│   ├── stockfish.py               # Stockfish subprocess wrapper — position evaluation
│   ├── classifier.py              # Phase assignment, severity thresholds, condition detection
│   ├── annotator.py               # Claude API — per-mistake pattern classification
│   ├── scanner.py                 # Registry scan orchestration — targeted re-analysis logic
│   └── opening_stats.py           # Opening line aggregation and statistics
│
├── pipeline/
│   ├── worker.py                  # Analysis pipeline — stage execution
│   └── retry.py                   # APScheduler job — retries failed/stuck games
│
├── routers/
│   ├── games.py                   # /api/games
│   ├── analysis.py                # /api/analysis
│   ├── patterns.py                # /api/patterns
│   ├── openings.py                # /api/openings
│   └── admin.py                   # /api/admin
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js                 # All backend fetch calls — single file
│       ├── components/
│       │   ├── ChessBoard.jsx     # From reference/ — reuse as-is
│       │   ├── MoveList.jsx       # Move list with severity highlights
│       │   ├── MistakePanel.jsx   # Game mistakes + recurring patterns panel
│       │   ├── OpeningRow.jsx     # Opening line row with inline moves — from reference/
│       │   └── PatternCard.jsx    # Pattern summary card
│       └── pages/
│           ├── GameView.jsx       # Chessboard + analysis panel
│           ├── Openings.jsx       # Opening lines table
│           └── Patterns.jsx       # Recurring patterns + game conditions
│
└── tests/
    ├── test_pipeline.py
    ├── test_classifier.py
    ├── test_scanner.py
    └── test_opening_stats.py
```

---

## 5. Configuration (config.py)

All configuration via environment variables. Nothing hardcoded.

```
STOCKFISH_PATH          required — absolute path to local Stockfish binary
LICHESS_TOKEN           required — Lichess API personal access token
LICHESS_USERNAME        required — Lichess username whose games are imported
ANTHROPIC_API_KEY       required — Anthropic API key for Claude
DATABASE_URL            default: sqlite+aiosqlite:///./chess_trainer.db
STOCKFISH_DEPTH         default: 18
CP_LOSS_INACCURACY      default: 50
CP_LOSS_MISTAKE         default: 100
CP_LOSS_BLUNDER         default: 200
REGISTRY_PATH           default: registry/patterns.yaml
MAX_RETRIES             default: 5
RETRY_INTERVAL_SECONDS  default: 300
```

---

## 6. Data Model (models.py)

All models in a single file. Relationships defined explicitly.

### 6.1 Game

The central object. Grows over time as analysis layers are added.

```python
class Game(Base):
    __tablename__ = "games"

    id: int                          # PK
    lichess_id: str                  # UNIQUE — deduplication key
    pgn: str                         # raw PGN, stored permanently
    player_color: str                # "white" | "black"
    opponent_username: str | None
    result: str                      # "win" | "loss" | "draw"
    played_at: datetime
    eco_code: str | None
    opening_name: str | None
    variation_name: str | None
    time_control: str | None
    total_moves: int | None

    # Engine layer status — set once, never modified after ENGINE_COMPLETE
    engine_status: str               # "pending" | "running" | "complete" | "failed"
    engine_completed_at: datetime | None
    engine_failure_reason: str | None
    engine_failure_count: int        # default 0
    engine_next_retry_at: datetime | None

    # Classification layer status — tracks annotation progress
    annotation_status: str           # "pending" | "running" | "complete" | "failed"
    annotation_completed_at: datetime | None

    # Condition layer status — tracks game condition detection
    condition_status: str            # "pending" | "running" | "complete" | "failed"
    condition_completed_at: datetime | None

    # Registry tracking — which registry version was current at last full scan
    registry_version_at_last_scan: str | None
    has_unscanned_patterns: bool     # default False — set True when new patterns added
```

**Invariant:** `engine_status = "complete"` is a prerequisite for all other layers. Once set to complete, engine fields on Move records are never modified.

### 6.2 Move

One record per move. Engine fields are written once and immutable.

```python
class Move(Base):
    __tablename__ = "moves"

    id: int                          # PK
    game_id: int                     # FK -> Game
    move_number: int
    color: str                       # "white" | "black"
    san: str
    fen_before: str
    fen_after: str
    phase: str                       # "opening" | "middlegame" | "endgame"

    # Engine fields — immutable after engine_status = complete
    cp_eval_before: float | None
    cp_eval_after: float | None
    cp_loss: float | None            # positive = bad for the player
    best_move_san: str | None
    mistake_severity: str | None     # "inaccuracy" | "mistake" | "blunder" | None

    # Relationships
    pattern_matches: list[MovePatternMatch]  # all pattern matches accumulated over time
```

### 6.3 MovePatternMatch

Append-only. Each record links a move to one pattern classification. A move may accumulate multiple records over time as the registry grows.

```python
class MovePatternMatch(Base):
    __tablename__ = "move_pattern_matches"

    id: int                          # PK
    move_id: int                     # FK -> Move
    game_id: int                     # FK -> Game (denormalized for query performance)
    registry_pattern_id: str         # e.g. "MT-001" — references patterns.yaml
    annotation: str                  # Claude's explanation, max 80 words
    matched_at: datetime
    registry_version_at_match: str   # version of patterns.yaml when match was made

    # UNIQUE constraint: (move_id, registry_pattern_id)
    # A move can only match a given pattern once
```

### 6.4 PatternScanLog

Tracks whether a given game has been scanned for a given pattern. This is what enables targeted re-analysis when new patterns are added — only games with no scan record for the new pattern are queued.

```python
class PatternScanLog(Base):
    __tablename__ = "pattern_scan_log"

    id: int                          # PK
    game_id: int                     # FK -> Game
    registry_pattern_id: str         # e.g. "MT-001"
    scanned_at: datetime
    result: str                      # "matched" | "no_match"
    match_count: int                 # number of moves matched (0 if no_match)

    # UNIQUE constraint: (game_id, registry_pattern_id)
    # One scan record per game per pattern
```

### 6.5 Pattern

A confirmed recurring problem — built up across games. Created when a pattern is seen for the first time; frequency incremented on each subsequent match.

```python
class Pattern(Base):
    __tablename__ = "patterns"

    id: int                          # PK
    registry_pattern_id: str         # UNIQUE — e.g. "MT-001"
    phase: str                       # from registry
    axis: str                        # from registry
    name: str                        # from registry
    frequency: int                   # total occurrences across all games
    games_affected: int              # number of distinct games this appeared in
    first_seen_at: datetime
    last_seen_at: datetime
    first_seen_game_id: int          # FK -> Game
    last_seen_game_id: int           # FK -> Game
    example_fen: str | None          # clearest example position FEN
    example_annotation: str | None   # annotation from clearest example
```

### 6.6 GameCondition

A structural pattern detected at the whole-game level. Append-only — new conditions can be added to the registry and detected in existing games without engine re-analysis.

```python
class GameCondition(Base):
    __tablename__ = "game_conditions"

    id: int                          # PK
    game_id: int                     # FK -> Game
    registry_pattern_id: str         # e.g. "GC-001"
    condition_name: str
    detected_at_move: int | None
    player_was_worse: bool           # was player already losing when condition arose?
    game_result: str                 # "win" | "loss" | "draw" — copied for aggregation
    context_note: str | None

    # UNIQUE constraint: (game_id, registry_pattern_id)
    # A game can only have a given condition recorded once
```

### 6.7 OpeningStats

```python
class OpeningStats(Base):
    __tablename__ = "opening_stats"

    id: int                          # PK
    eco_code: str
    opening_name: str
    variation_name: str | None
    total_games: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    loss_rate: float
    avg_cp_loss_opening: float | None
    divergence_move: int | None
    divergence_san: str | None
    last_computed_at: datetime

    # UNIQUE constraint: (eco_code, opening_name, variation_name)
```

---

## 7. Pattern Registry (registry/patterns.yaml)

### 7.1 Purpose and Rules

- This file is the only place pattern definitions live
- It is version-controlled alongside the codebase
- It is human-editable — no UI required to add a pattern
- Application code reads it at startup and on explicit reload
- **Never hardcode a pattern ID, name, or description in Python code**
- The `registry_version` string must be incremented when patterns are added or modified

### 7.2 Schema

```yaml
registry_version: "1.0"
last_updated: "2026-03-10"

patterns:
  - id: "MT-001"           # unique, immutable once published
    phase: "middlegame"    # opening | middlegame | endgame | all
    axis: "tactical"       # tactical | strategic | opening_line | game_condition
    name: "Missed Fork"
    description: "Failed to execute or see a fork opportunity"
    detection_method: "hybrid"   # engine | ai | hybrid | statistical
    cp_loss_min: 200             # minimum cp_loss to consider this pattern
    active: true                 # false = skip during all scanning
```

**ID prefix conventions — follow strictly when adding patterns:**

| Prefix | Meaning |
|---|---|
| OT | Opening — Tactical |
| OS | Opening — Strategic |
| OL | Opening Line (statistical) |
| MT | Middlegame — Tactical |
| MS | Middlegame — Strategic |
| ET | Endgame — Tactical |
| ES | Endgame — Strategic |
| GC | Game Condition |

**Adding a new pattern:**
1. Add entry to `patterns.yaml` with a new unique ID following prefix conventions
2. Increment `registry_version` (e.g. "1.0" → "1.1")
3. Update `last_updated`
4. Call `POST /api/admin/registry/reload` — the system will automatically identify all games with no scan record for the new pattern and queue them for targeted re-analysis

### 7.3 Initial Registry — Complete List

```yaml
registry_version: "1.0"
last_updated: "2026-03-10"

patterns:

  # ── OPENING TACTICAL ──────────────────────────────────────────────────────
  - { id: OT-001, phase: opening, axis: tactical,  detection_method: engine,  cp_loss_min: 200, active: true,
      name: "Hung Piece in Opening",
      description: "Left a piece en prise during the opening phase" }

  - { id: OT-002, phase: opening, axis: tactical,  detection_method: hybrid,  cp_loss_min: 150, active: true,
      name: "Premature Attack Refuted",
      description: "An early attack that loses material or tempo when correctly met" }

  - { id: OT-003, phase: opening, axis: tactical,  detection_method: hybrid,  cp_loss_min: 150, active: true,
      name: "Failed Opening Combination",
      description: "An attempted tactical sequence in the opening that does not work" }

  - { id: OT-004, phase: opening, axis: tactical,  detection_method: engine,  cp_loss_min: 150, active: true,
      name: "Missed Opponent Tactic",
      description: "Failed to respond to opponent's tactical threat in the opening" }

  - { id: OT-005, phase: opening, axis: tactical,  detection_method: hybrid,  cp_loss_min: 100, active: true,
      name: "Wrong Recapture",
      description: "Recaptured with the wrong piece, allowing a fork or pin" }

  # ── OPENING STRATEGIC ─────────────────────────────────────────────────────
  - { id: OS-001, phase: opening, axis: strategic, detection_method: ai,      cp_loss_min: 50,  active: true,
      name: "Premature Pawn Push",
      description: "A pawn push that weakens key squares before development is complete" }

  - { id: OS-002, phase: opening, axis: strategic, detection_method: ai,      cp_loss_min: 50,  active: true,
      name: "Delayed Castling",
      description: "Failed to castle when king safety required it" }

  - { id: OS-003, phase: opening, axis: strategic, detection_method: ai,      cp_loss_min: 30,  active: true,
      name: "Redundant Piece Move",
      description: "Moved the same piece twice in the opening without compensation" }

  - { id: OS-004, phase: opening, axis: strategic, detection_method: ai,      cp_loss_min: 30,  active: true,
      name: "Poor Development Order",
      description: "Developed pieces in a suboptimal order, ceding initiative" }

  - { id: OS-005, phase: opening, axis: strategic, detection_method: ai,      cp_loss_min: 50,  active: true,
      name: "Ignored Center Control",
      description: "Conceded the center without compensation" }

  - { id: OS-006, phase: opening, axis: strategic, detection_method: ai,      cp_loss_min: 50,  active: true,
      name: "Early Queen Sortie Backfires",
      description: "Moved the queen early and lost tempo being chased back" }

  - { id: OS-007, phase: opening, axis: strategic, detection_method: engine,  cp_loss_min: 80,  active: true,
      name: "Bad Opening Deviation",
      description: "Deviated from a known good continuation with an objectively worse move" }

  # ── OPENING LINE (statistical — computed by opening_stats.py, not annotator) ──
  - { id: OL-001, phase: opening, axis: opening_line, detection_method: statistical, cp_loss_min: 0, active: true,
      name: "Consistent Losses After Move N",
      description: "Loss rate >= 60% in a specific line after a particular move number" }

  - { id: OL-002, phase: opening, axis: opening_line, detection_method: statistical, cp_loss_min: 0, active: true,
      name: "Repeated Divergence Point",
      description: "Consistently plays the same inferior move at a known choice point" }

  # ── MIDDLEGAME TACTICAL ───────────────────────────────────────────────────
  - { id: MT-001, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 200, active: true,
      name: "Missed Fork",
      description: "Failed to execute or see a fork opportunity" }

  - { id: MT-002, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 150, active: true,
      name: "Missed Pin",
      description: "Failed to exploit or missed a pin" }

  - { id: MT-003, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 150, active: true,
      name: "Missed Skewer",
      description: "Failed to execute or missed a skewer" }

  - { id: MT-004, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 300, active: true,
      name: "Missed Back-Rank Mate",
      description: "Failed to see or execute a back-rank mating pattern" }

  - { id: MT-005, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 200, active: true,
      name: "Missed Discovered Attack",
      description: "Failed to execute a discovered attack" }

  - { id: MT-006, phase: middlegame, axis: tactical, detection_method: engine, cp_loss_min: 200, active: true,
      name: "Hung Piece",
      description: "Left a piece undefended in the middlegame" }

  - { id: MT-007, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 150, active: true,
      name: "Missed Zwischenzug",
      description: "Failed to play an in-between move before recapturing" }

  - { id: MT-008, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 200, active: true,
      name: "Bad Sacrifice",
      description: "Sacrificed material without sufficient compensation" }

  - { id: MT-009, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 150, active: true,
      name: "Missed Defensive Resource",
      description: "Missed a defensive move that saves the position" }

  - { id: MT-010, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 300, active: true,
      name: "Missed Winning Combination",
      description: "A forced winning sequence was available and not played" }

  - { id: MT-011, phase: middlegame, axis: tactical, detection_method: hybrid, cp_loss_min: 150, active: true,
      name: "Calculation Error",
      description: "Correct concept, wrong execution due to calculation failure" }

  # ── MIDDLEGAME STRATEGIC ──────────────────────────────────────────────────
  - { id: MS-001, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 50,  active: true,
      name: "Passive Piece Placement",
      description: "Placed a piece on a passive square with no active role" }

  - { id: MS-002, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 80,  active: true,
      name: "Wrong Plan",
      description: "Pursued a plan that is objectively wrong for the position" }

  - { id: MS-003, phase: middlegame, axis: strategic, detection_method: hybrid, cp_loss_min: 100, active: true,
      name: "Ignored Opponent Threat",
      description: "Failed to address opponent's concrete positional threat" }

  - { id: MS-004, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 50,  active: true,
      name: "Weak Pawn — Isolated",
      description: "Created or allowed an isolated pawn without compensation" }

  - { id: MS-005, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 50,  active: true,
      name: "Weak Pawn — Doubled",
      description: "Created or allowed doubled pawns without compensation" }

  - { id: MS-006, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 50,  active: true,
      name: "Weak Pawn — Backward",
      description: "Created a backward pawn that becomes a chronic weakness" }

  - { id: MS-007, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 80,  active: true,
      name: "Weak Square Surrendered",
      description: "Allowed opponent to occupy or control a key weak square" }

  - { id: MS-008, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 80,  active: true,
      name: "Wrong Piece Trade",
      description: "Traded a good piece for a bad one or traded into a worse endgame" }

  - { id: MS-009, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 100, active: true,
      name: "Neglected King Safety",
      description: "Failed to address king safety while pursuing an attack" }

  - { id: MS-010, phase: middlegame, axis: strategic, detection_method: hybrid, cp_loss_min: 150, active: true,
      name: "Blunder After Advantage",
      description: "Threw away a significant advantage" }

  - { id: MS-011, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 80,  active: true,
      name: "Prophylaxis Failure",
      description: "Failed to prevent opponent's telegraphed plan" }

  - { id: MS-012, phase: middlegame, axis: strategic, detection_method: ai,    cp_loss_min: 50,  active: true,
      name: "Premature Piece Exchange",
      description: "Exchanged a well-placed piece for a poorly-placed one" }

  # ── ENDGAME TACTICAL ──────────────────────────────────────────────────────
  - { id: ET-001, phase: endgame, axis: tactical, detection_method: hybrid,    cp_loss_min: 200, active: true,
      name: "Missed Fork in Endgame",
      description: "Failed to execute a fork in an endgame position" }

  - { id: ET-002, phase: endgame, axis: tactical, detection_method: engine,    cp_loss_min: 300, active: true,
      name: "Missed Promotion Path",
      description: "Failed to see or execute a pawn promotion sequence" }

  - { id: ET-003, phase: endgame, axis: tactical, detection_method: engine,    cp_loss_min: 300, active: true,
      name: "Blunder in Winning Endgame",
      description: "Dropped a won endgame via tactical oversight" }

  - { id: ET-004, phase: endgame, axis: tactical, detection_method: engine,    cp_loss_min: 500, active: true,
      name: "Stalemate — Walked Into",
      description: "Walked into stalemate when winning" }

  - { id: ET-005, phase: endgame, axis: tactical, detection_method: hybrid,    cp_loss_min: 0,   active: true,
      name: "Stalemate — Missed Escape",
      description: "Missed a stalemate resource in a losing position" }

  - { id: ET-006, phase: endgame, axis: tactical, detection_method: hybrid,    cp_loss_min: 150, active: true,
      name: "Missed Skewer in Endgame",
      description: "Missed a skewer that would win material in the endgame" }

  # ── ENDGAME STRATEGIC ─────────────────────────────────────────────────────
  - { id: ES-001, phase: endgame, axis: strategic, detection_method: ai,       cp_loss_min: 100, active: true,
      name: "King Activation Failure",
      description: "Failed to activate the king in the endgame" }

  - { id: ES-002, phase: endgame, axis: strategic, detection_method: engine,   cp_loss_min: 150, active: true,
      name: "Wrong King Path",
      description: "King took an inferior path, losing key squares or tempo" }

  - { id: ES-003, phase: endgame, axis: strategic, detection_method: engine,   cp_loss_min: 200, active: true,
      name: "Opposition Failure",
      description: "Failed to maintain or contest opposition in a king-pawn endgame" }

  - { id: ES-004, phase: endgame, axis: strategic, detection_method: ai,       cp_loss_min: 100, active: true,
      name: "Passed Pawn Mishandled",
      description: "Advanced or traded a passed pawn incorrectly" }

  - { id: ES-005, phase: endgame, axis: strategic, detection_method: ai,       cp_loss_min: 100, active: true,
      name: "Passive Rook in Endgame",
      description: "Placed rook on a passive file or rank in the endgame" }

  - { id: ES-006, phase: endgame, axis: strategic, detection_method: ai,       cp_loss_min: 100, active: true,
      name: "Rook Not Behind Passed Pawn",
      description: "Failed to place rook behind the passed pawn (own or opponent's)" }

  - { id: ES-007, phase: endgame, axis: strategic, detection_method: ai,       cp_loss_min: 150, active: true,
      name: "Poor Conversion Technique",
      description: "Poor technique when converting a winning endgame" }

  - { id: ES-008, phase: endgame, axis: strategic, detection_method: ai,       cp_loss_min: 150, active: true,
      name: "Wrong Endgame Transition",
      description: "Transitioned into a lost or drawn endgame when a win was available" }

  # ── GAME CONDITIONS ───────────────────────────────────────────────────────
  # Detected by classifier.py from stored Move data — no Claude call, no engine re-run
  - { id: GC-001, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Rook vs Pawn Ending",
      description: "Entered an ending with only kings, rooks, and pawns; track win/loss rate" }

  - { id: GC-002, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Opposite-Color Bishop Ending",
      description: "Endgame with only kings, pawns, and bishops on opposite colors" }

  - { id: GC-003, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Knight Outpost Allowed",
      description: "Opponent had a knight on a central/semi-central outpost square for 5+ consecutive moves" }

  - { id: GC-004, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Isolated Queen Pawn",
      description: "Player entered the middlegame with an isolated pawn on the d-file" }

  - { id: GC-005, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Down Material Entering Endgame",
      description: "Player was 150cp or more worse when the endgame phase began" }

  - { id: GC-006, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Worse After Opening",
      description: "Total cp_loss in the opening phase exceeded 100 centipawns" }

  - { id: GC-007, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Exchange Sacrifice Received",
      description: "Opponent sacrificed a rook for a minor piece" }

  - { id: GC-008, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "King Safety Deficit",
      description: "Player's king was uncastled past move 15 while opponent had already castled" }

  - { id: GC-009, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Pawn Minority in Endgame",
      description: "Player had fewer pawns than the opponent when the endgame began" }

  - { id: GC-010, phase: all, axis: game_condition, detection_method: engine, cp_loss_min: 0, active: true,
      name: "Perpetual King Attack",
      description: "Player's king was in check 3 or more times in the last 10 moves" }
```

---

## 8. Analysis Pipeline

### 8.1 Overview

The pipeline has three independent layers. Each layer has its own status on the Game record. A layer can only run after the layer it depends on is complete.

```
Layer 1 — ENGINE (depends on: nothing)
  Game.engine_status: pending → running → complete | failed
  Output: cp_eval, cp_loss, best_move_san, mistake_severity on every Move
  Immutable after complete.

Layer 2 — ANNOTATION (depends on: engine complete)
  Game.annotation_status: pending → running → complete | failed
  Output: MovePatternMatch records for each mistake move
  Append-only. New patterns trigger targeted re-annotation of unmatched moves.

Layer 3 — CONDITION (depends on: engine complete)
  Game.condition_status: pending → running → complete | failed
  Output: GameCondition records
  Append-only. New GC patterns trigger targeted re-scan of unmatched conditions.
```

Layers 2 and 3 can run in parallel once Layer 1 is complete.

After both annotation and condition are complete, Pattern and PatternOccurrence records are updated (this is not a separate stage — it runs synchronously at the end of annotation and condition processing).

### 8.2 Layer 1 — Engine Analysis

**Trigger:** Game reaches engine_status = "pending"

**Steps:**
1. Parse PGN with python-chess
2. Extract game metadata: player_color, result, played_at, eco_code, opening_name, variation_name, time_control, total_moves
3. Create Move records: one per move with san, fen_before, fen_after, move_number, color
4. Assign phase to each Move (rules in Section 8.6)
5. For each move, call Stockfish at configured depth
6. Compute cp_loss from player's perspective (always positive = bad for player)
7. Set best_move_san and mistake_severity on each Move
8. Set engine_status = "complete", engine_completed_at = now()
9. Set annotation_status = "pending" and condition_status = "pending"

**On failure:** Set engine_status = "failed", increment engine_failure_count, set engine_next_retry_at per retry policy.

### 8.3 Layer 2 — Annotation (Append-Only)

**Trigger:** Game.annotation_status = "pending" AND engine_status = "complete"

**Normal path (first annotation):**
1. Load all active patterns from registry where axis != "game_condition" and axis != "opening_line"
2. For each Move where mistake_severity is not null:
   - Check PatternScanLog for (game_id, pattern_id) — skip if already scanned for all active patterns
   - Call annotator.py with: fen_before, san, best_move_san, cp_loss, phase, registry patterns
   - Receive: registry_pattern_id, annotation
   - Create MovePatternMatch record
   - Create PatternScanLog record for each pattern evaluated against this move
3. Update Pattern frequency counts (find-or-create Pattern, increment, create PatternOccurrence)
4. Set annotation_status = "complete", store registry_version_at_last_scan

**Re-scan path (new pattern added to registry):**
1. Identify which registry_pattern_ids have no PatternScanLog record for this game
2. For each Move where mistake_severity is not null AND move has not been scanned for the new pattern:
   - Call annotator.py with the new pattern as the only candidate
   - If matched: create MovePatternMatch, update Pattern frequency
   - Create PatternScanLog record regardless of result

### 8.4 Layer 3 — Condition Detection (Append-Only)

**Trigger:** Game.condition_status = "pending" AND engine_status = "complete"

**Normal path (first scan):**
1. Load all active GC patterns from registry
2. Call classifier.detect_game_conditions() with the game's Move records
3. For each detected condition: create GameCondition record
4. Create PatternScanLog record for every GC pattern evaluated (matched or not)
5. Update Pattern frequency counts for matched conditions
6. Set condition_status = "complete"

**Re-scan path (new GC pattern added):**
1. Identify GC patterns with no PatternScanLog for this game
2. Run condition detection for only those patterns against stored Move data
3. Create records as above

**Game condition detection rules** (implemented in classifier.py using python-chess):

| ID | Condition | Detection Logic |
|---|---|---|
| GC-001 | Rook vs Pawn Ending | Phase transitions to endgame; board has only K, R, P for both sides |
| GC-002 | Opposite-Color Bishop Ending | Endgame; only K, B, P on board; bishops on opposite-colored squares |
| GC-003 | Knight Outpost Allowed | Opponent knight on {c5,d4,d5,e4,e5,f5} for ≥ 5 consecutive middlegame moves |
| GC-004 | Isolated Queen Pawn | Player's d-pawn has no friendly pawns on c-file or e-file at middlegame start |
| GC-005 | Down Material at Endgame | cp_eval at first endgame move is ≤ -150 from player perspective |
| GC-006 | Worse After Opening | Sum of player cp_loss for all opening-phase moves ≥ 100 |
| GC-007 | Exchange Sacrifice Received | Opponent's material drops by ~2pts (rook lost) while player loses ~3pts (minor piece) in same exchange |
| GC-008 | King Safety Deficit | Player's king not castled by move 15 AND opponent's king is castled |
| GC-009 | Pawn Minority at Endgame | Player pawn count < opponent pawn count at first endgame move |
| GC-010 | Perpetual King Attack | Player's king was in check on ≥ 3 of the last 10 moves of the game |

### 8.5 Retry Policy

`pipeline/retry.py` runs every RETRY_INTERVAL_SECONDS via APScheduler.

| engine_failure_count | Retry delay |
|---|---|
| 1 | 2 minutes |
| 2 | 10 minutes |
| 3 | 1 hour |
| 4 | 6 hours |
| 5 | 24 hours |
| > MAX_RETRIES | Set to "needs_manual_review" — stop retrying |

Stuck job reset: any game with engine_status = "running" for more than 30 minutes is reset to "pending".

Annotation and condition failures use the same retry policy independently.

### 8.6 Phase Assignment Rules

Applied per-move during engine analysis. Stored permanently on Move.phase.

| Phase | Rule |
|---|---|
| Opening | move_number ≤ 15 AND total pieces on board ≥ 28 |
| Endgame | Total material ≤ 26 pts (Q=9, R=5, B=3, N=3, P=1, kings excluded) OR (no queens AND total ≤ 40) |
| Middlegame | Everything else |

---

## 9. Service Specifications

### 9.1 lichess.py

```python
async def import_games(db: AsyncSession) -> dict:
    # Returns: { imported: int, skipped: int, errors: int }
```

- Stream `GET https://lichess.org/api/games/user/{LICHESS_USERNAME}` (NDJSON)
- Params: rated=true, moves=true, opening=true
- For each game: if lichess_id exists in DB → skip; else insert with engine_status="pending"
- HTTP 429: sleep 60s, retry. HTTP 401: raise ConfigError.

### 9.2 stockfish.py

```python
class StockfishEngine:
    def start(self) -> None          # launch subprocess, reuse across moves
    def stop(self) -> None
    def evaluate(self, fen: str, depth: int) -> dict:
        # Returns: { cp_eval: float, best_move_san: str }
        # cp_eval is from the perspective of the side to move
        # Mate scores map to ±10000
```

One instance per analysis session. Do not restart per game or per move.

### 9.3 classifier.py

```python
def assign_phase(board: chess.Board, move_number: int) -> str:
    # Returns: "opening" | "middlegame" | "endgame"

def assign_severity(cp_loss: float) -> str | None:
    # Returns: "inaccuracy" | "mistake" | "blunder" | None
    # Uses CP_LOSS_INACCURACY, CP_LOSS_MISTAKE, CP_LOSS_BLUNDER from config

def detect_game_conditions(
    moves: list[Move],
    active_gc_patterns: list[dict]
) -> list[dict]:
    # Returns list of detected conditions:
    # [{ registry_pattern_id, condition_name, detected_at_move,
    #    player_was_worse, context_note }]
    # Only evaluates patterns in active_gc_patterns
    # Uses only data already on Move records — no Stockfish calls
```

### 9.4 annotator.py

```python
async def annotate_mistake(
    fen: str,
    played_move_san: str,
    best_move_san: str,
    cp_loss: float,
    phase: str,
    candidate_patterns: list[dict]   # subset of registry patterns relevant to this call
) -> dict:
    # Returns: { registry_pattern_id: str, annotation: str }
    # registry_pattern_id will always be one of the IDs in candidate_patterns
    # annotation is max 80 words
    # Never raises — returns UNCLASSIFIED on persistent failure
```

**System prompt (exact text — do not paraphrase):**
```
You are a chess coach analyzing a player's mistake.
Given a position, the move played, the best move, and a list of pattern IDs with descriptions,
identify which pattern best matches this mistake.

Rules:
- Return ONLY a JSON object — no prose, no markdown fences
- registry_pattern_id MUST exactly match one of the IDs in the provided list
- If no pattern fits precisely, return the closest match — never return null or an unknown ID
- annotation must be specific: name the pieces and squares involved, state the consequence
- annotation must be 80 words or fewer
- Do not include game_condition patterns (IDs starting with GC-)

Response format:
{"registry_pattern_id": "XX-000", "annotation": "..."}
```

**User message format:**
```
Phase: {phase}
FEN: {fen}
Move played: {played_move_san}
Best move: {best_move_san}
Centipawn loss: {cp_loss}

Available patterns:
{json.dumps([{"id": p["id"], "name": p["name"], "description": p["description"]}
             for p in candidate_patterns])}
```

**Error handling:**
- Invalid JSON → retry once with "Return only raw JSON, nothing else" appended
- Still invalid → return `{"registry_pattern_id": "UNCLASSIFIED", "annotation": "Classification failed"}`

### 9.5 scanner.py

Orchestrates targeted re-analysis when the registry changes.

```python
async def get_unscanned_games(
    db: AsyncSession,
    registry_pattern_id: str
) -> list[int]:
    # Returns game IDs with no PatternScanLog record for this pattern
    # Only returns games where engine_status = "complete"

async def queue_rescan_for_pattern(
    db: AsyncSession,
    registry_pattern_id: str
) -> dict:
    # Finds all games with no scan record for this pattern
    # Sets has_unscanned_patterns = True on those games
    # Returns: { games_queued: int }
```

### 9.6 opening_stats.py

```python
async def compute_opening_stats(db: AsyncSession) -> int:
    # Recomputes all OpeningStats from games where engine_status = "complete"
    # Returns count of lines computed
```

- Group complete games by (eco_code, opening_name, variation_name)
- Exclude groups with fewer than 3 games
- Compute: total_games, wins, losses, draws, win_rate, loss_rate
- avg_cp_loss_opening: mean cp_loss of all opening-phase moves across the group
- divergence_move: most common move number where a mistake or blunder first appears in this line
- divergence_san: most common move played at that move number in this line
- Delete existing OpeningStats and reinsert (full recompute, not incremental)

---

## 10. API Endpoints

All responses are JSON. List endpoints support `?limit=&offset=` pagination.

### 10.1 Games

| Method | Path | Response |
|---|---|---|
| POST | `/api/games/import` | `{ imported, skipped, errors }` |
| GET | `/api/games` | List: id, lichess_id, played_at, result, eco_code, opening_name, variation_name, engine_status |
| GET | `/api/games/{id}` | Full game with all moves, pattern matches, and game conditions |
| GET | `/api/games/{id}/mistakes` | Only mistake/blunder/inaccuracy moves with all pattern matches |
| GET | `/api/games/{id}/recurring` | Mistakes from this game where Pattern.frequency > 1, with frequency |

### 10.2 Analysis

| Method | Path | Description |
|---|---|---|
| POST | `/api/analysis/run` | Queue all engine_status=pending games |
| GET | `/api/analysis/status` | Count of games per engine/annotation/condition status combination |
| GET | `/api/analysis/failed` | Games with any layer in failed or needs_manual_review state |
| POST | `/api/analysis/retry-failed` | Re-queue all failed games |

### 10.3 Patterns

| Method | Path | Description |
|---|---|---|
| GET | `/api/patterns` | All Pattern records sorted by frequency desc |
| GET | `/api/patterns/{id}` | Single pattern with all PatternOccurrence records |
| GET | `/api/patterns/report` | Frequency matrix: phase × axis |
| GET | `/api/patterns/conditions` | Game condition Patterns with W/L/D aggregation, sorted by loss_rate |

**Pattern report response:**
```json
{
  "matrix": {
    "opening":    { "tactical": { "count": 12, "top": [{"name":"...", "frequency":5}] },
                    "strategic": { "count": 7, "top": [...] } },
    "middlegame": { "tactical": {...}, "strategic": {...} },
    "endgame":    { "tactical": {...}, "strategic": {...} }
  }
}
```

**Conditions response (per item):**
```json
{
  "registry_pattern_id": "GC-003",
  "name": "Knight Outpost Allowed",
  "total_games": 8,
  "wins": 1, "losses": 6, "draws": 1,
  "loss_rate": 0.75,
  "frequency": 8
}
```

### 10.4 Openings

| Method | Path | Description |
|---|---|---|
| GET | `/api/openings` | All OpeningStats sorted by loss_rate desc |
| GET | `/api/openings/{eco_code}` | All variations for one ECO code |
| POST | `/api/openings/compute` | Recompute from all engine-complete games |

**Single opening response:**
```json
{
  "eco_code": "B08",
  "opening_name": "Pirc Defense",
  "variation_name": "Classical Variation",
  "total_games": 14, "wins": 3, "losses": 9, "draws": 2,
  "loss_rate": 0.64,
  "divergence_move": 10,
  "divergence_san": "Nbd7",
  "avg_cp_loss_opening": 42.3
}
```

### 10.5 Admin

| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/registry` | Full patterns.yaml contents as JSON |
| POST | `/api/admin/registry/reload` | Parse YAML, queue re-scan for any new pattern IDs |
| GET | `/api/admin/coverage` | Game counts per status; unscanned pattern count |
| GET | `/api/admin/scan-log` | PatternScanLog summary: patterns × games coverage matrix |
| POST | `/api/admin/reprocess/game/{id}` | Re-queue a specific game from a named layer |
| POST | `/api/admin/reprocess/pattern/{pattern_id}` | Queue all unscanned games for one pattern |
| GET | `/api/admin/stuck` | Games with any layer in "running" state > 30 minutes |

---

## 11. Frontend — Three Pages

### 11.1 Design Direction

Dark theme. Dense but readable. Chess-terminal aesthetic — monospace for move notation, clean data tables, no decorative elements. The chessboard is the visual anchor on the game page; everything else serves the data. Reuse `ChessBoard.jsx` and `OpeningRow.jsx` from `reference/` without modification.

### 11.2 Page 1 — Game View (`/games/:id`)

**Layout:** Two columns. Left: chessboard + scrollable move list. Right: analysis panel.

**Left column:**
- `ChessBoard` — displays position at currently selected move
- `MoveList` — all moves in game, pairs per row (white + black), move number prefix. Mistake moves highlighted: amber = inaccuracy, orange = mistake, red = blunder. Clicking any move updates the board position.

**Right column — two stacked sections:**

**Section A — This Game**
- Title: game result badge + opening name + opponent + date
- List of all moves where mistake_severity is not null, ordered by move number
- Each row: move number, SAN (monospace), severity badge, truncated annotation (60 chars max)
- Clicking a row navigates board to that move

**Section B — Recurring**
- Title: "Recurring Patterns"
- List of mistakes from this game where Pattern.frequency > 1
- Each row: pattern name, frequency badge (e.g. "×7"), truncated annotation
- Clicking navigates board to that move
- Empty state: "No recurring patterns in this game"

**Games list** (`/games`): table of all games. Columns: date, opponent, result badge, opening name + variation, analysis status. Clicking a row opens game view.

### 11.3 Page 2 — Openings (`/openings`)

**Layout:** Full-width sortable table. One row per opening line.

**Each row (all on one line — reuse `OpeningRow` from reference/):**
- ECO code — monospace, muted
- Opening name — bold
- Variation — muted italic
- Inline move chips — moves displayed as small horizontal badges
- W / L / D badges — colored (green/red/gray)
- Loss rate — right-aligned, red if > 50%
- Divergence annotation — e.g. "Goes wrong at move 10 · Nbd7"

**Defaults:** Sorted by loss_rate descending. Filter bar: minimum games played (default 3).

**Row expansion:** Clicking a row reveals the list of individual games in that line — date, result, opponent. Clicking a game navigates to Game View.

### 11.4 Page 3 — Patterns (`/patterns`)

**Two sections on one page:**

**Section A — Recurring Mistakes**
- Filter tabs: All | Tactical | Strategic | Opening | Middlegame | Endgame
- `PatternCard` per Pattern (axis != game_condition), sorted by frequency desc
- Each card: pattern name, phase + axis badges, "×N across M games", first/last seen dates, most recent annotation snippet
- Expanding a card shows: list of game occurrences with date, move number, and annotation

**Section B — Game Situations**
- Title: "Game Situations"
- One card per game-condition Pattern
- Each card: condition name, "N games — X losses (Y%)", W/L/D bar
- Sorted by loss_rate descending
- Expanding shows list of games where condition was detected, each with result badge

### 11.5 Navigation

Top nav bar: **Games | Openings | Patterns** — no sidebar, no nesting.

---

## 12. Implementation Phases

Complete each phase and verify before starting the next.

### Phase 1 — Foundation
**Goal:** Import games, parse PGN, store structured move data.

1. Project structure per Section 4
2. `config.py`, `database.py`, `models.py` with all tables, Alembic migration
3. `lichess.py` — import with deduplication
4. PGN parsing in `worker.py` — create Move records, assign phases
5. `GET /api/games`, `POST /api/games/import`, `GET /api/analysis/status`
6. Tests: deduplication, phase assignment, PGN parsing correctness

**Done when:** 10 games imported; every game has Move records with correct phase assignments.

### Phase 2 — Engine Analysis
**Goal:** Every move has cp_eval, cp_loss, best_move, severity.

1. `stockfish.py` subprocess wrapper
2. `classifier.py` — severity thresholds, phase logic
3. ENGINE layer in `worker.py`
4. `GET /api/games/{id}/mistakes`
5. Tests: cp_loss values correct, severity thresholds applied correctly

**Done when:** 10 games reach engine_status=complete; every move has cp_loss; `mistakes` endpoint returns blunders.

### Phase 3 — Registry + Annotation
**Goal:** Every mistake classified; scan log populated; Pattern records built.

1. `registry/patterns.yaml` with full list from Section 7.3
2. Registry loader in `admin.py` — parse YAML, expose via GET
3. `annotator.py` with exact Claude prompt from Section 9.4
4. ANNOTATION layer in `worker.py` — create MovePatternMatch and PatternScanLog records
5. Pattern find-or-create + frequency increment logic
6. `GET /api/patterns`, `GET /api/patterns/report`
7. Tests: annotator returns valid ID; UNCLASSIFIED fallback; PatternScanLog populated correctly

**Done when:** 10 games reach annotation_status=complete; pattern report returns correct matrix.

### Phase 4 — Conditions + Targeted Re-scan
**Goal:** Game conditions detected; new patterns can be added and retroactively scanned.

1. `classifier.detect_game_conditions()` for all GC patterns
2. CONDITION layer in `worker.py`
3. `scanner.py` — unscanned game detection, re-scan queue logic
4. `POST /api/admin/registry/reload` — detects new patterns, queues re-scan
5. `GET /api/patterns/conditions`, `GET /api/admin/scan-log`
6. Tests: conditions detected correctly; adding a new pattern to YAML and reloading queues correct games

**Done when:** Conditions detected; adding a new GC pattern to YAML + calling reload queues all games for that pattern without touching engine data.

### Phase 5 — Openings
**Goal:** Opening stats computed and served.

1. `opening_stats.py` — aggregation logic
2. `GET /api/openings`, `GET /api/openings/{eco_code}`, `POST /api/openings/compute`
3. Tests: W/L/D counts correct; divergence move logic correct

**Done when:** Openings API returns lines sorted by loss_rate with correct stats.

### Phase 6 — Reliability
**Goal:** No game silently dropped; failures retried; reprocessing works.

1. `retry.py` — APScheduler, retry policy from Section 8.5
2. Stuck job detection and reset
3. `GET /api/admin/coverage`, `GET /api/admin/stuck`
4. `POST /api/admin/reprocess/*` endpoints
5. Tests: retry increments failure_count; stuck jobs reset; reprocess clears correct records

**Done when:** Coverage shows 100% complete for all importable games; a game can be manually requeued from any layer.

### Phase 7 — Frontend
**Goal:** All three pages render correct data; board navigation works.

1. Vite + React scaffold, Tailwind, api.js
2. Games list + Game View (board + mistake panel + recurring panel) — reuse `ChessBoard` from reference/
3. Openings page — reuse `OpeningRow` from reference/
4. Patterns page — recurring mistakes section + game situations section
5. Navigation

**Done when:** All three pages display correct data from the API; clicking moves on game view navigates the board; opening rows show inline moves.

---

## 13. Definition of Done

The application is complete when:

1. All Lichess games imported and in complete status across all three layers
2. Every mistake move has: cp_loss, best_move_san, at least one MovePatternMatch record
3. PatternScanLog has a record for every (game, active_pattern) pair
4. Pattern frequency counts are accurate — verified by spot-checking 5 patterns
5. Opening stats are accurate — verified by spot-checking 3 lines
6. Game conditions detected correctly — verified by spot-checking 3 condition types
7. Adding a new pattern to YAML + calling reload queues correct games without engine re-run
8. All three frontend pages render and function correctly
9. `ruff check` passes — zero errors
10. `pytest` passes — zero failures

---

## Appendix A: Key Design Decisions

| Decision | Rationale |
|---|---|
| MovePatternMatch table (many-to-many) instead of single field on Move | Enables append-only classification — a move accumulates matches over time |
| PatternScanLog table | Enables targeted re-analysis — system knows exactly which (game, pattern) pairs still need scanning |
| Three independent layer statuses on Game | Engine, annotation, and condition can fail and retry independently; engine data is never at risk |
| Engine data immutable after complete | Stockfish analysis is expensive (2000-5000 games × 40 moves × depth 18); run once, reuse forever |
| Append-only on new patterns | Existing correct classifications are preserved; only genuinely unclassified moves are re-evaluated |
| Game condition detection uses stored Move data only | Conditions are derived from board state, not from Stockfish re-evaluation; cheap to re-run |
| Statistical minimum of 3 games for openings | Prevents single-game noise from distorting opening reports |
| YAML registry version-controlled | Human-readable, diffable, auditable — the complete history of what the system was capable of detecting at any point in time |
```