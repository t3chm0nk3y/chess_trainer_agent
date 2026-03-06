"""Tests for data model changes -- new tables and columns."""

from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base
from backend.models import (
    Game,
    MistakeCategory,
    Move,
    OpeningStats,
    Pattern,
    PatternAcknowledgment,
    ProgressSnapshot,
)


def _make_db() -> Session:
    """Create a fresh in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_mistake_category_hierarchy():
    db = _make_db()
    parent = MistakeCategory(
        name="tactical", description="Tactical mistakes",
        detection_method="engine",
    )
    db.add(parent)
    db.flush()

    child = MistakeCategory(
        parent_id=parent.id, name="missed_tactic",
        description="Missed winning tactic", detection_method="engine",
    )
    db.add(child)
    db.commit()

    loaded = db.query(MistakeCategory).filter(MistakeCategory.parent_id.is_(None)).first()
    assert loaded.name == "tactical"
    assert len(loaded.children) == 1
    assert loaded.children[0].name == "missed_tactic"
    db.close()


def test_pattern_acknowledgment():
    db = _make_db()
    pattern = Pattern(
        label="Test pattern", description="A test", category="tactical",
        severity_score=50.0, frequency=3,
    )
    db.add(pattern)
    db.flush()

    ack = PatternAcknowledgment(pattern_id=pattern.id, player_note="I'll work on this")
    db.add(ack)
    db.commit()

    loaded = db.query(Pattern).first()
    assert len(loaded.acknowledgments) == 1
    assert loaded.acknowledgments[0].player_note == "I'll work on this"
    db.close()


def test_pattern_new_fields():
    db = _make_db()
    pattern = Pattern(
        label="Test", description="Desc", category="tactical",
        acknowledged=True, acknowledged_at=datetime.utcnow(),
        post_acknowledgment_count=2, mistake_type="tactical",
    )
    db.add(pattern)
    db.commit()

    loaded = db.query(Pattern).first()
    assert loaded.acknowledged is True
    assert loaded.post_acknowledgment_count == 2
    assert loaded.mistake_type == "tactical"
    db.close()


def test_move_new_fields():
    db = _make_db()
    game = Game(
        pgn="1. e4 e5", white="W", black="B", result="1-0",
        player_color="white", source="pgn_upload",
    )
    db.add(game)
    db.flush()

    move = Move(
        game_id=game.id, move_number=1, ply=0, san="e4", uci="e2e4",
        fen_before="start", fen_after="after",
        best_move_uci="e2e4", mistake_type="tactical",
    )
    db.add(move)
    db.commit()

    loaded = db.query(Move).first()
    assert loaded.best_move_uci == "e2e4"
    assert loaded.mistake_type == "tactical"
    db.close()


def test_opening_stats():
    db = _make_db()
    stats = OpeningStats(
        eco_code="B08", opening_name="Pirc Defense",
        variation_name="Classical Variation",
        total_games=12, wins=2, losses=9, draws=1,
        avg_cp_loss=45.3, divergence_move=9,
    )
    db.add(stats)
    db.commit()

    loaded = db.query(OpeningStats).first()
    assert loaded.eco_code == "B08"
    assert loaded.losses == 9
    assert loaded.divergence_move == 9
    db.close()


def test_progress_snapshot_new_fields():
    db = _make_db()
    snap = ProgressSnapshot(
        snapshot_date=date.today(), total_games=20, avg_accuracy=72.5,
        accuracy_opening=80.0, accuracy_middlegame=70.0, accuracy_endgame=65.0,
        acknowledged_patterns=3, recurring_patterns=1, resolved_patterns=2,
        session_id="session-001",
    )
    db.add(snap)
    db.commit()

    loaded = db.query(ProgressSnapshot).first()
    assert loaded.accuracy_opening == 80.0
    assert loaded.acknowledged_patterns == 3
    assert loaded.session_id == "session-001"
    db.close()
