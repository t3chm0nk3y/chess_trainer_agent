"""Mistake categorization and reporting service."""

import json
import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.models import Game, Move, Pattern, PatternInstance

logger = logging.getLogger(__name__)


def get_mistake_matrix(
    db: Session,
    game_id: str | None = None,
) -> dict:
    """Build the phase x type mistake matrix.

    Returns a dict with:
    - matrix: 2D dict [phase][type] -> {count, examples}
    - totals: per-phase and per-type totals
    - overall: total mistakes
    """
    query = db.query(Move).filter(
        Move.classification.in_(["inaccuracy", "mistake", "blunder"]),
    )
    if game_id:
        query = query.filter(Move.game_id == game_id)

    mistakes = query.all()

    phases = ["opening", "middlegame", "endgame"]
    types = ["tactical", "strategic", "unclassified"]

    # Build matrix
    matrix: dict[str, dict[str, dict]] = {}
    for phase in phases:
        matrix[phase] = {}
        for mtype in types:
            matrix[phase][mtype] = {"count": 0, "examples": []}

    for m in mistakes:
        phase = m.phase or "middlegame"
        mtype = m.mistake_type or "unclassified"
        if phase not in matrix:
            phase = "middlegame"
        if mtype not in matrix.get(phase, {}):
            mtype = "unclassified"

        cell = matrix[phase][mtype]
        cell["count"] += 1
        if len(cell["examples"]) < 3:
            cell["examples"].append({
                "game_id": m.game_id,
                "ply": m.ply,
                "san": m.san,
                "eval_delta": m.eval_delta,
                "classification": m.classification,
            })

    # Compute totals
    phase_totals = {}
    for phase in phases:
        phase_totals[phase] = sum(
            matrix[phase][t]["count"] for t in types
        )

    type_totals = {}
    for t in types:
        type_totals[t] = sum(
            matrix[p][t]["count"] for p in phases
        )

    return {
        "matrix": matrix,
        "phase_totals": phase_totals,
        "type_totals": type_totals,
        "total_mistakes": sum(phase_totals.values()),
    }


def get_repeated_mistakes(
    db: Session,
    min_frequency: int = 2,
) -> list[dict]:
    """Get patterns ordered by frequency (most repeated first).

    Only includes patterns with frequency >= min_frequency.
    """
    patterns = (
        db.query(Pattern)
        .filter(
            Pattern.resolved.is_(False),
            Pattern.frequency >= min_frequency,
        )
        .order_by(Pattern.frequency.desc())
        .all()
    )

    result = []
    for p in patterns:
        instances = (
            db.query(PatternInstance)
            .filter(PatternInstance.pattern_id == p.id)
            .all()
        )

        ack_status = "new"
        if p.acknowledged:
            if p.post_acknowledgment_count > 0:
                ack_status = "recurring"
            else:
                ack_status = "acknowledged"

        result.append({
            "id": p.id,
            "label": p.label,
            "description": p.description,
            "category": p.category,
            "mistake_type": p.mistake_type,
            "severity_score": p.severity_score,
            "frequency": p.frequency,
            "first_seen": (
                str(p.first_seen) if p.first_seen else None
            ),
            "last_seen": (
                str(p.last_seen) if p.last_seen else None
            ),
            "acknowledgment_status": ack_status,
            "post_acknowledgment_count": p.post_acknowledgment_count,
            "training_recommendation": p.training_recommendation,
            "instance_count": len(instances),
            "example_game_ids": (
                json.loads(p.example_game_ids)
                if p.example_game_ids else []
            ),
        })

    return result


def get_mistake_trends(
    db: Session,
    period_games: int = 10,
) -> dict:
    """Compute accuracy trends by phase and type.

    Compares the most recent `period_games` analyzed games
    to the older games.
    """
    all_games = (
        db.query(Game)
        .filter(Game.analysis_status == "analyzed")
        .order_by(Game.date_played.desc())
        .all()
    )

    if len(all_games) < 2:
        return {"trends": {}, "has_data": False}

    recent_ids = {g.id for g in all_games[:period_games]}
    older_ids = {g.id for g in all_games[period_games:]}

    if not older_ids:
        return {"trends": {}, "has_data": False}

    def _accuracy_for_games(game_ids: set) -> dict:
        moves = (
            db.query(Move)
            .filter(
                Move.game_id.in_(game_ids),
                Move.classification.isnot(None),
            )
            .all()
        )
        if not moves:
            return {}

        by_phase: dict[str, dict] = defaultdict(
            lambda: {"total": 0, "good": 0}
        )
        for m in moves:
            phase = m.phase or "middlegame"
            by_phase[phase]["total"] += 1
            if m.classification in ("best", "good"):
                by_phase[phase]["good"] += 1

        result = {}
        for phase, counts in by_phase.items():
            if counts["total"] > 0:
                result[phase] = round(
                    counts["good"] / counts["total"] * 100, 1
                )
        return result

    recent_acc = _accuracy_for_games(recent_ids)
    older_acc = _accuracy_for_games(older_ids)

    trends = {}
    all_phases = set(list(recent_acc.keys()) + list(older_acc.keys()))
    for phase in all_phases:
        recent_val = recent_acc.get(phase, 0)
        older_val = older_acc.get(phase, 0)
        trends[phase] = {
            "recent": recent_val,
            "older": older_val,
            "delta": round(recent_val - older_val, 1),
            "improving": recent_val > older_val,
        }

    return {"trends": trends, "has_data": True}
