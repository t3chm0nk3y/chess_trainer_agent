# Workflows
# Chess Trainer Agent

The workflow system uses a FastMCP server to define and manage multi-step analysis pipelines.

---

## Architecture

```
workflow-mcp/
├── server.py      # FastMCP server exposing workflow tools
├── models.py      # Workflow, WorkflowRun, WorkflowStep dataclasses
├── store.py       # In-memory store + YAML file loader
└── workflows/     # YAML workflow definitions
    ├── full_game_analysis.yaml
    ├── new_game_comparison.yaml
    ├── pattern_synthesis.yaml
    ├── import_lichess_games.yaml
    ├── import_chesscom_games.yaml
    └── weekly_progress_report.yaml
```

### Current Status

The workflow MCP server is **fully implemented** as a standalone service. However, it is **not yet wired** to the backend -- the backend routers return stubbed responses and do not call the workflow MCP tools. Workflow execution (actually running the steps) is also not implemented.

---

## MCP Server Tools

The `server.py` exposes these FastMCP tools:

| Tool | Description |
|------|-------------|
| `workflow_list` | List all registered workflows |
| `workflow_get(name)` | Get full workflow definition |
| `workflow_execute(name, params)` | Start a workflow run |
| `workflow_step_complete(run_id, step, result)` | Record step completion |
| `workflow_run_status(run_id)` | Get run status |
| `workflow_create(...)` | Register a new workflow |
| `workflow_update(name, steps)` | Update workflow (auto-increments version) |
| `workflow_history(name, limit)` | Recent runs for a workflow |

### Running the Server

```bash
cd workflow-mcp
python server.py
```

This loads all YAML definitions from `workflows/` on startup.

---

## Data Model

### Workflow
- `name`: Unique identifier
- `description`: Human-readable purpose
- `trigger`: "manual", "on_import", or "scheduled"
- `parameters`: List of input parameter definitions
- `steps`: Ordered list of step definitions
- `outputs`: List of output names
- `version`: Auto-incrementing version number

### WorkflowStep
- `number`: Step sequence number
- `tool`: The tool/service to call (e.g. "chessagine.analyze_game")
- `description`: What this step does
- `input_map`: Template mapping for inputs (uses `{{ variable }}` syntax)

### WorkflowRun
- `run_id`: UUID
- `workflow_name`: Which workflow
- `parameters`: Input params for this run
- `status`: "running", "completed", "failed"
- `step_results`: List of per-step results
- `started_at` / `completed_at`: Timestamps

---

## Workflow Definitions

### full_game_analysis (trigger: on_import)

End-to-end analysis of a single game. 7 steps:

1. Fetch game PGN from database
2. Analyze each position with engine (originally ChessAgine MCP)
3. Classify moves (best/good/inaccuracy/mistake/blunder)
4. Detect game phases (opening/middlegame/endgame)
5. Send mistakes to Claude for annotation
6. Store analysis results in database
7. Mark game as analyzed

**Note:** Steps 2-4 are currently handled directly by `analysis_worker.py` instead of going through the workflow system.

### new_game_comparison (trigger: manual)

Analyze a game and compare against known patterns. 5 steps:

1. Execute full_game_analysis workflow
2. Fetch current pattern definitions
3. Send game mistakes + patterns to Claude for comparison
4. Update pattern frequencies and last_seen dates
5. Calculate delta vs historical averages

### pattern_synthesis (trigger: manual)

Cross-game pattern identification.

### import_lichess_games (trigger: manual)

Game import from Lichess.

### import_chesscom_games (trigger: manual)

Game import from Chess.com.

### weekly_progress_report (trigger: scheduled)

Generate a weekly progress summary.

---

## Store Layer

`WorkflowStore` provides an in-memory store:
- Workflow definitions are loaded from YAML files at startup
- Workflow runs are stored in memory (no persistence across restarts)
- The store supports CRUD operations and run tracking

The backend has a separate `WorkflowRun` ORM model in `backend/models.py` for persistent run tracking, but it is not yet connected to the workflow MCP store.

---

## Integration Gap

To complete workflow integration (Phase 6 in the SRS):

1. The backend needs to connect to the workflow MCP server (via `mcp_client.py` or direct function calls)
2. Workflow step execution needs to dispatch to actual service functions
3. The `{{ variable }}` template syntax in YAML input_maps needs an interpolation engine
4. Run results from the MCP store need to sync with the backend's `WorkflowRun` table
