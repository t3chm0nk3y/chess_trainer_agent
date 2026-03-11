"""Generate all pre-computed reports.

Usage: .venv/bin/python scripts/generate_reports.py [--type TYPE]

Types: all, player_profile, opening, pattern, monthly, phase, game_condition, weakness
"""

import argparse
import asyncio
import logging
import sys

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main(report_type: str):
    from database import async_session, init_db
    from services.report_generator import (
        _upsert_reports,
        generate_all_reports,
        generate_game_condition_reports,
        generate_monthly_reports,
        generate_opening_reports,
        generate_pattern_reports,
        generate_phase_reports,
        generate_player_profile,
        generate_weakness_reports,
    )

    await init_db()

    async with async_session() as db:
        if report_type == "all":
            count = await generate_all_reports(db)
        else:
            generators = {
                "player_profile": generate_player_profile,
                "opening": generate_opening_reports,
                "pattern": generate_pattern_reports,
                "monthly": generate_monthly_reports,
                "phase": generate_phase_reports,
                "game_condition": generate_game_condition_reports,
                "weakness": generate_weakness_reports,
            }
            gen = generators[report_type]
            reports = await gen(db)
            count = await _upsert_reports(db, reports)

        logger.info("Done — %d reports generated", count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate chess trainer reports")
    parser.add_argument(
        "--type",
        choices=[
            "player_profile", "opening", "pattern", "monthly",
            "phase", "game_condition", "weakness", "all",
        ],
        default="all",
    )
    args = parser.parse_args()
    asyncio.run(main(args.type))
