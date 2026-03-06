from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db

router = APIRouter()


@router.get("")
async def get_progress(db: Session = Depends(get_db)):
    """Progress snapshots over time."""
    from backend.models import ProgressSnapshot

    snapshots = db.query(ProgressSnapshot).order_by(ProgressSnapshot.snapshot_date).all()
    return {
        "snapshots": [
            {
                "id": s.id,
                "date": str(s.snapshot_date),
                "total_games": s.total_games,
                "avg_accuracy": s.avg_accuracy,
                "patterns_json": s.patterns_json,
            }
            for s in snapshots
        ]
    }


@router.get("/summary")
async def progress_summary(db: Session = Depends(get_db)):
    """Current accuracy stats and pattern trends."""
    from backend.models import Game, Move, Pattern

    total_games = db.query(Game).filter(Game.analysis_status == "analyzed").count()
    total_moves = db.query(Move).filter(Move.classification.isnot(None)).count()
    good_moves = (
        db.query(Move).filter(Move.classification.in_(["best", "good"])).count()
    )
    accuracy = (good_moves / total_moves * 100) if total_moves > 0 else 0.0
    active_patterns = db.query(Pattern).filter(Pattern.resolved.is_(False)).count()

    return {
        "total_games": total_games,
        "total_moves": total_moves,
        "accuracy": round(accuracy, 1),
        "active_patterns": active_patterns,
    }
