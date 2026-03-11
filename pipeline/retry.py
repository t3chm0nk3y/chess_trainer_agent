"""Retry worker — re-queues failed and stuck games per SRS Section 8.5."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from models import Game

logger = logging.getLogger(__name__)

# Retry delay schedule (failure_count -> minutes)
RETRY_DELAYS = {
    1: 2,
    2: 10,
    3: 60,
    4: 360,
    5: 1440,
}

STUCK_TIMEOUT_MINUTES = 30


def compute_next_retry(failure_count: int) -> timedelta:
    """Return delay before next retry based on failure count."""
    minutes = RETRY_DELAYS.get(failure_count, 1440)
    return timedelta(minutes=minutes)


async def get_retryable_games(db: AsyncSession) -> list[Game]:
    """Games with failed status, below MAX_RETRIES, and past next_retry_at."""
    now = datetime.now(tz=timezone.utc)
    result = await db.execute(
        select(Game).where(
            or_(
                Game.engine_status == "failed",
                Game.annotation_status == "failed",
                Game.condition_status == "failed",
            ),
            Game.engine_failure_count < config.MAX_RETRIES,
            or_(
                Game.engine_next_retry_at.is_(None),
                Game.engine_next_retry_at <= now,
            ),
        )
    )
    return list(result.scalars().all())


async def retry_failed_games(db: AsyncSession) -> int:
    """Re-queue all retryable failed games. Returns count re-queued."""
    games = await get_retryable_games(db)
    count = 0

    for game in games:
        if game.engine_status == "failed":
            game.engine_status = "pending"
        if game.annotation_status == "failed":
            game.annotation_status = "pending"
        if game.condition_status == "failed":
            game.condition_status = "pending"
        count += 1

    if count:
        await db.commit()
        logger.info("Re-queued %d failed games for retry", count)

    return count


async def mark_exceeded_retries(db: AsyncSession) -> int:
    """Mark games that have exceeded MAX_RETRIES as needs_manual_review."""
    result = await db.execute(
        select(Game).where(
            or_(
                Game.engine_status == "failed",
                Game.annotation_status == "failed",
                Game.condition_status == "failed",
            ),
            Game.engine_failure_count >= config.MAX_RETRIES,
        )
    )
    games = result.scalars().all()
    count = 0

    for game in games:
        if game.engine_status == "failed":
            game.engine_status = "needs_manual_review"
        if game.annotation_status == "failed":
            game.annotation_status = "needs_manual_review"
        if game.condition_status == "failed":
            game.condition_status = "needs_manual_review"
        count += 1

    if count:
        await db.commit()
        logger.info("Marked %d games as needs_manual_review", count)

    return count


async def reset_stuck_jobs(db: AsyncSession, timeout_minutes: int = 30) -> int:
    """Reset games stuck in 'running' state for > timeout_minutes."""
    count = 0

    # Engine stuck
    result = await db.execute(
        select(Game).where(
            Game.engine_status == "running",
            Game.engine_completed_at.is_(None),
        )
    )
    for game in result.scalars().all():
        game.engine_status = "pending"
        count += 1

    # Annotation stuck
    result = await db.execute(
        select(Game).where(
            Game.annotation_status == "running",
            Game.annotation_completed_at.is_(None),
        )
    )
    for game in result.scalars().all():
        game.annotation_status = "pending"
        count += 1

    # Condition stuck
    result = await db.execute(
        select(Game).where(
            Game.condition_status == "running",
            Game.condition_completed_at.is_(None),
        )
    )
    for game in result.scalars().all():
        game.condition_status = "pending"
        count += 1

    if count:
        await db.commit()
        logger.info("Reset %d stuck jobs", count)

    return count


async def run_retry_cycle(db: AsyncSession) -> dict:
    """Run a full retry cycle: mark exceeded, reset stuck, retry failed."""
    exceeded = await mark_exceeded_retries(db)
    stuck = await reset_stuck_jobs(db)
    retried = await retry_failed_games(db)
    return {
        "exceeded_marked": exceeded,
        "stuck_reset": stuck,
        "failed_retried": retried,
    }
