"""Tests for opening line analysis."""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Game, Move, OpeningStats
from backend.services.opening_analyzer import (
    compute_opening_stats,
    get_opening_detail,
    get_opening_stats_ranked,
)


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _add_game(
    db, eco, opening_name, result, player_color="white",
    opening_moves=None, date_played=None,
):
    """Helper to add a game with opening-phase moves."""
    game = Game(
        pgn="1. e4 e5",
        white="Player" if player_color == "white" else "Opp",
        black="Opp" if player_color == "white" else "Player",
        result=result,
        date_played=date_played or date(2025, 3, 15),
        opening_eco=eco,
        opening_name=opening_name,
        player_color=player_color,
        source="pgn_upload",
        analysis_status="analyzed",
    )
    db.add(game)
    db.flush()

    moves = opening_moves or ["e4", "e5", "Nf3", "Nc6"]
    for ply, san in enumerate(moves):
        move = Move(
            game_id=game.id,
            move_number=(ply // 2) + 1,
            ply=ply,
            san=san,
            uci=f"m{ply}",
            fen_before=f"fen_before_{ply}",
            fen_after=f"fen_after_{ply}",
            phase="opening",
            eval_delta=10.0 + ply,
            classification="good",
        )
        db.add(move)

    db.commit()
    return game


def test_compute_stats_basic():
    """Should compute win/loss/draw for a single opening."""
    db = _make_db()
    _add_game(db, "C50", "Italian Game", "1-0")
    _add_game(db, "C50", "Italian Game", "0-1")
    _add_game(db, "C50", "Italian Game", "1/2-1/2")

    stats = compute_opening_stats(db)
    assert len(stats) == 1
    s = stats[0]
    assert s.eco_code == "C50"
    assert s.total_games == 3
    assert s.wins == 1
    assert s.losses == 1
    assert s.draws == 1
    db.close()


def test_compute_stats_multiple_openings():
    """Should group by opening correctly."""
    db = _make_db()
    _add_game(db, "B20", "Sicilian Defense", "0-1")
    _add_game(db, "B20", "Sicilian Defense", "0-1")
    _add_game(db, "C50", "Italian Game", "1-0")

    stats = compute_opening_stats(db)
    assert len(stats) == 2
    db.close()


def test_compute_stats_variation_split():
    """Should split base opening from variation."""
    db = _make_db()
    _add_game(db, "B90", "Sicilian Defense: Najdorf Variation", "0-1")
    _add_game(db, "B20", "Sicilian Defense", "1-0")

    stats = compute_opening_stats(db)
    assert len(stats) == 2

    najdorf = [s for s in stats if s.variation_name == "Najdorf Variation"]
    assert len(najdorf) == 1
    assert najdorf[0].opening_name == "Sicilian Defense"
    db.close()


def test_stats_ranked_by_loss_pct():
    """Should rank openings by loss percentage."""
    db = _make_db()
    _add_game(db, "B20", "Sicilian Defense", "0-1")
    _add_game(db, "B20", "Sicilian Defense", "0-1")
    _add_game(db, "C50", "Italian Game", "1-0")
    _add_game(db, "C50", "Italian Game", "0-1")

    compute_opening_stats(db)
    ranked = get_opening_stats_ranked(db, sort_by="loss_pct")

    assert len(ranked) == 2
    assert ranked[0]["eco_code"] == "B20"
    assert ranked[0]["loss_pct"] == 100.0
    assert ranked[1]["eco_code"] == "C50"
    assert ranked[1]["loss_pct"] == 50.0
    db.close()


def test_player_color_black():
    """Should correctly determine wins/losses when player is black."""
    db = _make_db()
    # Player is black and wins (result 0-1)
    _add_game(
        db, "C50", "Italian Game", "0-1", player_color="black"
    )
    # Player is black and loses (result 1-0)
    _add_game(
        db, "C50", "Italian Game", "1-0", player_color="black"
    )

    stats = compute_opening_stats(db)
    assert stats[0].wins == 1
    assert stats[0].losses == 1
    db.close()


def test_avg_cp_loss():
    """Should compute average centipawn loss during opening."""
    db = _make_db()
    _add_game(db, "C50", "Italian Game", "1-0")

    stats = compute_opening_stats(db)
    assert stats[0].avg_cp_loss is not None
    assert stats[0].avg_cp_loss > 0
    db.close()


def test_divergence_move_detection():
    """Should find divergence between won and lost games."""
    db = _make_db()
    # Won game plays e4 e5 Nf3 Nc6
    _add_game(
        db, "C50", "Italian Game", "1-0",
        opening_moves=["e4", "e5", "Nf3", "Nc6"],
    )
    # Lost game diverges at move 2 (plays d6 instead of Nc6)
    _add_game(
        db, "C50", "Italian Game", "0-1",
        opening_moves=["e4", "e5", "Nf3", "d6"],
    )

    stats = compute_opening_stats(db)
    s = stats[0]
    # Divergence at ply 3 (d6 vs Nc6) = move number 2
    assert s.divergence_move == 2
    db.close()


def test_get_opening_detail():
    """Should return full detail with games list."""
    db = _make_db()
    _add_game(db, "B20", "Sicilian Defense", "0-1")
    _add_game(db, "B20", "Sicilian Defense", "1-0")

    compute_opening_stats(db)
    detail = get_opening_detail(db, "B20")

    assert detail is not None
    assert detail["eco_code"] == "B20"
    assert len(detail["lines"]) == 1
    line = detail["lines"][0]
    assert line["total_games"] == 2
    assert len(line["games"]) == 2
    db.close()


def test_get_opening_detail_not_found():
    """Should return None for unknown ECO code."""
    db = _make_db()
    detail = get_opening_detail(db, "Z99")
    assert detail is None
    db.close()


def test_no_analyzed_games():
    """Should return empty list when no games are analyzed."""
    db = _make_db()
    stats = compute_opening_stats(db)
    assert stats == []
    db.close()


def test_refresh_replaces_old_stats():
    """Running compute twice should replace, not duplicate."""
    db = _make_db()
    _add_game(db, "C50", "Italian Game", "1-0")

    compute_opening_stats(db)
    assert db.query(OpeningStats).count() == 1

    _add_game(db, "C50", "Italian Game", "0-1")
    compute_opening_stats(db)
    assert db.query(OpeningStats).count() == 1

    s = db.query(OpeningStats).first()
    assert s.total_games == 2
    db.close()
