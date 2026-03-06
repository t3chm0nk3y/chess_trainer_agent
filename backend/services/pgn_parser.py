"""PGN parsing service using python-chess."""

import io
from dataclasses import dataclass
from datetime import date

import chess
import chess.pgn


@dataclass
class ParsedGame:
    pgn: str
    white: str
    black: str
    result: str
    date_played: date | None
    opening_eco: str | None
    opening_name: str | None
    moves: list["ParsedMove"]


@dataclass
class ParsedMove:
    move_number: int
    ply: int
    san: str
    uci: str
    fen_before: str
    fen_after: str


def parse_pgn(pgn_text: str) -> list[ParsedGame]:
    """Parse a PGN string into a list of ParsedGame objects."""
    games = []
    pgn_io = io.StringIO(pgn_text)

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        games.append(_parse_single_game(game, pgn_text))

    return games


def _parse_single_game(game: chess.pgn.Game, raw_pgn: str) -> ParsedGame:
    headers = game.headers
    date_played = _parse_date(headers.get("Date", ""))

    moves = []
    board = game.board()
    for ply, node in enumerate(game.mainline()):
        move = node.move
        fen_before = board.fen()
        san = board.san(move)
        uci = move.uci()
        board.push(move)
        fen_after = board.fen()

        moves.append(
            ParsedMove(
                move_number=(ply // 2) + 1,
                ply=ply,
                san=san,
                uci=uci,
                fen_before=fen_before,
                fen_after=fen_after,
            )
        )

    # Extract the PGN for this specific game
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    game_pgn = game.accept(exporter)

    return ParsedGame(
        pgn=game_pgn,
        white=headers.get("White", "Unknown"),
        black=headers.get("Black", "Unknown"),
        result=headers.get("Result", "*"),
        date_played=date_played,
        opening_eco=headers.get("ECO"),
        opening_name=headers.get("Opening"),
        moves=moves,
    )


def _parse_date(date_str: str) -> date | None:
    """Parse PGN date format (YYYY.MM.DD) into a date object."""
    if not date_str or date_str == "????.??.??":
        return None
    try:
        parts = date_str.replace(".", "-").split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None
