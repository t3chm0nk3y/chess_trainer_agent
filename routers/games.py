"""/api/games — game listing and import."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Game, GameCondition, Move, MovePatternMatch, Pattern
from services.lichess import import_games

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("/import")
async def import_lichess_games(
    max_games: int | None = Query(None, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """Import rated games from Lichess. Optional max_games limit."""
    result = await import_games(db, max_games=max_games)
    return result


@router.get("")
async def list_games(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List games with pagination."""
    # Count total
    count_result = await db.execute(select(func.count(Game.id)))
    total = count_result.scalar_one()

    # Fetch page
    result = await db.execute(
        select(Game)
        .order_by(Game.played_at.desc())
        .limit(limit)
        .offset(offset)
    )
    games = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "games": [
            {
                "id": g.id,
                "lichess_id": g.lichess_id,
                "played_at": g.played_at.isoformat() if g.played_at else None,
                "result": g.result,
                "eco_code": g.eco_code,
                "opening_name": g.opening_name,
                "variation_name": g.variation_name,
                "engine_status": g.engine_status,
                "annotation_status": g.annotation_status,
                "condition_status": g.condition_status,
                "opponent_username": g.opponent_username,
                "player_color": g.player_color,
                "time_control": g.time_control,
                "total_moves": g.total_moves,
            }
            for g in games
        ],
    }


@router.get("/{game_id}")
async def get_game(game_id: int, db: AsyncSession = Depends(get_db)):
    """Get full game with all moves, pattern matches, and conditions."""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Game not found")

    # Fetch moves
    moves_result = await db.execute(
        select(Move)
        .where(Move.game_id == game_id)
        .order_by(Move.move_number, Move.color)
    )
    moves = moves_result.scalars().all()

    # Fetch game conditions
    conditions_result = await db.execute(
        select(GameCondition).where(GameCondition.game_id == game_id)
    )
    conditions = conditions_result.scalars().all()

    return {
        "id": game.id,
        "lichess_id": game.lichess_id,
        "pgn": game.pgn,
        "player_color": game.player_color,
        "opponent_username": game.opponent_username,
        "result": game.result,
        "played_at": game.played_at.isoformat() if game.played_at else None,
        "eco_code": game.eco_code,
        "opening_name": game.opening_name,
        "variation_name": game.variation_name,
        "time_control": game.time_control,
        "total_moves": game.total_moves,
        "engine_status": game.engine_status,
        "annotation_status": game.annotation_status,
        "condition_status": game.condition_status,
        "moves": [
            {
                "id": m.id,
                "move_number": m.move_number,
                "color": m.color,
                "san": m.san,
                "fen_before": m.fen_before,
                "fen_after": m.fen_after,
                "phase": m.phase,
                "cp_eval_before": m.cp_eval_before,
                "cp_eval_after": m.cp_eval_after,
                "cp_loss": m.cp_loss,
                "best_move_san": m.best_move_san,
                "mistake_severity": m.mistake_severity,
            }
            for m in moves
        ],
        "conditions": [
            {
                "registry_pattern_id": c.registry_pattern_id,
                "condition_name": c.condition_name,
                "detected_at_move": c.detected_at_move,
                "player_was_worse": c.player_was_worse,
                "game_result": c.game_result,
                "context_note": c.context_note,
            }
            for c in conditions
        ],
    }


@router.get("/{game_id}/mistakes")
async def get_game_mistakes(game_id: int, db: AsyncSession = Depends(get_db)):
    """Only mistake/blunder/inaccuracy moves with all pattern matches."""
    from fastapi import HTTPException

    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    moves_result = await db.execute(
        select(Move)
        .where(Move.game_id == game_id, Move.mistake_severity.isnot(None))
        .order_by(Move.move_number)
    )
    mistakes = moves_result.scalars().all()

    items = []
    for m in mistakes:
        # Fetch pattern matches for this move
        matches_result = await db.execute(
            select(MovePatternMatch).where(MovePatternMatch.move_id == m.id)
        )
        matches = matches_result.scalars().all()

        items.append({
            "id": m.id,
            "move_number": m.move_number,
            "color": m.color,
            "san": m.san,
            "fen_before": m.fen_before,
            "phase": m.phase,
            "cp_loss": m.cp_loss,
            "best_move_san": m.best_move_san,
            "mistake_severity": m.mistake_severity,
            "pattern_matches": [
                {
                    "registry_pattern_id": pm.registry_pattern_id,
                    "annotation": pm.annotation,
                    "matched_at": pm.matched_at.isoformat() if pm.matched_at else None,
                }
                for pm in matches
            ],
        })

    return {"game_id": game_id, "mistakes": items}


@router.get("/{game_id}/recurring")
async def get_recurring_mistakes(game_id: int, db: AsyncSession = Depends(get_db)):
    """Mistakes from this game where Pattern.frequency > 1."""
    from fastapi import HTTPException

    result = await db.execute(select(Game).where(Game.id == game_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Game not found")

    # Get pattern matches for this game with frequency > 1
    matches_result = await db.execute(
        select(MovePatternMatch, Pattern)
        .join(Pattern, MovePatternMatch.registry_pattern_id == Pattern.registry_pattern_id)
        .where(MovePatternMatch.game_id == game_id, Pattern.frequency > 1)
    )
    rows = matches_result.all()

    items = []
    for match, pattern in rows:
        # Get the move
        move_result = await db.execute(select(Move).where(Move.id == match.move_id))
        move = move_result.scalar_one()
        items.append({
            "move_number": move.move_number,
            "san": move.san,
            "pattern_name": pattern.name,
            "frequency": pattern.frequency,
            "annotation": match.annotation,
        })

    return {"game_id": game_id, "recurring": items}
