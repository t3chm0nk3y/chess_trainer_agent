# Workflows
# Chess Trainer Agent

The workflow system uses YAML definitions to describe multi-step analysis pipelines. The backend executes these via `workflow_executor.py`.

---

## Architecture

```
workflow-mcp/
├── server.py      # FastMCP server (standalone, not used by backend)
├── models.py      # Workflow/WorkflowRun dataclasses
├── store.py       # In-memory store + YAML file loader
└── workflows/     # YAML workflow definitions
    ├── full_game_analysis.yaml
    ├── new_game_comparison.yaml
    ├── pattern_synthesis.yaml
    ├── import_lichess_games.yaml
    ├── import_chesscom_games.yaml
    └── weekly_progress_report.yaml
```

### Execution Engine

The backend implements its own workflow executor (`backend/services/workflow_executor.py`) rather than connecting to the MCP server as a client. This avoids MCP transport complexity while reusing the YAML workflow definitions.

The executor:
1. Loads YAML definitions from `workflow-mcp/workflows/` (cached at startup)
2. Creates a `WorkflowRun` DB record for persistence
3. Resolves `{{ variable }}` templates against input parameters and step results
4. Dispatches each step to a handler via the tool registry (28 handlers)
5. Records step-by-step results as JSON in the `WorkflowRun` record

---

## Template Syntax

Workflow inputs use `{{ }}` template syntax:

- **`{{ variable }}`** -- Resolves to an input parameter
- **`{{ step_N.field }}`** -- Resolves to a field from step N's result

Templates can appear in string values, returning the resolved object if the template fills the entire string, or interpolating within a larger string.

---

## Tool Registry

The executor maps YAML tool names to Python handler functions:

| Tool Name | Handler | Description |
|-----------|---------|-------------|
| `database.fetch_game` | Queries Game by ID | Returns pgn, game_id, player_color |
| `database.fetch_patterns` | Queries unresolved Patterns | Returns pattern list |
| `database.query_analyzed_games` | Queries analyzed games | Returns game list + count |
| `database.fetch_recent_games` | Queries games by date | Returns recent game IDs |
| `database.store_analysis` | No-op passthrough | Analysis stored by worker |
| `database.update_status` | Updates Game.analysis_status | |
| `database.deduplicate` | No-op passthrough | Handled by _store_parsed_games |
| `database.store_games` | No-op passthrough | |
| `database.update_patterns` | No-op passthrough | |
| `database.update_pattern_frequencies` | No-op passthrough | |
| `analysis.queue_batch` | Calls queue_analysis() | Queues games for analysis |
| `chessagine.analyze_game` | Calls _analyze_game_sync() | Full Stockfish analysis |
| `classifier.classify_moves` | No-op passthrough | Handled by worker |
| `classifier.detect_phases` | No-op passthrough | Handled by worker |
| `claude.annotate_mistakes` | No-op passthrough | Optional step |
| `claude.compare_new_game` | Calls match_game_to_patterns() | Pattern comparison |
| `claude.synthesize_patterns` | Calls run_pattern_synthesis() | Cross-game synthesis |
| `claude.generate_summary` | Returns placeholder | |
| `pattern_engine.aggregate_mistakes` | Calls gather_game_mistakes() | |
| `pattern_engine.build_summary` | Passthrough | |
| `pattern_engine.diff_patterns` | Passthrough | |
| `progress.calculate_delta` | Returns placeholder | |
| `progress.calculate_accuracy` | Queries Move accuracy | |
| `progress.compare_patterns` | Returns placeholder | |
| `progress.identify_trends` | Returns placeholder | |
| `progress.create_snapshot` | Calls create_progress_snapshot() | |
| `workflow.execute` | Recursive sub-workflow | |
| `lichess_mcp.export_games` | Calls lichess_api.fetch_games() | |
| `pgn_parser.parse` | Calls pgn_parser.parse_pgn() | |

---

## Workflow Definitions

### full_game_analysis (trigger: on_import)

End-to-end analysis of a single game. 7 steps:

1. Fetch game PGN from database
2. Analyze each position with Stockfish
3. Classify moves (best/good/inaccuracy/mistake/blunder)
4. Detect game phases (opening/middlegame/endgame)
5. Send mistakes to Claude for annotation
6. Store analysis results in database
7. Mark game as analyzed

**Note:** In practice, steps 2-7 are handled atomically by `analysis_worker._analyze_game_sync()`.

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

### weekly_progress_report (trigger: scheduled)

Generate a weekly progress summary.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/workflows` | List all registered workflows |
| GET | `/api/workflows/{name}` | Get workflow definition |
| GET | `/api/workflows/{name}/runs` | Run history for a workflow |
| POST | `/api/workflows/{name}/execute` | Trigger workflow execution |
| GET | `/api/workflows/runs/{run_id}` | Get specific run status |

---

## MCP Server (Standalone)

The `workflow-mcp/server.py` FastMCP server remains available as a standalone service but is not used by the backend. It can be run independently for testing or future MCP-based integrations:

```bash
cd workflow-mcp
python server.py
```
