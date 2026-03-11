"""Import games from Lichess and run Stockfish engine analysis.

Usage: .venv/bin/python scripts/import_and_analyze.py
"""

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
    from sqlalchemy import select

    from database import async_session, init_db
    from models import Game
    from pipeline.worker import run_engine_analysis
    from services.lichess import import_games

    await init_db()

    # Step 1: Import from Lichess
    logger.info("=== Step 1: Importing games from Lichess ===")
    async with async_session() as db:
        result = await import_games(db)
        logger.info(
            "Import: %d imported, %d skipped, %d errors",
            result["imported"], result["skipped"], result["errors"],
        )

    # Step 2: Run engine analysis on all pending games
    logger.info("=== Step 2: Running Stockfish engine analysis ===")
    async with async_session() as db:
        pending = await db.execute(
            select(Game).where(Game.engine_status == "pending").order_by(Game.played_at)
        )
        games = list(pending.scalars().all())
        total = len(games)
        logger.info("%d games pending engine analysis", total)

    done = 0
    errors = 0
    start = time.time()

    for i, game_stub in enumerate(games):
        async with async_session() as db:
            game = await db.get(Game, game_stub.id)
            if not game or game.engine_status != "pending":
                continue
            try:
                await run_engine_analysis(db, game)
                done += 1
            except Exception as e:
                errors += 1
                logger.error("Game %d failed: %s", game.id, e)

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
