"""/api/admin — registry management, coverage, reprocessing."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Game, PatternScanLog
from services.registry import get_registry, get_registry_version, reload_registry
from services.scanner import queue_rescan_for_pattern

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/registry")
async def get_registry_contents():
    """Full patterns.yaml contents as JSON."""
    registry = get_registry()
    return registry


@router.post("/registry/reload")
async def reload_registry_endpoint(db: AsyncSession = Depends(get_db)):
    """Parse YAML, queue re-scan for any new pattern IDs."""
    old_version = get_registry_version()
    registry = reload_registry()
    new_version = registry.get("registry_version", "unknown")

    # Find patterns that have no scan records for any game
    all_pattern_ids = [p["id"] for p in registry.get("patterns", []) if p.get("active", True)]

    new_patterns = []
    for pid in all_pattern_ids:
        scan_count = await db.execute(
            select(func.count(PatternScanLog.id))
            .where(PatternScanLog.registry_pattern_id == pid)
        )
        if scan_count.scalar_one() == 0:
            new_patterns.append(pid)

    # Mark games as having unscanned patterns
    games_queued = 0
    if new_patterns:
        result = await db.execute(
            select(Game).where(Game.engine_status == "complete")
        )
        games = result.scalars().all()
        for game in games:
            game.has_unscanned_patterns = True
            games_queued += 1
        await db.commit()

    return {
        "previous_version": old_version,
        "current_version": new_version,
        "new_patterns": new_patterns,
        "games_queued": games_queued,
    }


@router.get("/coverage")
async def get_coverage(db: AsyncSession = Depends(get_db)):
    """Game counts per status; unscanned pattern count."""
    engine_q = await db.execute(
        select(Game.engine_status, func.count(Game.id))
        .group_by(Game.engine_status)
    )
    engine = {r[0]: r[1] for r in engine_q.all()}

    annotation_q = await db.execute(
        select(Game.annotation_status, func.count(Game.id))
        .group_by(Game.annotation_status)
    )
    annotation = {r[0]: r[1] for r in annotation_q.all()}

    condition_q = await db.execute(
        select(Game.condition_status, func.count(Game.id))
        .group_by(Game.condition_status)
    )
    condition = {r[0]: r[1] for r in condition_q.all()}

    unscanned_q = await db.execute(
        select(func.count(Game.id))
        .where(Game.has_unscanned_patterns.is_(True))
    )
    unscanned = unscanned_q.scalar_one()

    return {
        "engine": engine,
        "annotation": annotation,
        "condition": condition,
        "games_with_unscanned_patterns": unscanned,
    }


@router.get("/scan-log")
async def scan_log_summary(db: AsyncSession = Depends(get_db)):
    """PatternScanLog summary: per-pattern game counts and match rates."""
    result = await db.execute(
        select(
            PatternScanLog.registry_pattern_id,
            func.count(PatternScanLog.id).label("games_scanned"),
            func.sum(PatternScanLog.match_count).label("total_matches"),
        )
        .group_by(PatternScanLog.registry_pattern_id)
    )
    rows = result.all()

    # Total engine-complete games for coverage calculation
    total_q = await db.execute(
        select(func.count(Game.id)).where(Game.engine_status == "complete")
    )
    total_games = total_q.scalar_one()

    items = []
    for pid, scanned, matches in rows:
        items.append({
            "registry_pattern_id": pid,
            "games_scanned": scanned,
            "total_matches": matches or 0,
            "total_games": total_games,
            "coverage": round(scanned / total_games, 4) if total_games > 0 else 0.0,
        })

    items.sort(key=lambda x: x["coverage"])
    return {"scan_log": items, "total_games": total_games}


class ReprocessRequest(BaseModel):
    from_layer: str = "engine"


@router.post("/reprocess/game/{game_id}")
async def reprocess_game(
    game_id: int,
    body: ReprocessRequest = ReprocessRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Re-queue a specific game from a named layer."""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    layer = body.from_layer
    if layer == "engine":
        game.engine_status = "pending"
        game.annotation_status = None
        game.condition_status = None
    elif layer == "annotation":
        if game.engine_status != "complete":
            raise HTTPException(
                status_code=400, detail="Engine must be complete before annotation"
            )
        game.annotation_status = "pending"
    elif layer == "condition":
        if game.engine_status != "complete":
            raise HTTPException(
                status_code=400, detail="Engine must be complete before conditions"
            )
        game.condition_status = "pending"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid layer: {layer}")

    await db.commit()
    return {"game_id": game_id, "requeued_from": layer}


@router.post("/reprocess/pattern/{pattern_id}")
async def reprocess_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Queue all unscanned games for one registry pattern."""
    result = await queue_rescan_for_pattern(db, pattern_id)
    await db.commit()
    return result


@router.get("/stuck")
async def get_stuck_games(
    timeout_minutes: int = Query(30, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Games with any layer in 'running' state > timeout_minutes."""
    stuck = []

    # Check engine_status = "running" for too long
    engine_q = await db.execute(
        select(Game).where(
            Game.engine_status == "running",
            Game.engine_completed_at.is_(None),
        )
    )
    for g in engine_q.scalars().all():
        stuck.append({
            "game_id": g.id,
            "stuck_layer": "engine",
            "lichess_id": g.lichess_id,
        })

    # Check annotation_status = "running"
    annotation_q = await db.execute(
        select(Game).where(
            Game.annotation_status == "running",
            Game.annotation_completed_at.is_(None),
        )
    )
    for g in annotation_q.scalars().all():
        stuck.append({
            "game_id": g.id,
            "stuck_layer": "annotation",
            "lichess_id": g.lichess_id,
        })

    # Check condition_status = "running"
    condition_q = await db.execute(
        select(Game).where(
            Game.condition_status == "running",
            Game.condition_completed_at.is_(None),
        )
    )
    for g in condition_q.scalars().all():
        stuck.append({
            "game_id": g.id,
            "stuck_layer": "condition",
            "lichess_id": g.lichess_id,
        })

    return {"stuck_games": stuck, "timeout_minutes": timeout_minutes}
