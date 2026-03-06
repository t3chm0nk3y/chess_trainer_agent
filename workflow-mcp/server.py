"""Workflow MCP server — stores and manages analysis workflow definitions."""

import logging

from fastmcp import FastMCP

from workflow_mcp.models import Workflow, WorkflowRun
from workflow_mcp.store import WorkflowStore

logger = logging.getLogger(__name__)

mcp = FastMCP("Chess Trainer Workflows")
store = WorkflowStore()


@mcp.tool()
def workflow_list() -> list[dict]:
    """Returns all registered workflows with name, description, and trigger type."""
    return [
        {"name": w.name, "description": w.description, "trigger": w.trigger}
        for w in store.list_workflows()
    ]


@mcp.tool()
def workflow_get(name: str) -> dict | None:
    """Get full workflow definition with steps, parameters, and outputs."""
    w = store.get_workflow(name)
    if not w:
        return None
    return w.to_dict()


@mcp.tool()
def workflow_execute(name: str, params: dict | None = None) -> dict:
    """Start a workflow execution. Returns run_id for tracking."""
    run = store.create_run(name, params or {})
    return {"run_id": run.run_id, "status": run.status}


@mcp.tool()
def workflow_step_complete(run_id: str, step: int, result: dict) -> dict:
    """Record completion of a workflow step."""
    run = store.update_step(run_id, step, result)
    if not run:
        return {"error": "Run not found"}
    return {"run_id": run.run_id, "status": run.status, "steps_completed": len(run.step_results)}


@mcp.tool()
def workflow_run_status(run_id: str) -> dict | None:
    """Get current status of a workflow run."""
    run = store.get_run(run_id)
    if not run:
        return None
    return run.to_dict()


@mcp.tool()
def workflow_create(
    name: str,
    description: str,
    trigger: str,
    parameters: list[dict],
    steps: list[dict],
    outputs: list[str] | None = None,
) -> dict:
    """Register a new workflow definition."""
    w = Workflow(
        name=name,
        description=description,
        trigger=trigger,
        parameters=parameters,
        steps=steps,
        outputs=outputs or [],
        version=1,
    )
    store.save_workflow(w)
    return {"name": w.name, "version": w.version}


@mcp.tool()
def workflow_update(name: str, steps: list[dict] | None = None, **kwargs) -> dict:
    """Update a workflow definition (auto-increments version)."""
    w = store.get_workflow(name)
    if not w:
        return {"error": "Workflow not found"}
    if steps:
        w.steps = steps
    w.version += 1
    store.save_workflow(w)
    return {"name": w.name, "version": w.version}


@mcp.tool()
def workflow_history(name: str, limit: int = 10) -> list[dict]:
    """Recent runs for a workflow."""
    runs = store.list_runs(name, limit)
    return [r.to_dict() for r in runs]


if __name__ == "__main__":
    store.load_defaults()
    mcp.run()
