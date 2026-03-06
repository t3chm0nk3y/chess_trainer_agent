from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db

router = APIRouter()


@router.get("")
async def list_workflows():
    """List all registered workflows."""
    # TODO: read from workflow MCP
    return {"workflows": []}


@router.get("/{name}")
async def get_workflow(name: str):
    """Get workflow definition."""
    # TODO: read from workflow MCP
    return {"name": name, "steps": []}


@router.get("/{name}/runs")
async def workflow_runs(name: str, limit: int = 10, db: Session = Depends(get_db)):
    """Run history for a workflow."""
    from backend.models import WorkflowRun

    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_name == name)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [
            {
                "id": r.id,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]
    }


@router.post("/{name}/execute")
async def execute_workflow(name: str, params: dict | None = None, db: Session = Depends(get_db)):
    """Trigger a workflow execution."""
    # TODO: create WorkflowRun, dispatch to workflow MCP
    return {"status": "queued", "workflow": name}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db)):
    """Status of a specific run."""
    from backend.models import WorkflowRun

    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": run.id,
        "workflow": run.workflow_name,
        "status": run.status,
        "parameters": run.parameters_json,
        "step_results": run.step_results_json,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
