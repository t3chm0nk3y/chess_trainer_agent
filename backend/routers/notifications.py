"""API endpoints for game-level notifications."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, PatternInstance

router = APIRouter()


@router.get("/games/{game_id}/notifications")
async def game_notifications(
    game_id: str,
    db: Session = Depends(get_db),
):
    """Get pattern-match notifications for a specific game.

    Returns moves flagged as matching known patterns,
    ordered by notification priority.
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    instances = (
        db.query(PatternInstance)
        .filter(PatternInstance.game_id == game_id)
        .all()
    )

    notifications = []
    for inst in instances:
        pattern = inst.pattern
        move = inst.move

        if pattern.acknowledged and pattern.post_acknowledgment_count > 0:
            priority = 1
            priority_label = "recurring_acknowledged"
        elif not pattern.acknowledged and pattern.frequency >= 3:
            priority = 2
            priority_label = "high_frequency"
        elif pattern.frequency <= 1:
            priority = 4
            priority_label = "new"
        else:
            priority = 3
            priority_label = "moderate"

        notifications.append({
            "pattern_id": pattern.id,
            "pattern_label": pattern.label,
            "pattern_description": pattern.description,
            "category": pattern.category,
            "frequency": pattern.frequency,
            "acknowledged": pattern.acknowledged,
            "post_acknowledgment_count": (
                pattern.post_acknowledgment_count
            ),
            "severity_score": pattern.severity_score,
            "move_id": move.id,
            "ply": move.ply,
            "san": move.san,
            "move_number": move.move_number,
            "eval_delta": move.eval_delta,
            "notes": inst.notes,
            "priority": priority,
            "priority_label": priority_label,
        })

    notifications.sort(key=lambda n: (n["priority"], -n["frequency"]))

    matched_count = len(notifications)
    recurring_count = sum(
        1 for n in notifications
        if n["priority_label"] == "recurring_acknowledged"
    )
    new_count = sum(
        1 for n in notifications
        if n["priority_label"] == "new"
    )

    return {
        "game_id": game_id,
        "notifications": notifications,
        "summary": {
            "total_matched": matched_count,
            "recurring_acknowledged": recurring_count,
            "new_patterns": new_count,
        },
    }


@router.get("/notifications/recent")
async def recent_notifications(db: Session = Depends(get_db)):
    """Get notifications from the most recently analyzed game."""
    game = (
        db.query(Game)
        .filter(Game.analysis_status == "analyzed")
        .order_by(Game.imported_at.desc())
        .first()
    )
    if not game:
        return {
            "game_id": None,
            "notifications": [],
            "summary": {
                "total_matched": 0,
                "recurring_acknowledged": 0,
                "new_patterns": 0,
            },
        }

    return await game_notifications(game.id, db)
