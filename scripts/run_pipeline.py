"""Run annotation + condition detection + opening stats on engine-complete games.

Safe to run repeatedly — each stage skips already-processed work.

Usage: .venv/bin/python scripts/run_pipeline.py [--stage annotation|conditions|openings|all]
"""

import argparse
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


async def run_annotations():
    """Run Claude annotation on all engine-complete, annotation-pending games."""
    from sqlalchemy import select

    from database import async_session, init_db
    from models import Game
    from pipeline.worker import run_annotation

    await init_db()

    async with async_session() as db:
        result = await db.execute(
            select(Game.id)
            .where(
                Game.engine_status == "complete",
                Game.annotation_status == "pending",
            )
            .order_by(Game.played_at)
        )
        game_ids = [r[0] for r in result.all()]
        total = len(game_ids)
        logger.info("Annotation: %d games pending", total)

    if not total:
        return

    done = 0
    errors = 0
    start = time.time()

    for i, game_id in enumerate(game_ids):
        async with async_session() as db:
            game = await db.get(Game, game_id)
            if not game or game.annotation_status != "pending":
                continue
            try:
                await run_annotation(db, game)
                done += 1
            except Exception as e:
                errors += 1
                logger.error("Annotation game %d failed: %s", game_id, e)

        if (i + 1) % 10 == 0 or (i + 1) == total:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / rate if rate > 0 else 0
            logger.info(
                "Annotation [%d/%d] done=%d err=%d rate=%.2f/s eta=%.0fs",
                i + 1, total, done, errors, rate, eta,
            )

    logger.info("Annotation complete: %d processed, %d errors", done, errors)


async def run_conditions():
    """Run condition detection on all engine-complete, condition-pending games."""
    from sqlalchemy import select

    from database import async_session, init_db
    from models import Game
    from pipeline.worker import run_condition_detection

    await init_db()

    async with async_session() as db:
        result = await db.execute(
            select(Game.id)
            .where(
                Game.engine_status == "complete",
                Game.condition_status == "pending",
            )
            .order_by(Game.played_at)
        )
        game_ids = [r[0] for r in result.all()]
        total = len(game_ids)
        logger.info("Conditions: %d games pending", total)

    if not total:
        return

    done = 0
    errors = 0
    start = time.time()

    for i, game_id in enumerate(game_ids):
        async with async_session() as db:
            game = await db.get(Game, game_id)
            if not game or game.condition_status != "pending":
                continue
            try:
                await run_condition_detection(db, game)
                done += 1
            except Exception as e:
                errors += 1
                logger.error("Conditions game %d failed: %s", game_id, e)

        if (i + 1) % 10 == 0 or (i + 1) == total:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / rate if rate > 0 else 0
            logger.info(
                "Conditions [%d/%d] done=%d err=%d rate=%.2f/s eta=%.0fs",
                i + 1, total, done, errors, rate, eta,
            )

    logger.info("Conditions complete: %d processed, %d errors", done, errors)


async def run_openings():
    """Recompute opening stats from all engine-complete games."""
    from database import async_session, init_db
    from services.opening_stats import compute_opening_stats

    await init_db()

    async with async_session() as db:
        count = await compute_opening_stats(db)
        logger.info("Opening stats computed: %d lines", count)


async def main(stage: str):
    if stage in ("annotation", "all"):
        await run_annotations()
    if stage in ("conditions", "all"):
        await run_conditions()
    if stage in ("openings", "all"):
        await run_openings()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run analysis pipeline stages")
    parser.add_argument(
        "--stage",
        choices=["annotation", "conditions", "openings", "all"],
        default="all",
        help="Which stage to run (default: all)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.stage))
