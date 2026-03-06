"""Background analysis worker for processing games."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Game, Move
from backend.services.classifier import classify_move, detect_phase
from backend.services.mcp_client import mcp_client

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


async def analyze_game(game_id: str) -> None:
    """Run full analysis pipeline on a single game.

    Steps:
    1. Fetch game from database
    2. For each position, get engine eval + themes via ChessAgine MCP
    3. Compute eval deltas
    4. Classify each move
    5. Detect game phase
    6. Store results
    7. Mark game as analyzed
    """
    db: Session = SessionLocal()
    try:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            logger.error("Game %s not found", game_id)
            return

        moves = (
            db.query(Move)
            .filter(Move.game_id == game_id)
            .order_by(Move.ply)
            .all()
        )

        prev_eval = 0.0
        for move in moves:
            try:
                # Get engine evaluation via ChessAgine MCP
                eval_result = await mcp_client.analyze_position(move.fen_before)

                move.engine_eval_before = prev_eval
                move.engine_eval_after = eval_result.score_cp
                move.eval_delta = abs(eval_result.score_cp - prev_eval)
                move.classification = classify_move(move.eval_delta)
                move.phase = detect_phase(move.fen_before)

                if eval_result.themes:
                    import json
                    move.themes_json = json.dumps(eval_result.themes)

                prev_eval = eval_result.score_cp

            except NotImplementedError:
                logger.warning("ChessAgine MCP not connected, skipping engine analysis")
                move.phase = detect_phase(move.fen_before)
            except Exception as e:
                logger.error("Error analyzing move %d in game %s: %s", move.ply, game_id, e)

        game.analysis_status = "analyzed"
        db.commit()
        logger.info("Game %s analysis complete", game_id)

    except Exception as e:
        logger.error("Failed to analyze game %s: %s", game_id, e)
        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.analysis_status = "error"
            db.commit()
    finally:
        db.close()


def queue_analysis(game_id: str) -> None:
    """Queue a game for background analysis."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(analyze_game(game_id))
    else:
        _executor.submit(asyncio.run, analyze_game(game_id))
