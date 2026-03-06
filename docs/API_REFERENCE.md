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

Upload a PGN file containing one or more games.

**Request:** Multipart file upload (field: `file`)

**Response:**
```json
{"status": "ok", "imported": 3, "skipped": 1}
```

### `POST /api/games/import/lichess`

Import games from Lichess for a given user.

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

Submit a game for pattern comparison. **Status: Stubbed (returns queued status).**

**Query Parameters:** `game_id` (string)

**Response:** `{"status": "queued", "game_id": "uuid"}`

### `GET /api/analyze/status/{job_id}`

Check status of an analysis job.

**Response:**
```json
{
  "job_id": "uuid",
  "workflow": "full_game_analysis",
  "status": "running",
  "started_at": "2026-03-06T10:00:00",
  "completed_at": null
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
      "patterns_json": "{...}"
    }
  ]
}
```

### `GET /api/progress/summary`

Get current aggregate stats.

**Response:**
```json
{
  "total_games": 50,
  "total_moves": 2500,
  "accuracy": 72.3,
  "active_patterns": 5
}
```

---

## Workflows

### `GET /api/workflows`

List registered workflows. **Status: Stubbed (returns empty list).**

### `GET /api/workflows/{name}`

Get workflow definition. **Status: Stubbed.**

### `GET /api/workflows/{name}/runs`

Get run history for a workflow.

**Query Parameters:** `limit` (int, default 10)

### `POST /api/workflows/{name}/execute`

Trigger a workflow. **Status: Stubbed.**

### `GET /api/workflows/runs/{run_id}`

Get specific run status.

---

## Planned Endpoints (from SRS, not yet implemented)

| Method | Path | Description | SRS Ref |
|--------|------|-------------|---------|
| GET | `/api/reports/mistakes` | Categorized mistake report (phase x type matrix) | FR-CAT-3 |
| GET | `/api/reports/repeated` | Repeated mistakes by frequency | FR-CAT-4 |
| GET | `/api/games/{id}/notifications` | Pattern-match notifications for a game | FR-NOT-2 |
| GET | `/api/notifications/recent` | Notifications from latest analysis | FR-NOT-3 |
| POST | `/api/patterns/{id}/acknowledge` | Acknowledge a pattern | FR-ACK-1 |
| DELETE | `/api/patterns/{id}/acknowledge` | Revoke acknowledgment | FR-ACK-1 |
| POST | `/api/patterns/{id}/resolve` | Mark pattern resolved | FR-ACK-4 |
| GET | `/api/patterns/acknowledged` | List acknowledged patterns | FR-ACK-2 |
| GET | `/api/progress/sessions` | Session-based game grouping | FR-PRG-2 |
| GET | `/api/progress/compare` | Period comparison | FR-PRG-4 |
