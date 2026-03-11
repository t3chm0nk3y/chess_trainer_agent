# Setup & Operations Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Stockfish binary (at `bin/stockfish` or set `STOCKFISH_PATH`)
- Anthropic API key
- Lichess API token

## Installation

```bash
# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Frontend
cd frontend && npm install && cd ..
```

## Environment Variables

Create `.env` in project root:

```
ANTHROPIC_API_KEY=sk-ant-...
LICHESS_TOKEN=lip_...
LICHESS_USERNAME=your_username
STOCKFISH_PATH=bin/stockfish
STOCKFISH_DEPTH=18
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key for pattern annotation |
| `LICHESS_TOKEN` | Yes | — | Lichess personal API token |
| `LICHESS_USERNAME` | Yes | — | Lichess username to import games for |
| `STOCKFISH_PATH` | Yes | — | Path to Stockfish binary |
| `STOCKFISH_DEPTH` | No | 18 | Stockfish search depth |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./chess_trainer.db` | Database URL |
| `CP_LOSS_INACCURACY` | No | 50 | Centipawn loss threshold for inaccuracy |
| `CP_LOSS_MISTAKE` | No | 100 | Centipawn loss threshold for mistake |
| `CP_LOSS_BLUNDER` | No | 200 | Centipawn loss threshold for blunder |
| `MAX_RETRIES` | No | 5 | Max retry attempts for failed analysis |
| `REGISTRY_PATH` | No | `registry/patterns.yaml` | Path to pattern registry |

---

## Running the App

```bash
# Backend (from project root)
uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend && npm run dev
```

- Backend API: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:5173 (proxies `/api` to backend)

---

## Analysis Pipeline

The pipeline has three layers that run sequentially per game. Each layer is independent and safe to re-run.

```
Import → Engine Analysis → Annotation → Condition Detection → Opening Stats
         (Stockfish)        (Claude AI)   (deterministic)      (aggregation)
```

### Step 1: Import Games

```bash
# Via API
curl -X POST http://localhost:8000/api/games/import

# Via script
.venv/bin/python scripts/import_and_analyze.py
```

This imports all rated games from Lichess and deduplicates by `lichess_id`.

### Step 2: Engine Analysis (Stockfish)

Evaluates every move with Stockfish. Sets `cp_eval`, `cp_loss`, `best_move`, `mistake_severity`. This is the slowest step (~2-3 games/minute at depth 18).

```bash
# Run on all pending games (long-running, ~10hrs for 1500 games)
.venv/bin/python scripts/run_engine.py
```

Engine data is **immutable** once complete — never re-evaluated.

### Step 3: Annotation (Claude AI)

Classifies each mistake move against the 61-pattern registry using Claude. Creates `MovePatternMatch` records. Requires `ANTHROPIC_API_KEY`.

```bash
# Run on all engine-complete, annotation-pending games
.venv/bin/python scripts/run_pipeline.py --stage annotation
```

### Step 4: Condition Detection

Detects structural game conditions (GC-001 through GC-010) from move data. No external API calls — purely deterministic. Creates `GameCondition` records.

```bash
.venv/bin/python scripts/run_pipeline.py --stage conditions
```

### Step 5: Opening Stats

Aggregates W/L/D, avg CP loss, and divergence moves by opening line. Full recompute each time.

```bash
.venv/bin/python scripts/run_pipeline.py --stage openings
```

### Run All Post-Engine Stages

```bash
.venv/bin/python scripts/run_pipeline.py --stage all
```

This runs annotation → conditions → openings in order.

### Incremental Processing

All stages are safe to run repeatedly:
- **Engine**: skips games with `engine_status != "pending"`
- **Annotation**: skips games already annotated; uses `PatternScanLog` to skip scanned patterns
- **Conditions**: skips games with `condition_status != "pending"`; unique constraint prevents duplicates
- **Openings**: full recompute (deletes and reinserts)

So the typical workflow after initial import is:
1. Start engine analysis in background
2. Periodically run `scripts/run_pipeline.py --stage all` to process completed games
3. Re-run after engine finishes to catch remaining games

---

## Monitoring Progress

```bash
# Analysis status (games per layer status)
curl http://localhost:8000/api/analysis/status

# Failed games
curl http://localhost:8000/api/analysis/failed

# Coverage report
curl http://localhost:8000/api/admin/coverage

# Stuck jobs (running > 30 min)
curl http://localhost:8000/api/admin/stuck

# Retry all failed
curl -X POST http://localhost:8000/api/analysis/retry-failed
```

---

## API Endpoints

### Games
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/games/import` | Import from Lichess |
| GET | `/api/games` | List games (paginated) |
| GET | `/api/games/{id}` | Full game with moves + conditions |
| GET | `/api/games/{id}/mistakes` | Mistake moves with pattern matches |
| GET | `/api/games/{id}/recurring` | Recurring pattern matches |

### Analysis
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analysis/run` | Check pending count |
| GET | `/api/analysis/status` | Status counts per layer |
| GET | `/api/analysis/failed` | Failed/needs-review games |
| POST | `/api/analysis/retry-failed` | Re-queue all failed |

### Patterns
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/patterns` | All patterns by frequency |
| GET | `/api/patterns/report` | Phase × axis matrix |
| GET | `/api/patterns/conditions` | Game conditions with W/L/D |
| GET | `/api/patterns/{id}` | Pattern with occurrences |

### Openings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/openings` | All lines by loss rate |
| GET | `/api/openings/{eco}` | Variations for one ECO code |
| POST | `/api/openings/compute` | Recompute stats |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/registry` | Full pattern registry as JSON |
| POST | `/api/admin/registry/reload` | Reload YAML + queue re-scans |
| GET | `/api/admin/coverage` | Coverage report |
| GET | `/api/admin/scan-log` | Pattern scan coverage matrix |
| GET | `/api/admin/stuck` | Stuck jobs |
| POST | `/api/admin/reprocess/game/{id}` | Re-queue one game |
| POST | `/api/admin/reprocess/pattern/{id}` | Queue re-scan for pattern |

---

## Tests

```bash
pytest                    # all tests
pytest -v                 # verbose
pytest tests/test_foo.py  # specific file
ruff check .              # lint
```

| File | Coverage |
|------|----------|
| `test_pipeline.py` | PGN parsing, move creation, engine analysis |
| `test_deduplication.py` | Lichess import dedup |
| `test_classifier.py` | Phase assignment, severity thresholds |
| `test_registry.py` | YAML loading, pattern filtering |
| `test_annotator.py` | Claude API mocking, JSON parsing |
| `test_conditions.py` | Game condition detection, scanner, admin endpoints |
| `test_opening_stats.py` | Opening aggregation, divergence, API |
| `test_retry.py` | Retry worker, stuck reset, exceeded retries |
