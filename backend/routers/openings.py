"""API endpoints for opening line analysis."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.opening_analyzer import (
    compute_opening_stats,
    get_opening_detail,
    get_opening_stats_ranked,
)

router = APIRouter()


@router.get("")
async def list_openings(
    sort_by: str = "loss_pct",
    db: Session = Depends(get_db),
):
    """List all opening lines with win/loss/draw stats.

    Sorted by loss percentage by default. Other options:
    total_games, avg_cp_loss.
    """
    stats = get_opening_stats_ranked(db, sort_by=sort_by)
    return {"openings": stats, "total": len(stats)}


@router.get("/{eco_code}")
async def get_opening(
    eco_code: str,
    db: Session = Depends(get_db),
):
    """Drill-down into a specific opening by ECO code.

    Returns all variation lines, games, and divergence info.
    """
    detail = get_opening_detail(db, eco_code)
    if not detail:
        raise HTTPException(
            status_code=404,
            detail=f"No opening data found for ECO code {eco_code}",
        )
    return detail


@router.post("/refresh")
async def refresh_openings(db: Session = Depends(get_db)):
    """Recalculate opening statistics from all analyzed games."""
    stats = compute_opening_stats(db)
    return {
        "status": "ok",
        "openings_computed": len(stats),
    }
