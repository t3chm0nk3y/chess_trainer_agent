"""Run Stockfish engine analysis on all pending/failed games."""

import asyncio
import logging
import sys
import time

sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    from sqlalchemy import select, update

    from database import async_session, init_db
    from models import Game
    from pipeline.worker import run_engine_analysis

    await init_db()

    # Reset failed games back to pending
    async with async_session() as db:
        await db.execute(
            update(Game)
            .where(Game.engine_status == "failed")
            .values(engine_status="pending", engine_failure_reason=None)
        )
        await db.commit()

    # Get all pending games
    async with async_session() as db:
        result = await db.execute(
            select(Game.id).where(Game.engine_status == "pending").order_by(Game.played_at)
        )
        game_ids = [r[0] for r in result.all()]
        total = len(game_ids)
        logger.info("%d games pending engine analysis", total)

    done = 0
    errors = 0
    start = time.time()

    for i, game_id in enumerate(game_ids):
        async with async_session() as db:
            game = await db.get(Game, game_id)
            if not game or game.engine_status != "pending":
                continue
            try:
                await run_engine_analysis(db, game)
                done += 1
            except Exception as e:
                errors += 1
                logger.error("Game %d failed: %s", game_id, e)

        if (i + 1) % 10 == 0 or (i + 1) == total:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / rate if rate > 0 else 0
            logger.info(
                "[%d/%d] done=%d err=%d rate=%.2f/s eta=%.0fs (%.1fm)",
                i + 1, total, done, errors, rate, eta, eta / 60,
            )

    elapsed = time.time() - start
    logger.info("Complete: %d analyzed, %d errors, %.1fs total", done, errors, elapsed)


if __name__ == "__main__":
    asyncio.run(main())
