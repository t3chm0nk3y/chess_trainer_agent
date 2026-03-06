# CLAUDE.md - Project Instructions for Claude Code

## Project Overview

Chess Trainer Agent: a personal chess coaching app that analyzes game history, identifies recurring mistakes, and tracks improvement. See `docs/SRS.md` for the full specification.

## Development Journal Process

**You MUST follow the development journal process defined in `docs/DEVELOPMENT_JOURNAL.md`.** This is critical for continuity across sessions.

### Before Starting Work

1. Read `docs/PROGRESS.md` to understand current state, active tasks, and blockers
2. Read the most recent daily log entry to understand what was last worked on
3. Check for any `[!]` (blocked) tasks that may need attention

### During Work

1. Update task checkboxes in `docs/PROGRESS.md` as you work:
   - `[ ]` not started -> `[~]` in progress -> `[x]` complete
   - `[!]` if blocked (record reason in daily log immediately)
2. When making non-obvious design choices, record them in `docs/DECISIONS.md` using the ADR format described in `docs/DEVELOPMENT_JOURNAL.md`
3. If you change architecture, API, or data model, update the corresponding doc in `docs/`

### After Completing Work

1. Write a daily log entry in `docs/PROGRESS.md` with: Completed, In Progress, Decisions, Blockers, Next Steps
2. Update `docs/DOC_PLAN.md` change tracking table if any documentation was modified
3. Ensure all modified docs accurately reflect the current code

## Key Documents

| Document | Purpose |
|----------|---------|
| `docs/SRS.md` | Ground truth requirements spec |
| `docs/PROGRESS.md` | Phase checklist + daily work log |
| `docs/DEVELOPMENT_JOURNAL.md` | Process for recording work |
| `docs/ARCHITECTURE.md` | System design and component relationships |
| `docs/API_REFERENCE.md` | REST API endpoints and schemas |
| `docs/DATA_MODEL.md` | Database tables and relationships |
| `docs/SERVICES.md` | Backend service layer docs |
| `docs/WORKFLOWS.md` | Workflow MCP system |
| `docs/SETUP.md` | Developer setup guide |

## Tech Stack

- Backend: Python 3.11+ / FastAPI / SQLAlchemy / SQLite
- Engine: Stockfish via python-chess (direct integration, not MCP)
- AI: Claude API (anthropic SDK) for annotation and pattern synthesis
- Frontend: React 19 / Vite (planned, not yet implemented)
- Workflows: FastMCP server with YAML definitions (defined, not yet wired)

## Common Commands

```bash
# Run backend
uvicorn backend.main:app --reload

# Run tests
pytest

# Lint
ruff check .
ruff check --fix .
```

## Code Conventions

- Line length: 100 (configured in pyproject.toml)
- Lint rules: E, F, I, W via ruff
- Tests in `tests/` directory, pytest with asyncio_mode=auto
- A task is "done" when: code passes ruff, tests exist and pass, API returns correct responses
