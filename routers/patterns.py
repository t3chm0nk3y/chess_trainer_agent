"""/api/patterns — pattern listing and reports."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import GameCondition, MovePatternMatch, Pattern

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("")
async def list_patterns(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """All Pattern records sorted by frequency desc."""
    count_result = await db.execute(select(func.count(Pattern.id)))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Pattern)
        .order_by(Pattern.frequency.desc())
        .limit(limit)
        .offset(offset)
    )
    patterns = result.scalars().all()

    return {
        "total": total,
        "patterns": [
            {
                "id": p.id,
                "registry_pattern_id": p.registry_pattern_id,
                "phase": p.phase,
                "axis": p.axis,
                "name": p.name,
                "frequency": p.frequency,
                "games_affected": p.games_affected,
                "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                "example_fen": p.example_fen,
                "example_annotation": p.example_annotation,
            }
            for p in patterns
        ],
    }


@router.get("/report")
async def pattern_report(db: AsyncSession = Depends(get_db)):
    """Frequency matrix: phase x axis."""
    result = await db.execute(select(Pattern))
    patterns = result.scalars().all()

    matrix = {}
    for phase in ("opening", "middlegame", "endgame"):
        matrix[phase] = {}
        for axis in ("tactical", "strategic"):
            matching = [
                p for p in patterns
                if p.phase == phase and p.axis == axis
            ]
            count = sum(p.frequency for p in matching)
            top = sorted(matching, key=lambda x: x.frequency, reverse=True)[:3]
            matrix[phase][axis] = {
                "count": count,
                "top": [
                    {"name": p.name, "frequency": p.frequency}
                    for p in top
                ],
            }

    return {"matrix": matrix}


@router.get("/conditions")
async def list_conditions(db: AsyncSession = Depends(get_db)):
    """Game condition Patterns with W/L/D aggregation, sorted by loss_rate."""
    # Get all condition patterns
    result = await db.execute(
        select(Pattern).where(Pattern.axis == "game_condition")
    )
    condition_patterns = result.scalars().all()

    items = []
    for p in condition_patterns:
        # Aggregate W/L/D from GameCondition records
        gc_result = await db.execute(
            select(GameCondition.game_result, func.count(GameCondition.id))
            .where(GameCondition.registry_pattern_id == p.registry_pattern_id)
            .group_by(GameCondition.game_result)
        )
        wld = {r[0]: r[1] for r in gc_result.all()}
        wins = wld.get("win", 0)
        losses = wld.get("loss", 0)
        draws = wld.get("draw", 0)
        total = wins + losses + draws
        loss_rate = losses / total if total > 0 else 0.0

        items.append({
            "registry_pattern_id": p.registry_pattern_id,
            "name": p.name,
            "total_games": total,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "loss_rate": round(loss_rate, 4),
            "frequency": p.frequency,
        })

    # Sort by loss_rate desc
    items.sort(key=lambda x: x["loss_rate"], reverse=True)
    return {"conditions": items}


@router.get("/{pattern_id}")
async def get_pattern(pattern_id: int, db: AsyncSession = Depends(get_db)):
    """Single pattern with all match records."""
    result = await db.execute(select(Pattern).where(Pattern.id == pattern_id))
    pattern = result.scalar_one_or_none()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Get all matches for this pattern
    matches_result = await db.execute(
        select(MovePatternMatch)
        .where(MovePatternMatch.registry_pattern_id == pattern.registry_pattern_id)
        .order_by(MovePatternMatch.matched_at.desc())
    )
    matches = matches_result.scalars().all()

    return {
        "id": pattern.id,
        "registry_pattern_id": pattern.registry_pattern_id,
        "phase": pattern.phase,
        "axis": pattern.axis,
        "name": pattern.name,
        "frequency": pattern.frequency,
        "games_affected": pattern.games_affected,
        "first_seen_at": pattern.first_seen_at.isoformat() if pattern.first_seen_at else None,
        "last_seen_at": pattern.last_seen_at.isoformat() if pattern.last_seen_at else None,
        "example_fen": pattern.example_fen,
        "example_annotation": pattern.example_annotation,
        "occurrences": [
            {
                "game_id": m.game_id,
                "move_id": m.move_id,
                "annotation": m.annotation,
                "matched_at": m.matched_at.isoformat() if m.matched_at else None,
            }
            for m in matches
        ],
    }
