"""API endpoints for mistake reports."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.mistake_reporter import (
    get_mistake_matrix,
    get_mistake_trends,
    get_repeated_mistakes,
)

router = APIRouter()


@router.get("/mistakes")
async def mistake_report(
    phase: str | None = None,
    type: str | None = Query(None, alias="type"),
    game_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Categorized mistake report (phase x type matrix).

    Optional filters: phase, type, game_id.
    """
    result = get_mistake_matrix(db, game_id=game_id)

    # Apply filters if requested
    if phase and phase in result["matrix"]:
        result["matrix"] = {phase: result["matrix"][phase]}
    if type:
        filtered = {}
        for p, types in result["matrix"].items():
            if type in types:
                filtered[p] = {type: types[type]}
        result["matrix"] = filtered

    return result


@router.get("/repeated")
async def repeated_mistakes(
    min_frequency: int = 2,
    db: Session = Depends(get_db),
):
    """Repeated mistakes ordered by frequency."""
    patterns = get_repeated_mistakes(db, min_frequency=min_frequency)
    return {"patterns": patterns, "total": len(patterns)}


@router.get("/trends")
async def mistake_trends(
    period_games: int = 10,
    db: Session = Depends(get_db),
):
    """Accuracy trends by phase, comparing recent vs older games."""
    return get_mistake_trends(db, period_games=period_games)
