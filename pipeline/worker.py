"""Analysis pipeline — stage execution."""

import io
import logging
from datetime import datetime

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game, GameCondition, Move, MovePatternMatch, Pattern, PatternScanLog
from services.annotator import annotate_mistake
from services.classifier import assign_phase, assign_severity, detect_game_conditions
from services.registry import (
    get_active_patterns,
    get_candidate_patterns_for_move,
    get_registry_version,
)
from services.stockfish import StockfishEngine

logger = logging.getLogger(__name__)


async def parse_and_create_moves(db: AsyncSession, game: Game) -> list[Move]:
    """Parse PGN and create Move records with phase assignment.

    This is the first stage of the pipeline. It creates Move records
    for every move in the game with correct phase assignments.
    """
    # Check if moves already exist
    existing = await db.execute(select(Move).where(Move.game_id == game.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        logger.info("Game %d already has moves, skipping PGN parse", game.id)
        result = await db.execute(
            select(Move).where(Move.game_id == game.id).order_by(Move.move_number)
        )
        return list(result.scalars().all())

    pgn_io = io.StringIO(game.pgn)
    chess_game = chess.pgn.read_game(pgn_io)
    if chess_game is None:
        raise ValueError(f"Failed to parse PGN for game {game.id}")

    moves = []
    board = chess_game.board()
    for ply, node in enumerate(chess_game.mainline()):
        move = node.move
        fen_before = board.fen()
        san = board.san(move)
        move_number = (ply // 2) + 1
        color = "white" if ply % 2 == 0 else "black"
        phase = assign_phase(board, move_number)
        board.push(move)
        fen_after = board.fen()

        move_record = Move(
            game_id=game.id,
            move_number=move_number,
            color=color,
            san=san,
            fen_before=fen_before,
            fen_after=fen_after,
            phase=phase,
        )
        db.add(move_record)
        moves.append(move_record)

    await db.flush()
    logger.info("Created %d moves for game %d", len(moves), game.id)
    return moves


async def run_engine_analysis(db: AsyncSession, game: Game) -> None:
    """Layer 1 — Engine analysis. Evaluate every move with Stockfish.

    Sets cp_eval_before, cp_eval_after, cp_loss, best_move_san, mistake_severity
    on each Move record. These fields are immutable after this completes.

    On completion: engine_status = "complete", annotation_status = "pending",
    condition_status = "pending".
    """
    game.engine_status = "running"
    await db.flush()

    try:
        # Ensure moves exist
        result = await db.execute(
            select(Move).where(Move.game_id == game.id).order_by(Move.move_number, Move.color)
        )
        moves = list(result.scalars().all())
        if not moves:
            moves = await parse_and_create_moves(db, game)

        sf = StockfishEngine()
        try:
            sf.start()

            for move in moves:
                # Evaluate position before this move
                before_eval = sf.evaluate(move.fen_before)
                after_eval = sf.evaluate(move.fen_after)

                move.cp_eval_before = before_eval["cp_eval"]
                move.cp_eval_after = after_eval["cp_eval"]
                move.best_move_san = before_eval["best_move_san"]

                # cp_loss from player's perspective (always positive = bad)
                # Side to move in fen_before is the player making this move
                # cp_eval is relative (from side-to-move perspective)
                # Loss = how much worse the position got for the player
                # before_eval is from player's perspective (they're about to move)
                # after_eval is from opponent's perspective (opponent is about to move)
                # So loss = before_eval - (-after_eval) = before_eval + after_eval
                # Wait — after_eval is relative to side to move (opponent).
                # From player perspective: position was before_eval, now it's -after_eval
                cp_loss = before_eval["cp_eval"] - (-after_eval["cp_eval"])
                # cp_loss > 0 means player lost centipawns
                move.cp_loss = max(0.0, cp_loss)
                move.mistake_severity = assign_severity(move.cp_loss)

        finally:
            sf.stop()

        game.engine_status = "complete"
        game.engine_completed_at = datetime.utcnow()
        game.annotation_status = "pending"
        game.condition_status = "pending"
        await db.commit()
        logger.info("Engine analysis complete for game %d (%d moves)", game.id, len(moves))

    except Exception as e:
        game.engine_status = "failed"
        game.engine_failure_reason = f"{type(e).__name__}: {e}"
        game.engine_failure_count = (game.engine_failure_count or 0) + 1
        await db.commit()
        logger.error("Engine analysis failed for game %d: %s", game.id, e)
        raise


async def run_annotation(db: AsyncSession, game: Game) -> None:
    """Layer 2 — Annotation. Classify each mistake move against registry patterns.

    Creates MovePatternMatch records (append-only) and PatternScanLog records.
    Updates Pattern frequency counts.

    Prerequisite: engine_status = "complete".
    """
    if game.engine_status != "complete":
        logger.warning("Game %d: engine not complete, skipping annotation", game.id)
        return

    game.annotation_status = "running"
    await db.flush()

    try:
        # Load moves with mistakes
        result = await db.execute(
            select(Move)
            .where(Move.game_id == game.id, Move.mistake_severity.isnot(None))
            .order_by(Move.move_number)
        )
        mistake_moves = list(result.scalars().all())

        if not mistake_moves:
            game.annotation_status = "complete"
            game.annotation_completed_at = datetime.utcnow()
            game.registry_version_at_last_scan = get_registry_version()
            await db.commit()
            return

        # Get active non-GC, non-OL patterns
        registry_version = get_registry_version()

        for move in mistake_moves:
            # Get candidate patterns for this move's phase and cp_loss
            candidates = get_candidate_patterns_for_move(move.phase, move.cp_loss)
            if not candidates:
                # Log scan with no candidates
                for p in _get_all_scannable_patterns():
                    await _log_scan(db, game.id, p["id"], "no_match", 0)
                continue

            # Check which patterns this move has already been scanned for
            scanned_result = await db.execute(
                select(PatternScanLog.registry_pattern_id)
                .where(
                    PatternScanLog.game_id == game.id,
                    PatternScanLog.registry_pattern_id.in_(
                        [p["id"] for p in candidates]
                    ),
                )
            )
            already_scanned = set(r[0] for r in scanned_result.all())

            # Filter to unscanned candidates
            unscanned = [p for p in candidates if p["id"] not in already_scanned]
            if not unscanned:
                continue

            # Call Claude annotator
            result = await annotate_mistake(
                fen=move.fen_before,
                played_move_san=move.san,
                best_move_san=move.best_move_san or "unknown",
                cp_loss=move.cp_loss,
                phase=move.phase,
                candidate_patterns=unscanned,
            )

            pattern_id = result["registry_pattern_id"]
            annotation = result["annotation"]

            # Create MovePatternMatch if valid pattern
            if pattern_id != "UNCLASSIFIED":
                # Check unique constraint
                existing_match = await db.execute(
                    select(MovePatternMatch)
                    .where(
                        MovePatternMatch.move_id == move.id,
                        MovePatternMatch.registry_pattern_id == pattern_id,
                    )
                )
                if existing_match.scalar_one_or_none() is None:
                    match = MovePatternMatch(
                        move_id=move.id,
                        game_id=game.id,
                        registry_pattern_id=pattern_id,
                        annotation=annotation,
                        matched_at=datetime.utcnow(),
                        registry_version_at_match=registry_version,
                    )
                    db.add(match)

                    # Update Pattern record (find-or-create)
                    await _update_pattern(db, pattern_id, game, move, annotation)

            # Log scan for all evaluated patterns
            for p in unscanned:
                scan_result = "matched" if p["id"] == pattern_id else "no_match"
                match_count = 1 if p["id"] == pattern_id else 0
                await _log_scan(db, game.id, p["id"], scan_result, match_count)

        game.annotation_status = "complete"
        game.annotation_completed_at = datetime.utcnow()
        game.registry_version_at_last_scan = registry_version
        await db.commit()
        logger.info("Annotation complete for game %d", game.id)

    except Exception as e:
        game.annotation_status = "failed"
        await db.commit()
        logger.error("Annotation failed for game %d: %s", game.id, e)
        raise


async def run_condition_detection(db: AsyncSession, game: Game) -> None:
    """Layer 3 — Condition detection. Detect structural game conditions.

    Creates GameCondition records (append-only) and PatternScanLog records.
    Updates Pattern frequency counts for conditions.

    Prerequisite: engine_status = "complete".
    """
    if game.engine_status != "complete":
        logger.warning("Game %d: engine not complete, skipping conditions", game.id)
        return

    game.condition_status = "running"
    await db.flush()

    try:
        # Load all moves
        result = await db.execute(
            select(Move)
            .where(Move.game_id == game.id)
            .order_by(Move.move_number, Move.color)
        )
        moves = list(result.scalars().all())

        # Get active GC patterns
        gc_patterns = [
            p for p in get_active_patterns()
            if p.get("axis") == "game_condition"
        ]

        if not gc_patterns or not moves:
            game.condition_status = "complete"
            game.condition_completed_at = datetime.utcnow()
            await db.commit()
            return

        # Check which GC patterns this game has already been scanned for
        scanned_result = await db.execute(
            select(PatternScanLog.registry_pattern_id)
            .where(
                PatternScanLog.game_id == game.id,
                PatternScanLog.registry_pattern_id.in_([p["id"] for p in gc_patterns]),
            )
        )
        already_scanned = set(r[0] for r in scanned_result.all())
        unscanned_gc = [p for p in gc_patterns if p["id"] not in already_scanned]

        if not unscanned_gc:
            game.condition_status = "complete"
            game.condition_completed_at = datetime.utcnow()
            await db.commit()
            return

        # Detect conditions
        detected = detect_game_conditions(
            moves=moves,
            active_gc_patterns=unscanned_gc,
            player_color=game.player_color,
            game_result=game.result,
        )

        detected_ids = set()
        for cond in detected:
            pid = cond["registry_pattern_id"]
            detected_ids.add(pid)

            # Check unique constraint
            existing = await db.execute(
                select(GameCondition)
                .where(
                    GameCondition.game_id == game.id,
                    GameCondition.registry_pattern_id == pid,
                )
            )
            if existing.scalar_one_or_none() is None:
                gc = GameCondition(
                    game_id=game.id,
                    registry_pattern_id=pid,
                    condition_name=cond["condition_name"],
                    detected_at_move=cond.get("detected_at_move"),
                    player_was_worse=cond.get("player_was_worse", False),
                    game_result=game.result,
                    context_note=cond.get("context_note"),
                )
                db.add(gc)

                # Update Pattern frequency for this condition
                await _update_pattern_for_condition(db, pid, game)

        # Log scan for all evaluated GC patterns
        for p in unscanned_gc:
            scan_result = "matched" if p["id"] in detected_ids else "no_match"
            match_count = 1 if p["id"] in detected_ids else 0
            await _log_scan(db, game.id, p["id"], scan_result, match_count)

        game.condition_status = "complete"
        game.condition_completed_at = datetime.utcnow()
        await db.commit()
        logger.info("Condition detection complete for game %d: %d found", game.id, len(detected))

    except Exception as e:
        game.condition_status = "failed"
        await db.commit()
        logger.error("Condition detection failed for game %d: %s", game.id, e)
        raise


async def _update_pattern_for_condition(
    db: AsyncSession,
    registry_pattern_id: str,
    game: Game,
) -> None:
    """Find-or-create a Pattern record for a game condition."""
    from services.registry import get_registry

    result = await db.execute(
        select(Pattern).where(Pattern.registry_pattern_id == registry_pattern_id)
    )
    pattern = result.scalar_one_or_none()

    registry = get_registry()
    reg_pattern = None
    for p in registry.get("patterns", []):
        if p["id"] == registry_pattern_id:
            reg_pattern = p
            break

    now = datetime.utcnow()

    if pattern is None:
        pattern = Pattern(
            registry_pattern_id=registry_pattern_id,
            phase=reg_pattern["phase"] if reg_pattern else "all",
            axis=reg_pattern["axis"] if reg_pattern else "game_condition",
            name=reg_pattern["name"] if reg_pattern else registry_pattern_id,
            frequency=1,
            games_affected=1,
            first_seen_at=now,
            last_seen_at=now,
            first_seen_game_id=game.id,
            last_seen_game_id=game.id,
        )
        db.add(pattern)
    else:
        pattern.frequency += 1
        pattern.last_seen_at = now
        if pattern.last_seen_game_id != game.id:
            pattern.games_affected += 1
        pattern.last_seen_game_id = game.id


def _get_all_scannable_patterns() -> list[dict]:
    """Get all active patterns that annotation scans for (not GC or OL)."""
    return get_active_patterns(exclude_axes={"game_condition", "opening_line"})


async def _log_scan(
    db: AsyncSession,
    game_id: int,
    registry_pattern_id: str,
    result: str,
    match_count: int,
) -> None:
    """Create a PatternScanLog entry, skipping if already exists."""
    existing = await db.execute(
        select(PatternScanLog)
        .where(
            PatternScanLog.game_id == game_id,
            PatternScanLog.registry_pattern_id == registry_pattern_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return

    log = PatternScanLog(
        game_id=game_id,
        registry_pattern_id=registry_pattern_id,
        scanned_at=datetime.utcnow(),
        result=result,
        match_count=match_count,
    )
    db.add(log)


async def _update_pattern(
    db: AsyncSession,
    registry_pattern_id: str,
    game: Game,
    move: Move,
    annotation: str,
) -> None:
    """Find-or-create a Pattern record and increment frequency."""
    from services.registry import get_registry

    result = await db.execute(
        select(Pattern).where(Pattern.registry_pattern_id == registry_pattern_id)
    )
    pattern = result.scalar_one_or_none()

    # Look up registry metadata
    registry = get_registry()
    reg_pattern = None
    for p in registry.get("patterns", []):
        if p["id"] == registry_pattern_id:
            reg_pattern = p
            break

    now = datetime.utcnow()

    if pattern is None:
        # Create new Pattern
        pattern = Pattern(
            registry_pattern_id=registry_pattern_id,
            phase=reg_pattern["phase"] if reg_pattern else move.phase,
            axis=reg_pattern["axis"] if reg_pattern else "tactical",
            name=reg_pattern["name"] if reg_pattern else registry_pattern_id,
            frequency=1,
            games_affected=1,
            first_seen_at=now,
            last_seen_at=now,
            first_seen_game_id=game.id,
            last_seen_game_id=game.id,
            example_fen=move.fen_before,
            example_annotation=annotation,
        )
        db.add(pattern)
    else:
        pattern.frequency += 1
        pattern.last_seen_at = now

        # Track distinct games
        if pattern.last_seen_game_id != game.id:
            pattern.games_affected += 1
        pattern.last_seen_game_id = game.id
