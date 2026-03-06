"""Tests for Stockfish engine integration."""

import pytest

from backend.services.engine import StockfishEngine


@pytest.fixture(scope="module")
def engine():
    """Create a Stockfish engine instance for tests."""
    eng = StockfishEngine()
    yield eng
    eng.close()


def test_analyze_starting_position(engine):
    """Engine should return a near-zero eval for the starting position."""
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    result = engine.analyze_position(fen, depth=10)
    assert -100 < result.score_cp < 100
    assert result.best_move is not None
    assert result.mate_in is None


def test_analyze_winning_position(engine):
    """Engine should detect a large advantage when white is up a queen."""
    # White has an extra queen
    fen = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    result = engine.analyze_position(fen, depth=10)
    assert result.score_cp > 500


def test_analyze_mate_position(engine):
    """Engine should detect checkmate patterns."""
    # Mate in 1 for white (Qh7#)
    fen = "6k1/5ppp/8/8/8/8/8/4Q1K1 w - - 0 1"
    result = engine.analyze_position(fen, depth=15)
    assert result.score_cp >= 9000 or (result.mate_in is not None and result.mate_in > 0)


def test_analyze_game_positions(engine):
    """Batch analysis should return one result per position."""
    fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    ]
    results = engine.analyze_game_positions(fens, depth=8)
    assert len(results) == 3
    for r in results:
        assert hasattr(r, "score_cp")


def test_principal_variation(engine):
    """Engine should return a principal variation."""
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    result = engine.analyze_position(fen, depth=10)
    assert len(result.pv) > 0


def test_engine_not_found():
    """Should raise RuntimeError when Stockfish binary is missing."""
    eng = StockfishEngine()
    # Temporarily override the path
    from backend.config import settings
    original = settings.STOCKFISH_PATH
    settings.STOCKFISH_PATH = "/nonexistent/stockfish"
    try:
        with pytest.raises(RuntimeError, match="Stockfish not found"):
            eng.analyze_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    finally:
        settings.STOCKFISH_PATH = original
        eng.close()
