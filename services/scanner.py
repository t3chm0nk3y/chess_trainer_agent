"""Registry scan orchestration — targeted re-analysis logic."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game, PatternScanLog

logger = logging.getLogger(__name__)


async def get_unscanned_games(
    db: AsyncSession,
    registry_pattern_id: str,
) -> list[int]:
    """Returns game IDs with no PatternScanLog record for this pattern.

    Only returns games where engine_status = "complete".
    """
    # Get all engine-complete game IDs
    all_games = await db.execute(
        select(Game.id).where(Game.engine_status == "complete")
    )
    all_game_ids = {r[0] for r in all_games.all()}

    # Get game IDs that have been scanned for this pattern
    scanned = await db.execute(
        select(PatternScanLog.game_id)
        .where(PatternScanLog.registry_pattern_id == registry_pattern_id)
    )
    scanned_ids = {r[0] for r in scanned.all()}

    unscanned = sorted(all_game_ids - scanned_ids)
    return unscanned


async def queue_rescan_for_pattern(
    db: AsyncSession,
    registry_pattern_id: str,
) -> dict:
    """Find all games with no scan record for this pattern.

    Sets has_unscanned_patterns = True on those games.
    Returns: { games_queued: int }
    """
    unscanned_ids = await get_unscanned_games(db, registry_pattern_id)
    if not unscanned_ids:
        return {"games_queued": 0}

    for game_id in unscanned_ids:
        game = await db.get(Game, game_id)
        if game:
            game.has_unscanned_patterns = True

    await db.flush()
    logger.info(
        "Queued %d games for re-scan of pattern %s",
        len(unscanned_ids), registry_pattern_id,
    )
    return {"games_queued": len(unscanned_ids)}
