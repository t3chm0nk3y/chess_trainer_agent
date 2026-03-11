"""/api/analysis — analysis status and control."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Game
from pipeline.retry import retry_failed_games

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/status")
async def analysis_status(db: AsyncSession = Depends(get_db)):
    """Count of games per engine/annotation/condition status combination."""
    engine_q = await db.execute(
        select(Game.engine_status, func.count(Game.id))
        .group_by(Game.engine_status)
    )
    engine_counts = {row[0]: row[1] for row in engine_q.all()}

    annotation_q = await db.execute(
        select(Game.annotation_status, func.count(Game.id))
        .group_by(Game.annotation_status)
    )
    annotation_counts = {row[0]: row[1] for row in annotation_q.all()}

    condition_q = await db.execute(
        select(Game.condition_status, func.count(Game.id))
        .group_by(Game.condition_status)
    )
    condition_counts = {row[0]: row[1] for row in condition_q.all()}

    total_q = await db.execute(select(func.count(Game.id)))
    total = total_q.scalar_one()

    return {
        "total_games": total,
        "engine": engine_counts,
        "annotation": annotation_counts,
        "condition": condition_counts,
    }


@router.post("/run")
async def run_analysis(db: AsyncSession = Depends(get_db)):
    """Queue all engine_status=pending games (returns count)."""
    result = await db.execute(
        select(func.count(Game.id)).where(Game.engine_status == "pending")
    )
    pending = result.scalar_one()
    return {"pending_games": pending, "message": "Use scripts/run_engine.py to process"}


@router.get("/failed")
async def get_failed_games(db: AsyncSession = Depends(get_db)):
    """Games with any layer in failed or needs_manual_review state."""
    result = await db.execute(
        select(Game).where(
            or_(
                Game.engine_status.in_(["failed", "needs_manual_review"]),
                Game.annotation_status.in_(["failed", "needs_manual_review"]),
                Game.condition_status.in_(["failed", "needs_manual_review"]),
            )
        )
    )
    games = result.scalars().all()
    return {
        "failed_games": [
            {
                "id": g.id,
                "lichess_id": g.lichess_id,
                "engine_status": g.engine_status,
                "annotation_status": g.annotation_status,
                "condition_status": g.condition_status,
                "failure_reason": g.engine_failure_reason,
                "failure_count": g.engine_failure_count,
            }
            for g in games
        ],
    }


@router.post("/retry-failed")
async def retry_failed(db: AsyncSession = Depends(get_db)):
    """Re-queue all failed games for retry."""
    count = await retry_failed_games(db)
    return {"games_retried": count}
