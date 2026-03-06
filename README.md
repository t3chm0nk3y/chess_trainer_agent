# Chess Trainer Agent

A personal chess coaching application that analyzes game history, identifies recurring mistakes, and tracks improvement over time.

## What It Does

- **Imports games** from Lichess (Chess.com planned) or PGN file upload
- **Analyzes positions** with Stockfish engine evaluation
- **Classifies mistakes** by severity (inaccuracy/mistake/blunder), game phase (opening/middlegame/endgame), and type (tactical/strategic)
- **Identifies patterns** across games using Claude AI to find recurring weaknesses
- **Tracks progress** with accuracy snapshots and pattern resolution

## Architecture

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│   Frontend   │────>│  FastAPI Backend                             │
│  React 19    │     │  ┌────────────┐  ┌───────────┐  ┌─────────┐ │
│  + Vite      │     │  │  Routers   │  │ Services  │  │  Tasks  │ │
│  (planned)   │     │  │ games      │  │ engine    │  │ analysis│ │
│              │     │  │ openings   │  │ claude    │  │ worker  │ │
│              │     │  │ patterns   │  │ pgn_parse │  └─────────┘ │
│              │     │  │ analysis   │  │ classifier│              │
│              │     │  │ progress   │  │ pattern   │              │
│              │     │  │ workflows  │  │ opening   │              │
│              │     │  └────────────┘  │ lichess   │              │
│              │     │                  │ mcp_client│              │
│              │     │                  └───────────┘              │
└──────────────┘     └────────┬────────────────┬───────────────────┘
                              │                │
                    ┌─────────▼──┐    ┌────────▼────────┐
                    │  SQLite DB │    │ Workflow MCP     │
                    │            │    │ (FastMCP server) │
                    └────────────┘    │ YAML definitions │
                                      └─────────────────┘
External:
  - Stockfish 18 (local binary)
  - Claude API (Anthropic)
  - Lichess API
```

## Current Status

**Phase 1 (Foundation) is complete.** Games can be imported from Lichess, analyzed with Stockfish, and moves are classified with engine evaluations. See [docs/PROGRESS.md](docs/PROGRESS.md) for the full checklist.

Phases 2-6 (opening analysis, mistake categorization, notifications, acknowledgments, progress tracking, polish) are defined in the [SRS](docs/SRS.md) but not yet implemented.

## Quick Start

```bash
# Prerequisites: Python 3.11+, Stockfish binary

# Clone and set up
git clone <repo-url>
cd chess_trainer_agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys and Stockfish path

# Run
uvicorn backend.main:app --reload

# Test
pytest
```

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

## Documentation

| Document | Description |
|----------|-------------|
| [SRS](docs/SRS.md) | Software Requirements Specification (ground truth) |
| [Architecture](docs/ARCHITECTURE.md) | System design, component relationships, data flow |
| [API Reference](docs/API_REFERENCE.md) | REST endpoints with request/response schemas |
| [Data Model](docs/DATA_MODEL.md) | Database tables, relationships, field definitions |
| [Services](docs/SERVICES.md) | Backend service layer documentation |
| [Workflows](docs/WORKFLOWS.md) | Workflow MCP server and YAML definitions |
| [Setup](docs/SETUP.md) | Developer environment setup |
| [Progress](docs/PROGRESS.md) | Development phase checklist and daily log |
| [Dev Journal Process](docs/DEVELOPMENT_JOURNAL.md) | How to record work, decisions, and blockers |

## Tech Stack

- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy / SQLite
- **Frontend:** React 19 / Vite / react-chessboard / recharts (planned)
- **AI:** Claude API (Anthropic) for annotation and pattern synthesis
- **Engine:** Stockfish 18 via python-chess
- **Workflows:** FastMCP server with YAML-defined pipelines
- **External:** Lichess API for game import
