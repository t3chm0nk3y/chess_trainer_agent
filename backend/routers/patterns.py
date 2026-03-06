"""API endpoints for pattern management and acknowledgment."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Pattern, PatternAcknowledgment

router = APIRouter()


class AcknowledgeRequest(BaseModel):
    player_note: str | None = None


@router.get("")
async def list_patterns(db: Session = Depends(get_db)):
    """All patterns, sorted by severity."""
    patterns = (
        db.query(Pattern)
        .order_by(Pattern.severity_score.desc())
        .all()
    )
    return {"patterns": [_pattern_to_dict(p) for p in patterns]}


@router.get("/acknowledged")
async def list_acknowledged(db: Session = Depends(get_db)):
    """List all acknowledged but unresolved patterns."""
    patterns = (
        db.query(Pattern)
        .filter(
            Pattern.acknowledged.is_(True),
            Pattern.resolved.is_(False),
        )
        .order_by(Pattern.post_acknowledgment_count.desc())
        .all()
    )
    return {
        "patterns": [
            {
                "id": p.id,
                "label": p.label,
                "description": p.description,
                "category": p.category,
                "frequency": p.frequency,
                "acknowledged_at": (
                    p.acknowledged_at.isoformat()
                    if p.acknowledged_at else None
                ),
                "post_acknowledgment_count": (
                    p.post_acknowledgment_count
                ),
                "severity_score": p.severity_score,
            }
            for p in patterns
        ],
        "total": len(patterns),
    }


@router.post("/refresh")
async def refresh_patterns(db: Session = Depends(get_db)):
    """Re-run Claude pattern synthesis."""
    # TODO: trigger pattern_synthesis workflow
    return {"status": "queued"}


@router.get("/{pattern_id}")
async def get_pattern(
    pattern_id: str, db: Session = Depends(get_db)
):
    """Pattern detail with all instances."""
    pattern = (
        db.query(Pattern).filter(Pattern.id == pattern_id).first()
    )
    if not pattern:
        raise HTTPException(
            status_code=404, detail="Pattern not found"
        )
    d = _pattern_to_dict(pattern)
    d["instances"] = [
        {
            "id": inst.id,
            "game_id": inst.game_id,
            "move_id": inst.move_id,
            "notes": inst.notes,
        }
        for inst in pattern.instances
    ]
    return d


@router.post("/{pattern_id}/acknowledge")
async def acknowledge_pattern(
    pattern_id: str,
    body: AcknowledgeRequest | None = None,
    db: Session = Depends(get_db),
):
    """Acknowledge a pattern."""
    pattern = (
        db.query(Pattern).filter(Pattern.id == pattern_id).first()
    )
    if not pattern:
        raise HTTPException(
            status_code=404, detail="Pattern not found"
        )

    now = datetime.utcnow()
    pattern.acknowledged = True
    pattern.acknowledged_at = now

    ack = PatternAcknowledgment(
        pattern_id=pattern_id,
        acknowledged_at=now,
        player_note=body.player_note if body else None,
    )
    db.add(ack)
    db.commit()

    return {
        "status": "acknowledged",
        "pattern_id": pattern_id,
        "acknowledged_at": now.isoformat(),
    }


@router.delete("/{pattern_id}/acknowledge")
async def revoke_acknowledgment(
    pattern_id: str, db: Session = Depends(get_db)
):
    """Revoke acknowledgment of a pattern."""
    pattern = (
        db.query(Pattern).filter(Pattern.id == pattern_id).first()
    )
    if not pattern:
        raise HTTPException(
            status_code=404, detail="Pattern not found"
        )

    pattern.acknowledged = False
    pattern.acknowledged_at = None
    pattern.post_acknowledgment_count = 0

    db.query(PatternAcknowledgment).filter(
        PatternAcknowledgment.pattern_id == pattern_id
    ).delete()

    db.commit()
    return {"status": "revoked", "pattern_id": pattern_id}


@router.post("/{pattern_id}/resolve")
async def resolve_pattern(
    pattern_id: str, db: Session = Depends(get_db)
):
    """Mark a pattern as resolved."""
    pattern = (
        db.query(Pattern).filter(Pattern.id == pattern_id).first()
    )
    if not pattern:
        raise HTTPException(
            status_code=404, detail="Pattern not found"
        )

    pattern.resolved = True
    db.commit()
    return {"status": "resolved", "pattern_id": pattern_id}


def _pattern_to_dict(pattern) -> dict:
    return {
        "id": pattern.id,
        "label": pattern.label,
        "description": pattern.description,
        "category": pattern.category,
        "severity_score": pattern.severity_score,
        "frequency": pattern.frequency,
        "first_seen": (
            str(pattern.first_seen) if pattern.first_seen else None
        ),
        "last_seen": (
            str(pattern.last_seen) if pattern.last_seen else None
        ),
        "resolved": pattern.resolved,
        "acknowledged": pattern.acknowledged,
        "post_acknowledgment_count": (
            pattern.post_acknowledgment_count
        ),
        "example_game_ids": pattern.example_game_ids,
        "training_recommendation": pattern.training_recommendation,
    }
