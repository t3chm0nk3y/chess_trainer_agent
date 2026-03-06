"""Background analysis worker for processing games."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Game, Move, Pattern, PatternInstance
from backend.services.classifier import classify_move, detect_phase
from backend.services.claude_agent import classify_mistakes_batch
from backend.services.engine import stockfish

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


def _classify_mistake_types(moves: list[Move]) -> None:
    """Classify mistakes as tactical/strategic via Claude batch call."""
    mistake_moves = [
        m for m in moves
        if m.classification in ("inaccuracy", "mistake", "blunder")
        and m.eval_delta is not None
    ]
    if not mistake_moves:
        return

    batch_input = [
        {
            "fen": m.fen_before,
            "san": m.san,
            "best_move_uci": m.best_move_uci,
            "eval_delta": m.eval_delta,
            "phase": m.phase,
        }
        for m in mistake_moves
    ]

    classifications = classify_mistakes_batch(batch_input)
    for move, mtype in zip(mistake_moves, classifications):
        move.mistake_type = mtype


def _match_patterns(db: Session, game_id: str, moves: list[Move]) -> None:
    """Match mistake moves against known patterns and create PatternInstances.

    Uses keyword matching on pattern labels/descriptions against move context.
    For each mistake move, finds patterns whose category matches the move's phase
    or mistake_type and creates a PatternInstance link.
    """
    patterns = db.query(Pattern).filter(Pattern.resolved.is_(False)).all()
    if not patterns:
        return

    mistake_moves = [
        m for m in moves
        if m.classification in ("inaccuracy", "mistake", "blunder")
    ]
    if not mistake_moves:
        return

    # Build a lookup by category and mistake_type
    tactical_patterns = [p for p in patterns if p.mistake_type == "tactical"]
    strategic_patterns = [p for p in patterns if p.mistake_type == "strategic"]
    # Also index by general category
    category_patterns: dict[str, list[Pattern]] = {}
    for p in patterns:
        category_patterns.setdefault(p.category, []).append(p)

    today = date.today()
    matched_count = 0

    for move in mistake_moves:
        candidates: list[Pattern] = []

        # Match by mistake_type
        if move.mistake_type == "tactical":
            candidates.extend(tactical_patterns)
        elif move.mistake_type == "strategic":
            candidates.extend(strategic_patterns)

        # Also match by phase-based category (opening/middlegame/endgame maps loosely)
        if move.phase and move.phase in category_patterns:
            candidates.extend(category_patterns[move.phase])

        # Fallback: match any pattern in general categories
        for cat in ("tactical", "positional"):
            if cat in category_patterns:
                candidates.extend(category_patterns[cat])

        # Deduplicate
        seen_ids: set[str] = set()
        unique_candidates: list[Pattern] = []
        for p in candidates:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique_candidates.append(p)

        # Score candidates by keyword overlap with move context
        move_context = (
            f"{move.san} {move.phase or ''} {move.mistake_type or ''} "
            f"{move.classification or ''}"
        ).lower()

        best_pattern = None
        best_score = 0
        for p in unique_candidates:
            pattern_words = set(
                (p.label + " " + p.description).lower().split()
            )
            score = sum(1 for w in pattern_words if w in move_context)
            # Boost if mistake_type matches
            if p.mistake_type and p.mistake_type == move.mistake_type:
                score += 3
            if score > best_score:
                best_score = score
                best_pattern = p

        if best_pattern and best_score >= 1:
            instance = PatternInstance(
                pattern_id=best_pattern.id,
                game_id=game_id,
                move_id=move.id,
                notes=f"Auto-matched: {move.classification} at ply {move.ply}",
            )
            db.add(instance)

            # Update pattern metadata
            best_pattern.frequency = (best_pattern.frequency or 0) + 1
            best_pattern.last_seen = today
            if not best_pattern.first_seen:
                best_pattern.first_seen = today
            if best_pattern.acknowledged:
                best_pattern.post_acknowledgment_count = (
                    (best_pattern.post_acknowledgment_count or 0) + 1
                )

            matched_count += 1

    if matched_count > 0:
        db.flush()
        logger.info("Game %s: matched %d moves to patterns", game_id, matched_count)


def _analyze_game_sync(game_id: str, session_factory=None) -> None:
    """Run full analysis pipeline on a single game (synchronous).

    Steps:
    1. Fetch game and moves from database
    2. For each position, get engine eval via Stockfish
    3. Compute eval deltas relative to the player's perspective
    4. Classify each move
    5. Detect game phase
    6. Classify mistake types (tactical/strategic) via Claude
    7. Match mistakes against known patterns
    8. Store results
    9. Mark game as analyzed
    """
    factory = session_factory or SessionLocal
    db: Session = factory()
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

        if not moves:
            logger.warning("Game %s has no moves", game_id)
            game.analysis_status = "analyzed"
            db.commit()
            return

        engine_available = True

        # Evaluate the starting position first
        try:
            start_eval = stockfish.analyze_position(moves[0].fen_before)
            prev_eval_cp = start_eval.score_cp
        except RuntimeError:
            logger.warning("Stockfish not available, falling back to phase-only analysis")
            engine_available = False
            prev_eval_cp = 0.0

        for move in moves:
            # Detect phase regardless of engine availability
            move.phase = detect_phase(move.fen_before)

            if not engine_available:
                continue

            try:
                # Evaluate the position AFTER this move was played
                after_eval = stockfish.analyze_position(move.fen_after)

                move.engine_eval_before = prev_eval_cp
                move.engine_eval_after = after_eval.score_cp

                # Eval delta from the moving side's perspective.
                # White wants positive scores, black wants negative scores.
                # A "loss" means the eval moved away from the moving side.
                is_white_move = (move.ply % 2 == 0)
                if is_white_move:
                    # White moved: delta = eval_after - eval_before
                    # Negative means white lost advantage
                    delta = after_eval.score_cp - prev_eval_cp
                else:
                    # Black moved: delta = eval_before - eval_after
                    # (from black's perspective, lower white eval is better)
                    delta = prev_eval_cp - after_eval.score_cp

                # eval_delta stores the LOSS (positive = player lost centipawns)
                move.eval_delta = max(0, -delta)
                move.classification = classify_move(move.eval_delta)

                # Store best move from the pre-move position
                before_eval = stockfish.analyze_position(move.fen_before)
                move.best_move_uci = before_eval.best_move

                prev_eval_cp = after_eval.score_cp

            except Exception as e:
                logger.error("Error analyzing move %d in game %s: %s", move.ply, game_id, e)
                move.eval_delta = None
                move.classification = None

        # Step 6: Classify mistake types via Claude
        try:
            _classify_mistake_types(moves)
        except Exception as e:
            logger.warning("Mistake type classification failed for game %s: %s", game_id, e)

        # Step 7: Match against known patterns
        try:
            _match_patterns(db, game_id, moves)
        except Exception as e:
            logger.warning("Pattern matching failed for game %s: %s", game_id, e)

        game.analysis_status = "analyzed"
        db.commit()
        logger.info("Game %s analysis complete (%d moves)", game_id, len(moves))

    except Exception as e:
        logger.error("Failed to analyze game %s: %s", game_id, e)
        try:
            game = db.query(Game).filter(Game.id == game_id).first()
            if game:
                game.analysis_status = "error"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def analyze_game(game_id: str) -> None:
    """Run analysis in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _analyze_game_sync, game_id)


def queue_analysis(game_id: str) -> None:
    """Queue a game for background analysis."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(analyze_game(game_id))
        else:
            _executor.submit(_analyze_game_sync, game_id)
    except RuntimeError:
        # No event loop running
        _executor.submit(_analyze_game_sync, game_id)
