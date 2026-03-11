# API Reference
# Chess Trainer Agent

Base URL: `http://localhost:8000/api`

---

## Health

### `GET /api/health`

Returns server health status.

**Response:** `{"status": "ok"}`

---

## Games

### `POST /api/games/upload`

Upload a PGN file containing one or more games. Games are auto-queued for analysis.

**Request:** Multipart file upload (field: `file`)

**Response:**
```json
{"status": "ok", "imported": 3, "skipped": 1}
```

### `POST /api/games/import/lichess`

Import games from Lichess for a given user. Games are auto-queued for analysis.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `username` | string | yes | Lichess username |
| `since` | string | no | ISO date (e.g. "2025-01-01"). Games after this date. |
| `max_games` | int | no | Maximum games to fetch. Default: all. |
| `color` | string | no | "white" or "black" |
| `rated` | string | no | "true" or "false" |
| `time_control` | string | no | "bullet", "blitz", "rapid", "classical", "correspondence" |

**Response:**
```json
{"status": "ok", "imported": 10, "skipped": 2}
```

### `GET /api/games/import/lichess/latest`

Get the date of the most recently imported Lichess game for a user.

**Query Parameters:** `username` (string, required)

**Response:**
```json
{"latest_date": "2026-03-06", "game_count": 42}
```

### `POST /api/games/import/chesscom`

Import games from Chess.com. **Status: Not implemented (returns 501).**

### `GET /api/games`

List all games with optional filters.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | string | - | Filter by source (lichess, chesscom, pgn_upload) |
| `opening` | string | - | Filter by ECO code |
| `color` | string | - | Filter by player color |
| `limit` | int | 50 | Results per page |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "games": [
    {
      "id": "uuid",
      "white": "player1",
      "black": "player2",
      "result": "1-0",
      "date_played": "2026-03-01",
      "opening_eco": "B08",
      "opening_name": "Pirc Defense",
      "player_color": "white",
      "source": "lichess",
      "source_id": "abc123",
      "imported_at": "2026-03-06T10:00:00",
      "analysis_status": "analyzed"
    }
  ],
  "total": 42
}
```

### `GET /api/games/{game_id}`

Get a single game with all moves and annotations.

**Response:** Same as list item, plus `"moves": [...]` array.

### `GET /api/games/{game_id}/moves`

Get just the move list for a game.

**Response:**
```json
{
  "moves": [
    {
      "id": 1,
      "move_number": 1,
      "ply": 0,
      "san": "e4",
      "uci": "e2e4",
      "fen_before": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
      "engine_eval_before": 20.0,
      "engine_eval_after": 30.0,
      "eval_delta": 0.0,
      "classification": "best",
      "phase": "opening",
      "themes_json": null
    }
  ]
}
```

### `DELETE /api/games/{game_id}`

Delete a game and its moves.

**Response:** `{"status": "deleted"}`

---

## Openings

### `GET /api/openings`

List all opening lines with win/loss/draw stats, sorted by loss percentage.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort_by` | string | "loss_pct" | Sort field: "loss_pct", "total_games", "avg_cp_loss" |

**Response:**
```json
{
  "openings": [
    {
      "id": 1,
      "eco_code": "B08",
      "opening_name": "Pirc Defense",
      "variation_name": "Classical Variation",
      "move_sequence": ["e4", "d6", "d4", "Nf6", "Nc3", "g6"],
      "total_games": 12,
      "wins": 3,
      "losses": 9,
      "draws": 0,
      "win_pct": 25.0,
      "loss_pct": 75.0,
      "draw_pct": 0.0,
      "avg_cp_loss": 45.3,
      "divergence_move": 9,
      "last_updated": "2026-03-06T10:00:00"
    }
  ],
  "total": 15
}
```

### `GET /api/openings/{eco_code}`

Drill-down into a specific ECO code showing all variation lines and their games.

**Response:**
```json
{
  "eco_code": "B08",
  "lines": [
    {
      "eco_code": "B08",
      "opening_name": "Pirc Defense",
      "variation_name": "Classical Variation",
      "move_sequence": ["e4", "d6", "d4", "Nf6"],
      "total_games": 12,
      "wins": 3,
      "losses": 9,
      "draws": 0,
      "loss_pct": 75.0,
      "avg_cp_loss": 45.3,
      "divergence_move": 9,
      "games": [
        {
          "id": "uuid",
          "white": "player1",
          "black": "player2",
          "result": "0-1",
          "player_color": "white",
          "player_result": "loss",
          "date_played": "2026-03-01"
        }
      ]
    }
  ]
}
```

### `POST /api/openings/refresh`

Recalculate all opening statistics from analyzed games. Clears and rebuilds the `opening_stats` table.

**Response:** `{"status": "ok", "openings_computed": 15}`

---

## Analysis

### `POST /api/analyze/compare`

Submit a game for analysis and comparison against known patterns. Runs the `new_game_comparison` workflow.

**Query Parameters:** `game_id` (string)

**Response:**
```json
{"run_id": "uuid", "status": "completed", "game_id": "uuid"}
```

### `POST /api/analyze/pending`

Trigger analysis for all pending games.

**Response:** `{"queued": 5}`

### `GET /api/analyze/status/{run_id}`

Check status of a workflow run.

**Response:**
```json
{
  "run_id": "uuid",
  "workflow": "new_game_comparison",
  "status": "completed",
  "started_at": "2026-03-06T10:00:00",
  "completed_at": "2026-03-06T10:01:00"
}
```

---

## Patterns

### `GET /api/patterns`

List all patterns sorted by severity score (descending).

**Response:**
```json
{
  "patterns": [
    {
      "id": "uuid",
      "label": "Missed knight forks in middlegame",
      "description": "Repeatedly fails to spot knight fork opportunities...",
      "category": "tactical",
      "severity_score": 85.0,
      "frequency": 7,
      "first_seen": "2026-01-15",
      "last_seen": "2026-03-05",
      "resolved": false,
      "acknowledged": false,
      "post_acknowledgment_count": 0,
      "example_game_ids": "[\"id1\", \"id2\"]",
      "training_recommendation": "Practice knight fork puzzles on Lichess..."
    }
  ]
}
```

### `GET /api/patterns/{pattern_id}`

Get pattern detail with all instances (moves where this pattern was observed).

**Response:** Same as list item, plus:
```json
{
  "instances": [
    {"id": 1, "game_id": "uuid", "move_id": 42, "notes": "..."}
  ]
}
```

### `POST /api/patterns/refresh`

Trigger Claude pattern synthesis. **Status: Stubbed.**

**Response:** `{"status": "queued"}`

### `GET /api/patterns/acknowledged`

List all acknowledged but unresolved patterns, ordered by post-acknowledgment recurrence count.

**Response:**
```json
{
  "patterns": [
    {
      "id": "uuid",
      "label": "Missed knight forks",
      "description": "...",
      "category": "tactical",
      "frequency": 7,
      "acknowledged_at": "2026-03-01T10:00:00",
      "post_acknowledgment_count": 3,
      "severity_score": 85.0
    }
  ],
  "total": 2
}
```

### `POST /api/patterns/{pattern_id}/acknowledge`

Acknowledge a pattern. Creates a `PatternAcknowledgment` record.

**Request Body (optional):**
```json
{"player_note": "I need to watch for this in the Sicilian"}
```

**Response:**
```json
{"status": "acknowledged", "pattern_id": "uuid", "acknowledged_at": "2026-03-06T10:00:00"}
```

### `DELETE /api/patterns/{pattern_id}/acknowledge`

Revoke acknowledgment. Deletes all acknowledgment records and resets counters.

**Response:** `{"status": "revoked", "pattern_id": "uuid"}`

### `POST /api/patterns/{pattern_id}/resolve`

Mark a pattern as resolved.

**Response:** `{"status": "resolved", "pattern_id": "uuid"}`

---

## Reports

### `GET /api/reports/mistakes`

Categorized mistake report as a phase x type matrix.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `phase` | string | Filter by phase (opening, middlegame, endgame) |
| `type` | string | Filter by type (tactical, strategic, unclassified) |
| `game_id` | string | Scope to a single game |

**Response:**
```json
{
  "matrix": {
    "opening": {
      "tactical": {"count": 5, "examples": [...]},
      "strategic": {"count": 3, "examples": [...]},
      "unclassified": {"count": 1, "examples": [...]}
    },
    "middlegame": { ... },
    "endgame": { ... }
  },
  "phase_totals": {"opening": 9, "middlegame": 12, "endgame": 4},
  "type_totals": {"tactical": 15, "strategic": 8, "unclassified": 2},
  "total_mistakes": 25
}
```

### `GET /api/reports/repeated`

Repeated mistakes ordered by frequency.

**Query Parameters:** `min_frequency` (int, default 2)

**Response:**
```json
{
  "patterns": [
    {
      "id": "uuid",
      "label": "Missed knight forks",
      "description": "...",
      "category": "tactical",
      "mistake_type": "tactical",
      "severity_score": 85.0,
      "frequency": 7,
      "first_seen": "2026-01-15",
      "last_seen": "2026-03-05",
      "acknowledgment_status": "recurring",
      "post_acknowledgment_count": 3,
      "training_recommendation": "...",
      "instance_count": 7,
      "example_game_ids": ["id1", "id2"]
    }
  ],
  "total": 5
}
```

### `GET /api/reports/trends`

Accuracy trends by phase, comparing recent vs older games.

**Query Parameters:** `period_games` (int, default 10)

**Response:**
```json
{
  "trends": {
    "opening": {"recent": 75.0, "older": 68.0, "delta": 7.0, "improving": true},
    "middlegame": {"recent": 60.0, "older": 65.0, "delta": -5.0, "improving": false},
    "endgame": {"recent": 55.0, "older": 50.0, "delta": 5.0, "improving": true}
  },
  "has_data": true
}
```

---

## Notifications

### `GET /api/games/{game_id}/notifications`

Get pattern-match notifications for a specific game, ordered by priority.

**Priority levels:**
1. `recurring_acknowledged` — acknowledged pattern recurring again
2. `high_frequency` — unacknowledged pattern with frequency >= 3
3. `moderate` — moderate frequency pattern
4. `new` — first occurrence

**Response:**
```json
{
  "game_id": "uuid",
  "notifications": [
    {
      "pattern_id": "uuid",
      "pattern_label": "Missed knight forks",
      "pattern_description": "...",
      "category": "tactical",
      "frequency": 7,
      "acknowledged": true,
      "post_acknowledgment_count": 3,
      "severity_score": 85.0,
      "move_id": 42,
      "ply": 15,
      "san": "Nf3",
      "move_number": 8,
      "eval_delta": 120.0,
      "notes": "Auto-matched: mistake at ply 15",
      "priority": 1,
      "priority_label": "recurring_acknowledged"
    }
  ],
  "summary": {
    "total_matched": 3,
    "recurring_acknowledged": 1,
    "new_patterns": 1
  }
}
```

### `GET /api/notifications/recent`

Get notifications from the most recently analyzed game.

**Response:** Same format as `GET /api/games/{game_id}/notifications`.

---

## Progress

### `GET /api/progress`

Get all progress snapshots over time.

**Response:**
```json
{
  "snapshots": [
    {
      "id": 1,
      "date": "2026-03-06",
      "total_games": 50,
      "avg_accuracy": 72.3,
      "accuracy_opening": 75.0,
      "accuracy_middlegame": 68.0,
      "accuracy_endgame": 55.0,
      "acknowledged_patterns": 3,
      "recurring_patterns": 1,
      "resolved_patterns": 2,
      "session_id": "2026-03-06",
      "patterns_json": "{...}"
    }
  ]
}
```

### `GET /api/progress/summary`

Get current aggregate stats with per-phase accuracy and pattern counts.

**Response:**
```json
{
  "total_games": 50,
  "total_moves": 2500,
  "accuracy": 72.3,
  "phase_accuracy": {
    "opening": 75.0,
    "middlegame": 68.0,
    "endgame": 55.0
  },
  "active_patterns": 5,
  "acknowledged_patterns": 3,
  "recurring_patterns": 1,
  "resolved_patterns": 2
}
```

### `GET /api/progress/sessions`

List play sessions grouped by date with summary stats.

**Response:**
```json
{
  "sessions": [
    {
      "date": "2026-03-06",
      "games": 5,
      "wins": 3,
      "losses": 1,
      "draws": 1,
      "accuracy": 74.2
    }
  ]
}
```

### `GET /api/progress/compare`

Compare two time periods side by side. Compares [from_date, to_date] vs the equivalent prior period.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_date` | string | yes | Start date (YYYY-MM-DD) |
| `to_date` | string | yes | End date (YYYY-MM-DD) |

**Response:**
```json
{
  "current_period": {
    "from": "2026-03-01",
    "to": "2026-03-06",
    "games": 10,
    "accuracy": 74.0,
    "phase_accuracy": {"opening": 75.0, "middlegame": 70.0},
    "wins": 6, "losses": 3, "draws": 1
  },
  "prior_period": {
    "from": "2026-02-23",
    "to": "2026-02-28",
    "games": 8,
    "accuracy": 68.0,
    "phase_accuracy": {"opening": 70.0, "middlegame": 65.0},
    "wins": 4, "losses": 3, "draws": 1
  },
  "delta": {
    "accuracy": 6.0,
    "games": 2,
    "improving": true
  }
}
```

---

## Workflows

### `GET /api/workflows`

List all registered workflows (loaded from YAML definitions).

**Response:**
```json
{
  "workflows": [
    {
      "name": "full_game_analysis",
      "description": "End-to-end analysis of a single game",
      "trigger": "on_import",
      "version": 1,
      "steps": 7
    }
  ]
}
```

### `GET /api/workflows/{name}`

Get full workflow definition.

### `GET /api/workflows/{name}/runs`

Get run history for a workflow.

**Query Parameters:** `limit` (int, default 10)

### `POST /api/workflows/{name}/execute`

Trigger a workflow execution with optional parameters.

**Request Body (optional):** `{"game_id": "uuid"}`

**Response:**
```json
{
  "run_id": "uuid",
  "workflow": "new_game_comparison",
  "status": "completed",
  "step_count": 5
}
```

### `GET /api/workflows/runs/{run_id}`

Get specific run status with step results.

---

## Chat

### `POST /api/chat/stream`

SSE endpoint for streaming chat with the chess coach agent.

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "What are my worst openings?"}
  ]
}
```

**SSE Events:**
```
data: {"type": "text_delta", "text": "Based on your data..."}
data: {"type": "tool_call", "name": "get_openings_ranked"}
data: {"type": "tool_result", "name": "get_openings_ranked", "summary": "received 450 chars"}
data: {"type": "done"}
```

Event types: `text_delta`, `tool_call`, `tool_result`, `done`, `error`
