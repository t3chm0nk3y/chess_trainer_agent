"""Tests for PGN parsing service."""

from backend.services.pgn_parser import parse_pgn

SAMPLE_PGN = """[Event "Rated Blitz game"]
[Site "https://lichess.org/abcd1234"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]
[Date "2025.03.15"]
[ECO "B20"]
[Opening "Sicilian Defense"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 1-0"""


def test_parse_single_game():
    games = parse_pgn(SAMPLE_PGN)
    assert len(games) == 1
    game = games[0]
    assert game.white == "Player1"
    assert game.black == "Player2"
    assert game.result == "1-0"
    assert game.opening_eco == "B20"


def test_parse_moves():
    games = parse_pgn(SAMPLE_PGN)
    moves = games[0].moves
    assert len(moves) == 10  # 5 full moves = 10 half-moves
    assert moves[0].san == "e4"
    assert moves[0].ply == 0
    assert moves[1].san == "c5"
    assert moves[1].ply == 1


def test_parse_empty():
    games = parse_pgn("")
    assert games == []
