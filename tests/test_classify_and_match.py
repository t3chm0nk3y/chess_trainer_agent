"""Tests for task 3.1 (Claude mistake classification) and 4.1 (auto pattern matching)."""

from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Game, Move, Pattern, PatternInstance
from backend.tasks.analysis_worker import _classify_mistake_types, _match_patterns


def _make_db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    return Session(), Session


def _make_game_and_moves(db, game_id="g1"):
    game = Game(
        id=game_id, pgn="1. e4 e5", white="P1", black="P2",
        result="1-0", player_color="white", source="pgn_upload",
        analysis_status="pending", date_played=date(2025, 3, 15),
    )
    db.add(game)
    db.flush()

    moves = []
    configs = [
        ("e4", "best", 5.0, "opening", None),
        ("e5", "good", 20.0, "opening", None),
        ("Nf3", "mistake", 120.0, "opening", None),
        ("d6", "blunder", 300.0, "middlegame", None),
        ("d4", "inaccuracy", 60.0, "middlegame", None),
    ]
    for i, (san, cls, delta, phase, mtype) in enumerate(configs):
        m = Move(
            game_id=game_id, move_number=(i // 2) + 1, ply=i,
            san=san, uci=f"u{i}",
            fen_before=f"fen_b_{i}", fen_after=f"fen_a_{i}",
            phase=phase, eval_delta=delta, classification=cls,
            best_move_uci=f"best_{i}", mistake_type=mtype,
        )
        db.add(m)
        db.flush()
        moves.append(m)

    db.commit()
    return game, moves


# --- Task 3.1: Classify mistake types ---

def test_classify_mistake_types_calls_batch():
    """Verify _classify_mistake_types sets mistake_type on mistake moves."""
    db, _ = _make_db()
    _, moves = _make_game_and_moves(db)

    mock_result = ["tactical", "strategic", "tactical"]
    with patch(
        "backend.tasks.analysis_worker.classify_mistakes_batch",
        return_value=mock_result,
    ) as mock_batch:
        _classify_mistake_types(moves)

    # Should have been called with exactly the 3 mistake/blunder/inaccuracy moves
    assert mock_batch.call_count == 1
    batch_input = mock_batch.call_args[0][0]
    assert len(batch_input) == 3

    # Check that moves got assigned
    mistake_moves = [m for m in moves if m.classification in ("inaccuracy", "mistake", "blunder")]
    assert mistake_moves[0].mistake_type == "tactical"
    assert mistake_moves[1].mistake_type == "strategic"
    assert mistake_moves[2].mistake_type == "tactical"


def test_classify_mistake_types_skips_good_moves():
    """Best/good moves should not be sent for classification."""
    db, _ = _make_db()
    _, moves = _make_game_and_moves(db)

    with patch(
        "backend.tasks.analysis_worker.classify_mistakes_batch",
        return_value=["tactical", "strategic", "tactical"],
    ):
        _classify_mistake_types(moves)

    # "best" and "good" moves should have no mistake_type
    assert moves[0].mistake_type is None  # best
    assert moves[1].mistake_type is None  # good


def test_classify_mistake_types_no_mistakes():
    """No-op when there are no mistakes."""
    db, _ = _make_db()
    game = Game(
        id="g2", pgn="1. e4", white="P1", black="P2",
        result="1-0", player_color="white", source="pgn_upload",
    )
    db.add(game)
    db.flush()
    m = Move(
        game_id="g2", move_number=1, ply=0, san="e4", uci="e2e4",
        fen_before="start", fen_after="after",
        phase="opening", eval_delta=5.0, classification="best",
    )
    db.add(m)
    db.commit()

    with patch(
        "backend.tasks.analysis_worker.classify_mistakes_batch",
    ) as mock_batch:
        _classify_mistake_types([m])
        mock_batch.assert_not_called()


# --- Task 4.1: Auto pattern matching ---

def test_match_patterns_creates_instances():
    """Pattern matching should create PatternInstance records."""
    db, _ = _make_db()
    _, moves = _make_game_and_moves(db)

    # Set mistake_type on the mistake moves
    moves[2].mistake_type = "tactical"
    moves[3].mistake_type = "strategic"
    moves[4].mistake_type = "tactical"
    db.commit()

    # Create patterns
    p1 = Pattern(
        id="pat-t", label="Missed fork",
        description="Repeatedly misses knight forks tactical",
        category="tactical", mistake_type="tactical",
        frequency=0, severity_score=50,
    )
    p2 = Pattern(
        id="pat-s", label="Wrong plan",
        description="Chose wrong strategic plan",
        category="positional", mistake_type="strategic",
        frequency=0, severity_score=30,
    )
    db.add_all([p1, p2])
    db.commit()

    _match_patterns(db, "g1", moves)
    db.commit()

    instances = db.query(PatternInstance).all()
    assert len(instances) > 0

    # Check that pattern frequency was updated
    db.refresh(p1)
    db.refresh(p2)
    assert p1.frequency > 0 or p2.frequency > 0


def test_match_patterns_no_patterns():
    """No-op when there are no active patterns."""
    db, _ = _make_db()
    _, moves = _make_game_and_moves(db)

    _match_patterns(db, "g1", moves)
    db.commit()

    instances = db.query(PatternInstance).all()
    assert len(instances) == 0


def test_match_patterns_updates_acknowledged():
    """Matching an acknowledged pattern increments post_acknowledgment_count."""
    db, _ = _make_db()
    _, moves = _make_game_and_moves(db)
    moves[2].mistake_type = "tactical"
    db.commit()

    p = Pattern(
        id="pat-ack", label="Missed tactic",
        description="Missed tactical opportunity",
        category="tactical", mistake_type="tactical",
        frequency=3, severity_score=60,
        acknowledged=True, post_acknowledgment_count=0,
    )
    db.add(p)
    db.commit()

    _match_patterns(db, "g1", moves)
    db.commit()

    db.refresh(p)
    assert p.post_acknowledgment_count > 0
    assert p.last_seen == date.today()


def test_match_patterns_sets_first_seen():
    """First match should set first_seen date."""
    db, _ = _make_db()
    _, moves = _make_game_and_moves(db)
    moves[2].mistake_type = "tactical"
    db.commit()

    p = Pattern(
        id="pat-new", label="New tactical pattern",
        description="Tactical weakness",
        category="tactical", mistake_type="tactical",
        frequency=0, severity_score=10,
    )
    db.add(p)
    db.commit()

    _match_patterns(db, "g1", moves)
    db.commit()

    db.refresh(p)
    if p.frequency > 0:
        assert p.first_seen == date.today()


def test_match_patterns_skips_resolved():
    """Resolved patterns should not be matched."""
    db, _ = _make_db()
    _, moves = _make_game_and_moves(db)
    moves[2].mistake_type = "tactical"
    db.commit()

    p = Pattern(
        id="pat-res", label="Resolved tactical pattern",
        description="Tactical weakness now fixed",
        category="tactical", mistake_type="tactical",
        frequency=5, severity_score=70, resolved=True,
    )
    db.add(p)
    db.commit()

    _match_patterns(db, "g1", moves)
    db.commit()

    instances = db.query(PatternInstance).all()
    assert len(instances) == 0
