"""API endpoints for progress tracking."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, Move, Pattern, ProgressSnapshot

router = APIRouter()


@router.get("")
async def get_progress(db: Session = Depends(get_db)):
    """Progress snapshots over time."""
    snapshots = (
        db.query(ProgressSnapshot)
        .order_by(ProgressSnapshot.snapshot_date)
        .all()
    )
    return {
        "snapshots": [
            {
                "id": s.id,
                "date": str(s.snapshot_date),
                "total_games": s.total_games,
                "avg_accuracy": s.avg_accuracy,
                "accuracy_opening": s.accuracy_opening,
                "accuracy_middlegame": s.accuracy_middlegame,
                "accuracy_endgame": s.accuracy_endgame,
                "acknowledged_patterns": s.acknowledged_patterns,
                "recurring_patterns": s.recurring_patterns,
                "resolved_patterns": s.resolved_patterns,
                "session_id": s.session_id,
                "patterns_json": s.patterns_json,
            }
            for s in snapshots
        ]
    }


@router.get("/summary")
async def progress_summary(db: Session = Depends(get_db)):
    """Current accuracy stats and pattern trends."""
    total_games = (
        db.query(Game)
        .filter(Game.analysis_status == "analyzed")
        .count()
    )
    total_moves = (
        db.query(Move)
        .filter(Move.classification.isnot(None))
        .count()
    )
    good_moves = (
        db.query(Move)
        .filter(Move.classification.in_(["best", "good"]))
        .count()
    )
    accuracy = (
        round(good_moves / total_moves * 100, 1)
        if total_moves > 0 else 0.0
    )

    # Per-phase accuracy
    phase_accuracy = {}
    for phase in ["opening", "middlegame", "endgame"]:
        phase_total = (
            db.query(Move)
            .filter(
                Move.phase == phase,
                Move.classification.isnot(None),
            )
            .count()
        )
        phase_good = (
            db.query(Move)
            .filter(
                Move.phase == phase,
                Move.classification.in_(["best", "good"]),
            )
            .count()
        )
        if phase_total > 0:
            phase_accuracy[phase] = round(
                phase_good / phase_total * 100, 1
            )

    active_patterns = (
        db.query(Pattern).filter(Pattern.resolved.is_(False)).count()
    )
    acknowledged = (
        db.query(Pattern)
        .filter(
            Pattern.acknowledged.is_(True),
            Pattern.resolved.is_(False),
        )
        .count()
    )
    recurring = (
        db.query(Pattern)
        .filter(
            Pattern.acknowledged.is_(True),
            Pattern.resolved.is_(False),
            Pattern.post_acknowledgment_count > 0,
        )
        .count()
    )
    resolved = (
        db.query(Pattern).filter(Pattern.resolved.is_(True)).count()
    )

    return {
        "total_games": total_games,
        "total_moves": total_moves,
        "accuracy": accuracy,
        "phase_accuracy": phase_accuracy,
        "active_patterns": active_patterns,
        "acknowledged_patterns": acknowledged,
        "recurring_patterns": recurring,
        "resolved_patterns": resolved,
    }


@router.get("/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """List play sessions grouped by date with summary stats."""
    games = (
        db.query(Game)
        .filter(
            Game.analysis_status == "analyzed",
            Game.date_played.isnot(None),
        )
        .order_by(Game.date_played.desc())
        .all()
    )

    sessions: dict[str, dict] = {}
    for g in games:
        key = str(g.date_played)
        if key not in sessions:
            sessions[key] = {
                "date": key,
                "games": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "game_ids": [],
            }
        s = sessions[key]
        s["games"] += 1
        s["game_ids"].append(g.id)

        if g.result == "1/2-1/2":
            s["draws"] += 1
        elif (
            (g.player_color == "white" and g.result == "1-0")
            or (g.player_color == "black" and g.result == "0-1")
        ):
            s["wins"] += 1
        else:
            s["losses"] += 1

    # Compute accuracy per session
    result = []
    for key, s in sessions.items():
        total = (
            db.query(Move)
            .filter(
                Move.game_id.in_(s["game_ids"]),
                Move.classification.isnot(None),
            )
            .count()
        )
        good = (
            db.query(Move)
            .filter(
                Move.game_id.in_(s["game_ids"]),
                Move.classification.in_(["best", "good"]),
            )
            .count()
        )
        s["accuracy"] = (
            round(good / total * 100, 1) if total > 0 else 0.0
        )
        del s["game_ids"]
        result.append(s)

    return {"sessions": result}


@router.get("/compare")
async def compare_periods(
    from_date: str = Query(
        ..., description="Start date (YYYY-MM-DD)"
    ),
    to_date: str = Query(
        ..., description="End date (YYYY-MM-DD)"
    ),
    db: Session = Depends(get_db),
):
    """Compare two time periods side by side.

    Compares [from_date, to_date] vs the equivalent prior period.
    """
    try:
        end = date.fromisoformat(to_date)
        start = date.fromisoformat(from_date)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    period_days = (end - start).days
    prior_end = start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=period_days)

    def _period_stats(d_start: date, d_end: date) -> dict:
        games = (
            db.query(Game)
            .filter(
                Game.analysis_status == "analyzed",
                Game.date_played >= d_start,
                Game.date_played <= d_end,
            )
            .all()
        )
        game_ids = [g.id for g in games]

        if not game_ids:
            return {
                "games": 0, "accuracy": 0.0,
                "phase_accuracy": {},
                "wins": 0, "losses": 0, "draws": 0,
            }

        total = (
            db.query(Move)
            .filter(
                Move.game_id.in_(game_ids),
                Move.classification.isnot(None),
            )
            .count()
        )
        good = (
            db.query(Move)
            .filter(
                Move.game_id.in_(game_ids),
                Move.classification.in_(["best", "good"]),
            )
            .count()
        )

        phase_acc = {}
        for phase in ["opening", "middlegame", "endgame"]:
            pt = (
                db.query(Move)
                .filter(
                    Move.game_id.in_(game_ids),
                    Move.phase == phase,
                    Move.classification.isnot(None),
                )
                .count()
            )
            pg = (
                db.query(Move)
                .filter(
                    Move.game_id.in_(game_ids),
                    Move.phase == phase,
                    Move.classification.in_(["best", "good"]),
                )
                .count()
            )
            if pt > 0:
                phase_acc[phase] = round(pg / pt * 100, 1)

        wins = sum(
            1 for g in games
            if (g.player_color == "white" and g.result == "1-0")
            or (g.player_color == "black" and g.result == "0-1")
        )
        losses = sum(
            1 for g in games
            if (g.player_color == "white" and g.result == "0-1")
            or (g.player_color == "black" and g.result == "1-0")
        )
        draws = sum(
            1 for g in games if g.result == "1/2-1/2"
        )

        return {
            "games": len(games),
            "accuracy": (
                round(good / total * 100, 1) if total > 0 else 0.0
            ),
            "phase_accuracy": phase_acc,
            "wins": wins,
            "losses": losses,
            "draws": draws,
        }

    current = _period_stats(start, end)
    prior = _period_stats(prior_start, prior_end)

    delta_accuracy = round(
        current["accuracy"] - prior["accuracy"], 1
    )

    return {
        "current_period": {
            "from": str(start),
            "to": str(end),
            **current,
        },
        "prior_period": {
            "from": str(prior_start),
            "to": str(prior_end),
            **prior,
        },
        "delta": {
            "accuracy": delta_accuracy,
            "games": current["games"] - prior["games"],
            "improving": delta_accuracy > 0,
        },
    }
