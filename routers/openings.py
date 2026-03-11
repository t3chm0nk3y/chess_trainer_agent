"""/api/openings — opening line statistics."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import OpeningStats
from services.opening_stats import compute_opening_stats

router = APIRouter(prefix="/api/openings", tags=["openings"])


def _stats_to_dict(s: OpeningStats) -> dict:
    return {
        "id": s.id,
        "eco_code": s.eco_code,
        "opening_name": s.opening_name,
        "variation_name": s.variation_name,
        "total_games": s.total_games,
        "wins": s.wins,
        "losses": s.losses,
        "draws": s.draws,
        "win_rate": s.win_rate,
        "loss_rate": s.loss_rate,
        "avg_cp_loss_opening": s.avg_cp_loss_opening,
        "divergence_move": s.divergence_move,
        "divergence_san": s.divergence_san,
        "last_computed_at": s.last_computed_at.isoformat() if s.last_computed_at else None,
    }


@router.get("")
async def list_openings(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """All OpeningStats sorted by loss_rate desc."""
    result = await db.execute(
        select(OpeningStats)
        .order_by(OpeningStats.loss_rate.desc())
        .limit(limit)
        .offset(offset)
    )
    stats = result.scalars().all()
    return {"openings": [_stats_to_dict(s) for s in stats]}


@router.get("/{eco_code}")
async def get_opening_by_eco(eco_code: str, db: AsyncSession = Depends(get_db)):
    """All variations for one ECO code."""
    result = await db.execute(
        select(OpeningStats)
        .where(OpeningStats.eco_code == eco_code)
        .order_by(OpeningStats.loss_rate.desc())
    )
    stats = result.scalars().all()
    if not stats:
        raise HTTPException(status_code=404, detail=f"No openings found for {eco_code}")
    return {"eco_code": eco_code, "variations": [_stats_to_dict(s) for s in stats]}


@router.post("/compute")
async def compute_openings(db: AsyncSession = Depends(get_db)):
    """Recompute all opening stats from engine-complete games."""
    count = await compute_opening_stats(db)
    return {"lines_computed": count}
