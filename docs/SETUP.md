# Developer Setup
# Chess Trainer Agent

---

## Prerequisites

- Python 3.11+
- Stockfish chess engine binary
- Anthropic API key (for Claude integration)
- Lichess API token (optional, for game import)

---

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd chess_trainer_agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
pip install -e ".[dev]"
```

---

## Stockfish Setup

Download Stockfish from https://stockfishchess.org/download/ and either:

1. Place the binary in `bin/stockfish` (gitignored), or
2. Install system-wide and set the `STOCKFISH_PATH` env var

---

## Environment Configuration

Copy the example and fill in your values:

```bash
cp .env.example .env
```

### Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key for pattern analysis |
| `LICHESS_TOKEN` | No | - | Lichess personal API token for game import |
| `STOCKFISH_PATH` | No | "stockfish" | Path to Stockfish binary |
| `ENGINE_DEPTH` | No | 20 | Stockfish search depth (higher = slower, more accurate) |
| `CLAUDE_MODEL` | No | "claude-sonnet-4-20250514" | Claude model to use |
| `DATABASE_URL` | No | sqlite:///backend/chess_trainer.db | SQLAlchemy database URL |

---

## Running the Backend

```bash
# Development mode with auto-reload
uvicorn backend.main:app --reload

# Production mode
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

On first startup, the app will:
1. Create all database tables
2. Seed the mistake category taxonomy

---

## Running the Workflow MCP Server

```bash
cd workflow-mcp
python server.py
```

Note: The workflow server is standalone and not yet connected to the backend.

---

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_engine.py

# Run specific test
pytest tests/test_engine.py::test_classify_move
```

### Test Files

| File | Tests |
|------|-------|
| `tests/test_pgn_parser.py` | PGN parsing, date handling, multi-game files |
| `tests/test_classifier.py` | Move classification thresholds, phase detection |
| `tests/test_engine.py` | Stockfish engine integration |
| `tests/test_models.py` | ORM model creation, relationships |
| `tests/test_analysis_worker.py` | Full analysis pipeline |
| `tests/test_seed.py` | Mistake category seeding |

---

## Linting

```bash
# Check for lint errors
ruff check .

# Auto-fix
ruff check --fix .
```

Configuration in `pyproject.toml`:
- Line length: 100
- Target: Python 3.11
- Rules: E (pycodestyle), F (pyflakes), I (isort), W (warnings)

---

## Project Structure

```
chess_trainer_agent/
├── backend/           # FastAPI application
│   ├── main.py        # App entry point
│   ├── config.py      # Settings
│   ├── database.py    # DB setup
│   ├── models.py      # ORM models
│   ├── seed.py        # Initial data
│   ├── routers/       # API endpoints
│   ├── services/      # Business logic
│   └── tasks/         # Background workers
├── workflow-mcp/      # Workflow MCP server
├── frontend/          # React app (not yet implemented)
├── tests/             # Test suite
├── docs/              # Documentation
├── bin/               # Binaries (gitignored)
├── pyproject.toml     # Build config
└── requirements.txt   # Flat deps
```

---

## Common Tasks

### Import games from Lichess

```bash
curl -X POST "http://localhost:8000/api/games/import/lichess?username=YOUR_USERNAME&max_games=10"
```

### Trigger analysis (manual)

Games are not automatically analyzed on import. The analysis worker needs to be called programmatically or via the API. Currently, you can trigger analysis by calling `analyze_game(game_id)` from `backend/tasks/analysis_worker.py`.

### Check progress

```bash
curl http://localhost:8000/api/progress/summary
```

### Refresh opening stats

```bash
curl -X POST http://localhost:8000/api/openings/refresh
```
