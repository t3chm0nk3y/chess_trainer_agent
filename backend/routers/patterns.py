from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db

router = APIRouter()


@router.get("")
async def list_patterns(db: Session = Depends(get_db)):
    """All patterns, sorted by severity."""
    from backend.models import Pattern

    patterns = db.query(Pattern).order_by(Pattern.severity_score.desc()).all()
    return {"patterns": [_pattern_to_dict(p) for p in patterns]}


@router.get("/{pattern_id}")
async def get_pattern(pattern_id: str, db: Session = Depends(get_db)):
    """Pattern detail with all instances."""
    from backend.models import Pattern

    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
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


@router.post("/refresh")
async def refresh_patterns(db: Session = Depends(get_db)):
    """Re-run Claude pattern synthesis."""
    # TODO: trigger pattern_synthesis workflow
    return {"status": "queued"}


def _pattern_to_dict(pattern) -> dict:
    return {
        "id": pattern.id,
        "label": pattern.label,
        "description": pattern.description,
        "category": pattern.category,
        "severity_score": pattern.severity_score,
        "frequency": pattern.frequency,
        "first_seen": str(pattern.first_seen) if pattern.first_seen else None,
        "last_seen": str(pattern.last_seen) if pattern.last_seen else None,
        "resolved": pattern.resolved,
        "example_game_ids": pattern.example_game_ids,
        "training_recommendation": pattern.training_recommendation,
    }
