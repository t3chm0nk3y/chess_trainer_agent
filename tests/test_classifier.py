"""Tests for move classification and phase detection."""

from backend.services.classifier import classify_move, detect_phase


def test_classify_best():
    assert classify_move(5) == "best"
    assert classify_move(0) == "best"
    assert classify_move(10) == "best"


def test_classify_good():
    assert classify_move(15) == "good"
    assert classify_move(30) == "good"


def test_classify_inaccuracy():
    assert classify_move(50) == "inaccuracy"
    assert classify_move(70) == "inaccuracy"


def test_classify_mistake():
    assert classify_move(100) == "mistake"
    assert classify_move(150) == "mistake"


def test_classify_blunder():
    assert classify_move(200) == "blunder"
    assert classify_move(500) == "blunder"


def test_classify_none():
    assert classify_move(None) is None


def test_detect_opening():
    # Starting position, early game
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    assert detect_phase(fen) == "opening"


def test_detect_endgame():
    # King + rook vs king + rook
    fen = "4k3/8/8/8/8/8/8/R3K3 w - - 0 40"
    assert detect_phase(fen) == "endgame"
