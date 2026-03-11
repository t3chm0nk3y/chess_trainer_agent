"""Opening line aggregation and statistics."""

import logging
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game, Move, OpeningStats

logger = logging.getLogger(__name__)


async def compute_opening_stats(db: AsyncSession) -> int:
    """Recompute all OpeningStats from engine-complete games.

    - Groups by (eco_code, opening_name, variation_name)
    - Excludes groups with fewer than 3 games
    - Full recompute: deletes existing rows and reinserts
    - Returns count of opening lines computed
    """
    # Fetch all engine-complete games with eco_code
    result = await db.execute(
        select(Game).where(
            Game.engine_status == "complete",
            Game.eco_code.isnot(None),
        )
    )
    games = result.scalars().all()

    # Group by opening line
    groups: dict[tuple[str, str, str | None], list[Game]] = {}
    for g in games:
        key = (g.eco_code, g.opening_name or "Unknown", g.variation_name)
        groups.setdefault(key, []).append(g)

    # Delete existing stats
    await db.execute(delete(OpeningStats))

    now = datetime.now(tz=timezone.utc)
    count = 0

    for (eco_code, opening_name, variation_name), group_games in groups.items():
        if len(group_games) < 3:
            continue

        total = len(group_games)
        wins = sum(1 for g in group_games if g.result == "win")
        losses = sum(1 for g in group_games if g.result == "loss")
        draws = sum(1 for g in group_games if g.result == "draw")

        game_ids = [g.id for g in group_games]

        # Compute avg_cp_loss for opening-phase moves
        moves_result = await db.execute(
            select(Move).where(
                Move.game_id.in_(game_ids),
                Move.phase == "opening",
                Move.cp_loss.isnot(None),
            )
        )
        opening_moves = moves_result.scalars().all()

        avg_cp_loss = None
        if opening_moves:
            total_cp = sum(m.cp_loss for m in opening_moves)
            avg_cp_loss = round(total_cp / len(opening_moves), 2)

        # Compute divergence_move and divergence_san
        # = most common move number where a mistake/blunder first appears
        divergence_move, divergence_san = await _compute_divergence(
            db, game_ids
        )

        stats = OpeningStats(
            eco_code=eco_code,
            opening_name=opening_name,
            variation_name=variation_name,
            total_games=total,
            wins=wins,
            losses=losses,
            draws=draws,
            win_rate=round(wins / total, 4),
            loss_rate=round(losses / total, 4),
            avg_cp_loss_opening=avg_cp_loss,
            divergence_move=divergence_move,
            divergence_san=divergence_san,
            last_computed_at=now,
        )
        db.add(stats)
        count += 1

    await db.commit()
    logger.info("Computed opening stats for %d lines", count)
    return count


async def _compute_divergence(
    db: AsyncSession,
    game_ids: list[int],
) -> tuple[int | None, str | None]:
    """Find the most common move number where a mistake/blunder first appears.

    Returns (move_number, san) or (None, None) if no mistakes found.
    """
    # For each game, find the first mistake/blunder in the opening phase
    first_mistakes: list[tuple[int, str]] = []

    for game_id in game_ids:
        result = await db.execute(
            select(Move)
            .where(
                Move.game_id == game_id,
                Move.phase == "opening",
                Move.mistake_severity.in_(["mistake", "blunder"]),
            )
            .order_by(Move.move_number)
            .limit(1)
        )
        move = result.scalar_one_or_none()
        if move:
            first_mistakes.append((move.move_number, move.san))

    if not first_mistakes:
        return None, None

    # Most common move number
    move_counter = Counter(m[0] for m in first_mistakes)
    most_common_move = move_counter.most_common(1)[0][0]

    # Most common SAN at that move number
    sans_at_move = [m[1] for m in first_mistakes if m[0] == most_common_move]
    san_counter = Counter(sans_at_move)
    most_common_san = san_counter.most_common(1)[0][0]

    return most_common_move, most_common_san
