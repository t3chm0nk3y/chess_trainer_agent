"""Lichess API client — game import with deduplication."""

import io
import json
import logging
from datetime import datetime

import chess
import chess.pgn
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from models import Game, Move

logger = logging.getLogger(__name__)

LICHESS_API = "https://lichess.org/api"


def _parse_result(result_str: str, player_color: str) -> str:
    """Convert PGN result to win/loss/draw from player perspective."""
    if result_str == "1-0":
        return "win" if player_color == "white" else "loss"
    elif result_str == "0-1":
        return "loss" if player_color == "white" else "win"
    return "draw"


def _assign_phase(board: "chess.Board", move_number: int) -> str:
    """Assign phase per SRS Section 8.6.

    Opening: move_number <= 15 AND total pieces on board >= 28
    Endgame: total material <= 26 pts (Q=9, R=5, B=3, N=3, P=1, kings excluded)
             OR (no queens AND total material <= 40)
    Middlegame: everything else
    """
    piece_map = board.piece_map()
    total_pieces = len(piece_map)

    if move_number <= 15 and total_pieces >= 28:
        return "opening"

    # Count material (excluding kings)
    material_values = {
        chess.QUEEN: 9, chess.ROOK: 5, chess.BISHOP: 3, chess.KNIGHT: 3, chess.PAWN: 1,
    }
    total_material = 0
    has_queens = False
    for piece in piece_map.values():
        if piece.piece_type == chess.KING:
            continue
        if piece.piece_type == chess.QUEEN:
            has_queens = True
        total_material += material_values.get(piece.piece_type, 0)

    if total_material <= 26:
        return "endgame"
    if not has_queens and total_material <= 40:
        return "endgame"

    return "middlegame"


async def import_games(db: AsyncSession, max_games: int | None = None) -> dict:
    """Import rated games from Lichess with deduplication.

    Args:
        db: Database session.
        max_games: Max number of games to fetch from Lichess.
                   None means all games.

    Returns: { imported: int, skipped: int, errors: int, total_fetched: int }
    """
    username = config.LICHESS_USERNAME
    if not username:
        raise ValueError("LICHESS_USERNAME not configured")

    headers = {
        "Accept": "application/x-ndjson",
        "Authorization": f"Bearer {config.LICHESS_TOKEN}",
    }
    params: dict[str, str] = {
        "rated": "true",
        "moves": "true",
        "opening": "true",
        "sort": "dateDesc",
    }
    if max_games is not None:
        params["max"] = str(max_games)

    url = f"{LICHESS_API}/games/user/{username}"
    label = f"last {max_games}" if max_games else "all"
    logger.info("Importing %s games from Lichess for user: %s", label, username)

    imported = 0
    skipped = 0
    errors = 0

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            async with client.stream("GET", url, params=params, headers=headers) as resp:
                if resp.status_code == 401:
                    raise ValueError("Invalid Lichess token")
                if resp.status_code == 429:
                    logger.warning("Lichess rate limit hit, try again later")
                    return {"imported": 0, "skipped": 0, "errors": 1}
                resp.raise_for_status()

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        game_data = json.loads(line)
                        result = await _import_single_game(db, game_data, username)
                        if result == "imported":
                            imported += 1
                        elif result == "skipped":
                            skipped += 1
                    except Exception as e:
                        errors += 1
                        logger.error("Error importing game: %s", e)

        except httpx.HTTPStatusError as e:
            logger.error("Lichess API error: %s", e)
            errors += 1

    await db.commit()
    total_fetched = imported + skipped + errors
    logger.info(
        "Import complete: %d imported, %d skipped, %d errors (fetched %d)",
        imported, skipped, errors, total_fetched,
    )
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "total_fetched": total_fetched,
    }


async def _import_single_game(
    db: AsyncSession, game_data: dict, username: str
) -> str:
    """Import a single game from Lichess NDJSON. Returns 'imported' or 'skipped'."""
    lichess_id = game_data["id"]

    # Deduplication check
    existing = await db.execute(select(Game).where(Game.lichess_id == lichess_id))
    if existing.scalar_one_or_none() is not None:
        return "skipped"

    # Determine player color
    players = game_data.get("players", {})
    if players.get("white", {}).get("user", {}).get("name", "").lower() == username.lower():
        player_color = "white"
        opponent = players.get("black", {}).get("user", {}).get("name")
    else:
        player_color = "black"
        opponent = players.get("white", {}).get("user", {}).get("name")

    # Parse result
    winner = game_data.get("winner")
    if winner == "white":
        pgn_result = "1-0"
    elif winner == "black":
        pgn_result = "0-1"
    else:
        pgn_result = "1/2-1/2"
    result = _parse_result(pgn_result, player_color)

    # Parse timestamp
    created_at = game_data.get("createdAt", 0)
    played_at = datetime.utcfromtimestamp(created_at / 1000)

    # Opening info
    opening = game_data.get("opening", {})
    eco_code = opening.get("eco")
    opening_name = opening.get("name")
    # Split variation from opening name if present
    variation_name = None
    if opening_name and ":" in opening_name:
        parts = opening_name.split(":", 1)
        opening_name = parts[0].strip()
        variation_name = parts[1].strip()

    # Time control
    clock = game_data.get("clock", {})
    time_control = None
    if clock:
        initial = clock.get("initial", 0)
        increment = clock.get("increment", 0)
        time_control = f"{initial}+{increment}"

    # Build PGN from moves string
    moves_str = game_data.get("moves", "")
    pgn_text = _build_pgn(game_data, moves_str)

    # Parse moves via python-chess
    pgn_io = io.StringIO(pgn_text)
    chess_game = chess.pgn.read_game(pgn_io)
    if chess_game is None:
        raise ValueError(f"Failed to parse PGN for game {lichess_id}")

    # Count total moves
    move_list = list(chess_game.mainline_moves())
    total_moves = len(move_list)

    # Create Game record
    game = Game(
        lichess_id=lichess_id,
        pgn=pgn_text,
        player_color=player_color,
        opponent_username=opponent,
        result=result,
        played_at=played_at,
        eco_code=eco_code,
        opening_name=opening_name,
        variation_name=variation_name,
        time_control=time_control,
        total_moves=total_moves,
        engine_status="pending",
        annotation_status="pending",
        condition_status="pending",
    )
    db.add(game)
    await db.flush()  # get game.id

    # Create Move records with phase assignment
    board = chess_game.board()
    for ply, node in enumerate(chess_game.mainline()):
        move = node.move
        fen_before = board.fen()
        san = board.san(move)
        move_number = (ply // 2) + 1
        color = "white" if ply % 2 == 0 else "black"
        phase = _assign_phase(board, move_number)
        board.push(move)
        fen_after = board.fen()

        move_record = Move(
            game_id=game.id,
            move_number=move_number,
            color=color,
            san=san,
            fen_before=fen_before,
            fen_after=fen_after,
            phase=phase,
        )
        db.add(move_record)

    return "imported"


def _build_pgn(game_data: dict, moves_str: str) -> str:
    """Build a PGN string from Lichess game data and moves."""
    headers = []
    players = game_data.get("players", {})
    white_user = players.get("white", {}).get("user", {}).get("name", "?")
    black_user = players.get("black", {}).get("user", {}).get("name", "?")

    winner = game_data.get("winner")
    if winner == "white":
        result = "1-0"
    elif winner == "black":
        result = "0-1"
    else:
        result = "1/2-1/2"

    headers.append(f'[White "{white_user}"]')
    headers.append(f'[Black "{black_user}"]')
    headers.append(f'[Result "{result}"]')

    opening = game_data.get("opening", {})
    if opening.get("eco"):
        headers.append(f'[ECO "{opening["eco"]}"]')
    if opening.get("name"):
        headers.append(f'[Opening "{opening["name"]}"]')

    created_at = game_data.get("createdAt", 0)
    dt = datetime.utcfromtimestamp(created_at / 1000)
    headers.append(f'[Date "{dt.strftime("%Y.%m.%d")}"]')

    pgn = "\n".join(headers) + "\n\n"

    # Format moves with move numbers
    move_tokens = moves_str.split()
    formatted = []
    for i, token in enumerate(move_tokens):
        if i % 2 == 0:
            formatted.append(f"{i // 2 + 1}. {token}")
        else:
            formatted.append(token)

    pgn += " ".join(formatted) + f" {result}"
    return pgn

