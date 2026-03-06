# Data Model
# Chess Trainer Agent

Database: SQLite via SQLAlchemy ORM
Models defined in: `backend/models.py`

---

## Entity Relationship Diagram

```
MistakeCategory (self-referential)
  │
  ├─< MistakeCategory (children via parent_id)
  │
  └─< Pattern.category_id

Game
  │
  └─< Move
       │
       └─< PatternInstance

Pattern
  │
  ├─< PatternInstance
  └─< PatternAcknowledgment

OpeningStats (standalone aggregate)

ProgressSnapshot (standalone aggregate)

WorkflowRun (standalone)
```

---

## Tables

### Game

Primary table for imported chess games.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (PK) | no | UUID | Unique identifier |
| `pgn` | Text | no | - | Full PGN text |
| `white` | String | no | - | White player name |
| `black` | String | no | - | Black player name |
| `result` | String | no | - | "1-0", "0-1", or "1/2-1/2" |
| `date_played` | Date | yes | - | Game date from PGN headers |
| `opening_eco` | String | yes | - | ECO code (e.g. "B08") |
| `opening_name` | String | yes | - | Opening name from PGN headers |
| `player_color` | String | no | - | "white" or "black" |
| `source` | String | no | - | "lichess", "chesscom", or "pgn_upload" |
| `source_id` | String | yes | - | Deduplication key from source platform |
| `imported_at` | DateTime | no | utcnow | Import timestamp |
| `analysis_status` | String | no | "pending" | "pending", "analyzed", or "error" |

**Relationships:** `moves` -> Move (one-to-many, cascade delete)

---

### Move

Individual moves within a game, with engine analysis results.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer (PK) | no | auto | Unique identifier |
| `game_id` | String (FK) | no | - | References Game.id |
| `move_number` | Integer | no | - | Chess move number (1-indexed) |
| `ply` | Integer | no | - | Half-move index (0-indexed) |
| `san` | String | no | - | Standard Algebraic Notation (e.g. "Nf3") |
| `uci` | String | no | - | UCI notation (e.g. "g1f3") |
| `fen_before` | String | no | - | Board position before this move |
| `fen_after` | String | no | - | Board position after this move |
| `engine_eval_before` | Float | yes | - | Centipawn eval before move (white's perspective) |
| `engine_eval_after` | Float | yes | - | Centipawn eval after move (white's perspective) |
| `eval_delta` | Float | yes | - | Centipawn loss (always >= 0, higher = worse) |
| `best_move_uci` | String | yes | - | Engine's best move in the position |
| `classification` | String | yes | - | "best", "good", "inaccuracy", "mistake", "blunder" |
| `phase` | String | yes | - | "opening", "middlegame", "endgame" |
| `mistake_type` | String | yes | - | "tactical" or "strategic" (not yet populated) |
| `themes_json` | Text | yes | - | JSON positional themes (not yet populated) |

**Relationships:** `game` -> Game, `pattern_instances` -> PatternInstance

**Classification thresholds** (centipawn loss):
- best: <= 10
- good: <= 30
- inaccuracy: <= 70
- mistake: <= 150
- blunder: > 150

**Phase detection** (from `classifier.detect_phase`):
- opening: move_number <= 15 AND minor/major pieces >= 10
- endgame: minor/major pieces <= 6
- middlegame: everything else

---

### Pattern

Recurring mistake patterns identified by Claude AI synthesis.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (PK) | no | UUID | Unique identifier |
| `label` | String | no | - | Short pattern name (5-8 words) |
| `description` | Text | no | - | Detailed explanation of the weakness |
| `category` | String | no | - | "tactical", "positional", "endgame", "opening", "time_mgmt" |
| `category_id` | Integer (FK) | yes | - | References MistakeCategory.id |
| `mistake_type` | String | yes | - | "tactical" or "strategic" |
| `severity_score` | Float | no | 0.0 | 0-100 score (frequency x avg eval loss) |
| `frequency` | Integer | no | 0 | Number of occurrences |
| `first_seen` | Date | yes | - | Date of first occurrence |
| `last_seen` | Date | yes | - | Date of most recent occurrence |
| `resolved` | Boolean | no | False | Whether pattern is resolved |
| `acknowledged` | Boolean | no | False | Whether player has acknowledged |
| `acknowledged_at` | DateTime | yes | - | Timestamp of acknowledgment |
| `post_acknowledgment_count` | Integer | no | 0 | Occurrences after acknowledgment |
| `example_game_ids` | Text | yes | - | JSON array of game IDs |
| `training_recommendation` | Text | yes | - | Suggested practice advice |

**Relationships:** `instances` -> PatternInstance, `acknowledgments` -> PatternAcknowledgment, `mistake_category` -> MistakeCategory

---

### PatternInstance

Links a pattern to a specific move where it was observed.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer (PK) | no | auto | Unique identifier |
| `pattern_id` | String (FK) | no | - | References Pattern.id |
| `game_id` | String (FK) | no | - | References Game.id |
| `move_id` | Integer (FK) | no | - | References Move.id |
| `notes` | Text | yes | - | Instance-specific notes |

---

### PatternAcknowledgment

Records when a player acknowledges a pattern.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer (PK) | no | auto | Unique identifier |
| `pattern_id` | String (FK) | no | - | References Pattern.id |
| `acknowledged_at` | DateTime | no | utcnow | Acknowledgment timestamp |
| `player_note` | Text | yes | - | Player's free-text note |

---

### MistakeCategory

Hierarchical, extensible mistake taxonomy. Self-referential tree structure.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer (PK) | no | auto | Unique identifier |
| `parent_id` | Integer (FK) | yes | - | References MistakeCategory.id (parent) |
| `name` | String | no | - | Category name |
| `description` | Text | no | - | What this category means |
| `detection_method` | String | no | "hybrid" | "engine", "ai", or "hybrid" |
| `active` | Boolean | no | True | Whether category is enabled |

**Relationships:** `children` -> MistakeCategory (cascade delete), `parent` -> MistakeCategory

**Seed data** (from `backend/seed.py`):
```
tactical (engine)
  ├── missed_tactic (engine)
  ├── hung_piece (engine)
  ├── failed_combination (engine)
  └── missed_checkmate (engine)
strategic (ai)
  ├── bad_pawn_structure (ai)
  ├── poor_piece_placement (ai)
  ├── wrong_plan (ai)
  └── weak_square_control (ai)
```

---

### OpeningStats

Aggregated per-opening statistics. Rebuilt from scratch on each refresh.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer (PK) | no | auto | Unique identifier |
| `eco_code` | String | no | - | ECO classification code |
| `opening_name` | String | no | - | Base opening name |
| `variation_name` | String | yes | - | Variation name (after ":") |
| `move_sequence` | Text | yes | - | JSON array of SAN moves (longest common prefix) |
| `total_games` | Integer | no | 0 | Total games in this line |
| `wins` | Integer | no | 0 | Player wins |
| `losses` | Integer | no | 0 | Player losses |
| `draws` | Integer | no | 0 | Draws |
| `avg_cp_loss` | Float | yes | - | Average centipawn loss in opening phase |
| `divergence_move` | Integer | yes | - | Move where losses diverge from wins |
| `last_updated` | DateTime | no | utcnow | Last computation time |

---

### ProgressSnapshot

Point-in-time accuracy and pattern metrics.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer (PK) | no | auto | Unique identifier |
| `snapshot_date` | Date | no | - | Snapshot date |
| `total_games` | Integer | no | 0 | Analyzed games at time of snapshot |
| `avg_accuracy` | Float | no | 0.0 | % of moves classified "best" or "good" |
| `accuracy_opening` | Float | yes | - | Opening phase accuracy (not yet populated) |
| `accuracy_middlegame` | Float | yes | - | Middlegame accuracy (not yet populated) |
| `accuracy_endgame` | Float | yes | - | Endgame accuracy (not yet populated) |
| `acknowledged_patterns` | Integer | no | 0 | Count at time of snapshot (not yet populated) |
| `recurring_patterns` | Integer | no | 0 | Count at time of snapshot (not yet populated) |
| `resolved_patterns` | Integer | no | 0 | Count at time of snapshot (not yet populated) |
| `session_id` | String | yes | - | Session grouping key (not yet used) |
| `patterns_json` | Text | yes | - | JSON snapshot of active patterns |

---

### WorkflowRun

Tracks workflow execution history.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (PK) | no | UUID | Run identifier |
| `workflow_name` | String | no | - | Name of the workflow |
| `parameters_json` | Text | yes | - | JSON input parameters |
| `status` | String | no | "running" | "running", "completed", "failed" |
| `step_results_json` | Text | yes | - | JSON step-by-step results |
| `started_at` | DateTime | no | utcnow | Start time |
| `completed_at` | DateTime | yes | - | Completion time |
