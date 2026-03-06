"""Pattern synthesis and matching orchestration."""

import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from backend.models import Game, Move, Pattern, PatternInstance, ProgressSnapshot
from backend.services import claude_agent

logger = logging.getLogger(__name__)


async def gather_game_mistakes(db: Session, game_id: str | None = None) -> list[dict]:
    """Collect all classified mistakes from analyzed games.

    Args:
        db: Database session.
        game_id: If provided, only gather mistakes from this game.

    Returns:
        List of mistake dicts suitable for Claude prompts.
    """
    query = db.query(Move).filter(
        Move.classification.in_(["inaccuracy", "mistake", "blunder"])
    )
    if game_id:
        query = query.filter(Move.game_id == game_id)

    moves = query.all()
    mistakes = []
    for m in moves:
        mistakes.append({
            "game_id": m.game_id,
            "ply": m.ply,
            "san": m.san,
            "fen_before": m.fen_before,
            "eval_delta": m.eval_delta,
            "classification": m.classification,
            "phase": m.phase,
            "themes": json.loads(m.themes_json) if m.themes_json else None,
        })
    return mistakes


async def run_pattern_synthesis(db: Session, min_games: int = 5) -> list[dict]:
    """Run cross-game pattern synthesis via Claude.

    Args:
        db: Database session.
        min_games: Minimum analyzed games required before synthesis.

    Returns:
        List of new/updated pattern dicts.
    """
    analyzed_count = db.query(Game).filter(Game.analysis_status == "analyzed").count()
    if analyzed_count < min_games:
        logger.info(
            "Only %d analyzed games (need %d), skipping synthesis",
            analyzed_count,
            min_games,
        )
        return []

    mistakes = await gather_game_mistakes(db)
    if not mistakes:
        return []

    existing = db.query(Pattern).filter(Pattern.resolved.is_(False)).all()
    existing_dicts = [
        {
            "label": p.label,
            "description": p.description,
            "category": p.category,
            "severity_score": p.severity_score,
            "frequency": p.frequency,
        }
        for p in existing
    ]

    new_patterns = await claude_agent.synthesize_patterns(mistakes, existing_dicts or None)
    return new_patterns


async def match_game_to_patterns(db: Session, game_id: str) -> dict:
    """Compare a single game's mistakes against known patterns.

    Returns:
        Claude's comparison result with matched and new patterns.
    """
    game_mistakes = await gather_game_mistakes(db, game_id=game_id)
    known = db.query(Pattern).filter(Pattern.resolved.is_(False)).all()
    known_dicts = [
        {"label": p.label, "description": p.description, "category": p.category}
        for p in known
    ]

    return await claude_agent.compare_new_game(game_mistakes, known_dicts)


def create_progress_snapshot(db: Session) -> ProgressSnapshot:
    """Create a progress snapshot from current data."""
    total_games = db.query(Game).filter(Game.analysis_status == "analyzed").count()
    total_moves = db.query(Move).filter(Move.classification.isnot(None)).count()
    good_moves = db.query(Move).filter(Move.classification.in_(["best", "good"])).count()
    accuracy = (good_moves / total_moves * 100) if total_moves > 0 else 0.0

    patterns = db.query(Pattern).filter(Pattern.resolved.is_(False)).all()
    patterns_data = {
        p.id: {
            "label": p.label,
            "severity": p.severity_score,
            "frequency": p.frequency,
        }
        for p in patterns
    }

    snapshot = ProgressSnapshot(
        snapshot_date=date.today(),
        total_games=total_games,
        avg_accuracy=round(accuracy, 1),
        patterns_json=json.dumps(patterns_data),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
