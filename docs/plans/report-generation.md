# Plan: Report Generation System

## Context

The chess trainer has 1512 games with complete engine analysis, ~620 with AI annotations (in progress), and conditions pending. A future chat agent will need structured context about the player's chess profile. Pre-generated reports provide dense, queryable summaries without the agent having to re-derive insights from raw data each conversation.

Goal: Generate ~100 reports across 7 categories, stored in a `reports` table, accessible via API. Generate engine-only reports now; regenerate with richer data as annotation and conditions complete.

---

## Report Categories (~100 reports)

| Category | Count | Key Format | Data Source |
|---|---|---|---|
| Player Profile | 1 | `overview` | Engine |
| Opening Reports | 30-40 | `{eco}_{name}_{variation}` | Engine + OpeningStats |
| Pattern Reports | ~48 | `{registry_pattern_id}` | Engine + Pattern table |
| Monthly Summaries | 12-18 | `YYYY-MM` | Engine |
| Phase Reports | 3 | `opening`/`middlegame`/`endgame` | Engine |
| Game Condition Reports | 0-10 | `{registry_pattern_id}` | Engine + GameCondition |
| Weakness Reports | 5 | `tactical`/`strategic`/`openings`/`color`/`time_control` | Engine + Pattern |

---

## Step 1: Report Model

**Modify: `models.py`**

Add `Report` class:
- `id` (int, PK)
- `report_type` (String) — `player_profile`, `opening`, `pattern`, `monthly`, `phase`, `game_condition`, `weakness`
- `report_key` (String) — unique identifier within type
- `title` (String)
- `category` (String) — human-readable label
- `data` (Text) — JSON string
- `generated_at` (DateTime)
- `data_coverage` (String, nullable) — `engine_only`, `partial_annotations`, `full`
- UniqueConstraint on `(report_type, report_key)`

Table auto-created by `init_db()` via `Base.metadata.create_all`.

---

## Step 2: Report Generator Service

**Create: `services/report_generator.py`**

### Core functions:

```python
async def generate_all_reports(db: AsyncSession) -> int
async def _upsert_reports(db: AsyncSession, reports: list[ReportTuple]) -> int
async def _detect_coverage(db: AsyncSession) -> str  # engine_only|partial_annotations|full
```

### Generator functions (one per category):

**`generate_player_profile(db)`** — 1 report
- Total games, W/L/D counts and percentages
- Color performance (as white vs black): games, wins, losses, draws, win_rate
- Time control breakdown: games and win_rate per time_control
- Accuracy by phase: avg cp_loss for opening/middlegame/endgame moves
- Severity distribution: total inaccuracies, mistakes, blunders
- Top 10 most played openings with win_rate
- Pipeline status counts

**`generate_opening_reports(db)`** — 30-40 reports
- Requires OpeningStats to be computed (compute if empty)
- Per opening line: W/L/D, loss_rate, avg_cp_loss_opening, divergence point
- Additional: severity counts in opening-phase moves for those games
- Pattern cross-references when annotation data available

**`generate_pattern_reports(db)`** — ~48 reports
- Per Pattern record: name, phase, axis, frequency, games_affected
- Example FEN and annotation
- 5 most recent occurrences from MovePatternMatch (game_id, move_number, annotation)

**`generate_monthly_reports(db)`** — 12-18 reports
- Group games by year-month from `played_at`
- Per month: games, W/L/D, win_rate
- Avg cp_loss overall and by phase
- Severity counts, blunder rate per game
- Best/worst openings (top 3 each by win_rate, min 3 games)
- New patterns first seen that month

**`generate_phase_reports(db)`** — 3 reports
- Per phase: total moves, avg cp_loss, severity distribution
- Mistakes per game average
- Top patterns in that phase (from Pattern table)
- Trend: compare last 200 games vs older for avg cp_loss, with direction label

**`generate_game_condition_reports(db)`** — 0-10 reports
- Per GameCondition type with Pattern record: occurrence count, W/L/D
- Loss rate under condition vs overall loss rate (delta)
- Avg move number when detected
- Player was worse percentage

**`generate_weakness_reports(db)`** — 5 reports
- `tactical`: Top 10 tactical patterns by frequency with trend
- `strategic`: Top 10 strategic patterns by frequency with trend
- `openings`: Top 5 worst openings by loss_rate (min 5 games)
- `color`: White vs black comparison across all metrics
- `time_control`: Performance comparison across time controls

### Key design choices:
- Report key sanitization: lowercase, spaces to underscores, strip non-alphanumeric, truncate to 100 chars
- Data is compact summaries (counts, percentages, top-N), not raw dumps
- `data_coverage` auto-detected from annotation/condition completion rates

---

## Step 3: API Router

**Create: `routers/reports.py`**

```
GET  /api/reports                      — List all reports (metadata only, no data field)
GET  /api/reports?report_type=opening  — Filter by type
GET  /api/reports/{report_type}/{key}  — Get single report with full data
POST /api/reports/generate             — Regenerate all reports
```

**Modify: `main.py`** — Add `from routers import reports` and `app.include_router(reports.router)`

---

## Step 4: CLI Script

**Create: `scripts/generate_reports.py`**

```
Usage: .venv/bin/python scripts/generate_reports.py [--type all|player_profile|opening|pattern|monthly|phase|game_condition|weakness]
```

Follows `scripts/run_pipeline.py` pattern. Default `--type all`.

---

## Step 5: API Client + Dashboard Integration

**Modify: `frontend/src/api/client.js`** — Add `listReports()`, `getReport(type, key)`

Optional: Add report count to dashboard stats row.

---

## Files Summary

| Action | File |
|--------|------|
| Modify | `models.py` — Add Report model |
| Create | `services/report_generator.py` — All generator functions |
| Create | `routers/reports.py` — API endpoints |
| Create | `scripts/generate_reports.py` — CLI runner |
| Modify | `main.py` — Register reports router |
| Modify | `frontend/src/api/client.js` — Add report API functions |

---

## Verification

1. `ruff check .` — lint clean
2. `pytest tests/ -x` — all existing tests pass
3. `.venv/bin/python scripts/generate_reports.py --type all` — generates ~100 reports
4. `curl /api/reports` — returns report list with metadata
5. `curl /api/reports/player_profile/overview` — returns full player profile with data
6. Each report has `data_coverage: "engine_only"` (until annotation/conditions complete)

---

## Dependencies

- OpeningStats must be computed before opening reports (generator will trigger computation if table is empty)
- Pattern reports use whatever Pattern records exist (~48 currently)
- Game condition reports will be empty until condition pipeline runs — regenerate after
- Monthly reports only use engine data, available now for all 1512 games
