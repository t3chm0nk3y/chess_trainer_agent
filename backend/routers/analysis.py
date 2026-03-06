from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db

router = APIRouter()


@router.post("/compare")
async def compare_game(game_id: str, db: Session = Depends(get_db)):
    """Submit a new game and compare against known patterns."""
    # TODO: trigger new_game_comparison workflow
    return {"status": "queued", "game_id": game_id}


@router.get("/status/{job_id}")
async def analysis_status(job_id: str, db: Session = Depends(get_db)):
    """Poll async analysis job status."""
    from backend.models import WorkflowRun

    run = db.query(WorkflowRun).filter(WorkflowRun.id == job_id).first()
    if not run:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": run.id,
        "workflow": run.workflow_name,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
