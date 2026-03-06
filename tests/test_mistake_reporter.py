"""Tests for mistake categorization and reporting."""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Game, Move, Pattern
from backend.services.mistake_reporter import (
    get_mistake_matrix,
    get_mistake_trends,
    get_repeated_mistakes,
)


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _add_game_with_mistakes(db, mistakes, date_played=None):
    """Helper: create a game with specific classified moves.

    mistakes: list of (phase, classification, mistake_type) tuples.
    """
    game = Game(
        pgn="1. e4",
        white="P", black="O", result="1-0",
        player_color="white", source="pgn_upload",
        analysis_status="analyzed",
        date_played=date_played or date(2025, 3, 1),
    )
    db.add(game)
    db.flush()

    for i, (phase, classification, mtype) in enumerate(mistakes):
        move = Move(
            game_id=game.id, move_number=(i // 2) + 1, ply=i,
            san=f"m{i}", uci=f"u{i}",
            fen_before=f"fb{i}", fen_after=f"fa{i}",
            phase=phase, classification=classification,
            mistake_type=mtype, eval_delta=50.0,
        )
        db.add(move)

    db.commit()
    return game


# --- Matrix tests ---

def test_matrix_basic():
    db = _make_db()
    _add_game_with_mistakes(db, [
        ("opening", "mistake", "tactical"),
        ("opening", "blunder", "strategic"),
        ("middlegame", "inaccuracy", "tactical"),
        ("endgame", "mistake", "tactical"),
    ])

    result = get_mistake_matrix(db)
    assert result["total_mistakes"] == 4
    assert result["matrix"]["opening"]["tactical"]["count"] == 1
    assert result["matrix"]["opening"]["strategic"]["count"] == 1
    assert result["matrix"]["middlegame"]["tactical"]["count"] == 1
    assert result["matrix"]["endgame"]["tactical"]["count"] == 1
    db.close()


def test_matrix_examples_capped_at_3():
    db = _make_db()
    _add_game_with_mistakes(db, [
        ("opening", "mistake", "tactical"),
        ("opening", "mistake", "tactical"),
        ("opening", "mistake", "tactical"),
        ("opening", "mistake", "tactical"),
        ("opening", "blunder", "tactical"),
    ])

    result = get_mistake_matrix(db)
    assert result["matrix"]["opening"]["tactical"]["count"] == 5
    assert len(
        result["matrix"]["opening"]["tactical"]["examples"]
    ) == 3
    db.close()


def test_matrix_unclassified_type():
    db = _make_db()
    _add_game_with_mistakes(db, [
        ("opening", "mistake", None),
    ])

    result = get_mistake_matrix(db)
    assert result["matrix"]["opening"]["unclassified"]["count"] == 1
    db.close()


def test_matrix_filter_by_game():
    db = _make_db()
    g1 = _add_game_with_mistakes(db, [
        ("opening", "mistake", "tactical"),
    ])
    _add_game_with_mistakes(db, [
        ("endgame", "blunder", "strategic"),
    ])

    result = get_mistake_matrix(db, game_id=g1.id)
    assert result["total_mistakes"] == 1
    assert result["matrix"]["opening"]["tactical"]["count"] == 1
    assert result["matrix"]["endgame"]["strategic"]["count"] == 0
    db.close()


def test_matrix_phase_totals():
    db = _make_db()
    _add_game_with_mistakes(db, [
        ("opening", "mistake", "tactical"),
        ("opening", "blunder", "strategic"),
        ("endgame", "mistake", "tactical"),
    ])

    result = get_mistake_matrix(db)
    assert result["phase_totals"]["opening"] == 2
    assert result["phase_totals"]["endgame"] == 1
    assert result["phase_totals"]["middlegame"] == 0
    db.close()


# --- Repeated mistakes tests ---

def test_repeated_empty():
    db = _make_db()
    result = get_repeated_mistakes(db)
    assert result == []
    db.close()


def test_repeated_with_patterns():
    db = _make_db()
    p = Pattern(
        label="Missed fork", description="desc",
        category="tactical", mistake_type="tactical",
        frequency=5, severity_score=70,
    )
    db.add(p)
    db.commit()

    result = get_repeated_mistakes(db, min_frequency=2)
    assert len(result) == 1
    assert result[0]["label"] == "Missed fork"
    assert result[0]["acknowledgment_status"] == "new"
    db.close()


def test_repeated_acknowledged_status():
    db = _make_db()
    p = Pattern(
        label="Hanging piece", description="desc",
        category="tactical", frequency=3,
        acknowledged=True, post_acknowledgment_count=1,
    )
    db.add(p)
    db.commit()

    result = get_repeated_mistakes(db, min_frequency=2)
    assert result[0]["acknowledgment_status"] == "recurring"
    db.close()


def test_repeated_filters_resolved():
    db = _make_db()
    Pattern(
        label="Resolved", description="desc",
        category="tactical", frequency=5, resolved=True,
    )
    p = Pattern(
        label="Active", description="desc",
        category="tactical", frequency=3,
    )
    db.add(p)
    db.commit()

    result = get_repeated_mistakes(db, min_frequency=2)
    assert len(result) == 1
    assert result[0]["label"] == "Active"
    db.close()


# --- Trends tests ---

def test_trends_insufficient_data():
    db = _make_db()
    result = get_mistake_trends(db)
    assert result["has_data"] is False
    db.close()


def test_trends_with_data():
    db = _make_db()
    # Older games: more mistakes
    for i in range(5):
        _add_game_with_mistakes(db, [
            ("opening", "mistake", "tactical"),
            ("opening", "good", None),
        ], date_played=date(2025, 1, i + 1))

    # Recent games: fewer mistakes
    for i in range(5):
        _add_game_with_mistakes(db, [
            ("opening", "good", None),
            ("opening", "best", None),
        ], date_played=date(2025, 3, i + 1))

    result = get_mistake_trends(db, period_games=5)
    assert result["has_data"] is True
    assert "opening" in result["trends"]
    # Recent should have higher accuracy
    assert result["trends"]["opening"]["recent"] > result["trends"]["opening"]["older"]
    assert result["trends"]["opening"]["improving"] is True
    db.close()
