import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def _store_parsed_games(db: Session, parsed_games, source: str, username: str = "") -> dict:
    """Store parsed games in the database, deduplicating by source_id.

    Returns dict with imported/skipped counts.
    """
    from backend.models import Game, Move

    imported = 0
    skipped = 0

    for pg in parsed_games:
        # Build a source_id for deduplication
        source_id = None
        if source == "lichess" and pg.pgn:
            # Try to extract the Lichess game URL from the PGN Site header
            for line in pg.pgn.split("\n"):
                if line.startswith("[Site ") and "lichess.org" in line:
                    source_id = line.split('"')[1].split("/")[-1] if '"' in line else None
                    break
        if source == "chesscom" and pg.pgn:
            for line in pg.pgn.split("\n"):
                if line.startswith("[Link ") or line.startswith("[Site "):
                    source_id = line.split('"')[1] if '"' in line else None
                    break

        # Deduplicate
        if source_id:
            existing = db.query(Game).filter(
                Game.source == source, Game.source_id == source_id
            ).first()
            if existing:
                skipped += 1
                continue

        # Determine player color
        player_color = "white"
        if username:
            if pg.black.lower() == username.lower():
                player_color = "black"

        game = Game(
            pgn=pg.pgn,
            white=pg.white,
            black=pg.black,
            result=pg.result,
            date_played=pg.date_played,
            opening_eco=pg.opening_eco,
            opening_name=pg.opening_name,
            player_color=player_color,
            source=source,
            source_id=source_id,
        )
        db.add(game)
        db.flush()  # Get the game.id

        for pm in pg.moves:
            move = Move(
                game_id=game.id,
                move_number=pm.move_number,
                ply=pm.ply,
                san=pm.san,
                uci=pm.uci,
                fen_before=pm.fen_before,
                fen_after=pm.fen_after,
            )
            db.add(move)

        imported += 1

    db.commit()
    return {"imported": imported, "skipped": skipped}


@router.post("/upload")
async def upload_pgn(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload PGN file(s) and start analysis."""
    from backend.services.pgn_parser import parse_pgn

    content = await file.read()
    pgn_text = content.decode("utf-8", errors="replace")

    try:
        parsed = parse_pgn(pgn_text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PGN: {e}")

    if not parsed:
        raise HTTPException(status_code=400, detail="No games found in PGN file")

    result = _store_parsed_games(db, parsed, source="pgn_upload")
    return {"status": "ok", **result}


@router.post("/import/lichess")
async def import_lichess(
    username: str,
    since: str | None = None,
    max_games: int | None = None,
    color: str | None = None,
    rated: str | None = None,
    time_control: str | None = None,
    db: Session = Depends(get_db),
):
    """Import games from Lichess API. Imports all games by default."""
    from backend.services.lichess_api import fetch_games
    from backend.services.pgn_parser import parse_pgn

    # Convert rated string to bool
    rated_bool = None
    if rated == "true":
        rated_bool = True
    elif rated == "false":
        rated_bool = False

    try:
        pgn_text = await fetch_games(
            username=username,
            since=since,
            max_games=max_games,
            color=color,
            rated=rated_bool,
            time_control=time_control,
        )
    except Exception as e:
        logger.error("Lichess API error: %s", e)
        raise HTTPException(status_code=502, detail=f"Lichess API error: {e}")

    if not pgn_text.strip():
        return {"status": "ok", "imported": 0, "skipped": 0, "message": "No games found"}

    try:
        parsed = parse_pgn(pgn_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Lichess PGN: {e}")

    result = _store_parsed_games(db, parsed, source="lichess", username=username)
    return {"status": "ok", **result}


@router.post("/import/chesscom")
async def import_chesscom(
    username: str,
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
):
    """Import games from Chess.com API."""
    # TODO: implement Chess.com API fetch (similar to lichess_api.py)
    raise HTTPException(status_code=501, detail="Chess.com import not yet implemented")


@router.get("")
async def list_games(
    source: str | None = None,
    opening: str | None = None,
    color: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List all games with optional filters."""
    from backend.models import Game

    query = db.query(Game)
    if source:
        query = query.filter(Game.source == source)
    if opening:
        query = query.filter(Game.opening_eco == opening)
    if color:
        query = query.filter(Game.player_color == color)
    games = query.order_by(Game.date_played.desc()).offset(offset).limit(limit).all()
    return {"games": [_game_to_dict(g) for g in games], "total": query.count()}


@router.get("/{game_id}")
async def get_game(game_id: str, db: Session = Depends(get_db)):
    """Get a single game with all moves and annotations."""
    from backend.models import Game

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Game not found")
    return _game_to_dict(game, include_moves=True)


@router.get("/{game_id}/moves")
async def get_game_moves(game_id: str, db: Session = Depends(get_db)):
    """Get move list with evals, classifications, and themes."""
    from backend.models import Move

    moves = db.query(Move).filter(Move.game_id == game_id).order_by(Move.ply).all()
    return {"moves": [_move_to_dict(m) for m in moves]}


@router.delete("/{game_id}")
async def delete_game(game_id: str, db: Session = Depends(get_db)):
    """Remove a game."""
    from backend.models import Game

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Game not found")
    db.delete(game)
    db.commit()
    return {"status": "deleted"}


def _game_to_dict(game, include_moves: bool = False) -> dict:
    d = {
        "id": game.id,
        "white": game.white,
        "black": game.black,
        "result": game.result,
        "date_played": str(game.date_played) if game.date_played else None,
        "opening_eco": game.opening_eco,
        "opening_name": game.opening_name,
        "player_color": game.player_color,
        "source": game.source,
        "source_id": game.source_id,
        "imported_at": game.imported_at.isoformat() if game.imported_at else None,
        "analysis_status": game.analysis_status,
    }
    if include_moves:
        d["moves"] = [_move_to_dict(m) for m in game.moves]
    return d


def _move_to_dict(move) -> dict:
    return {
        "id": move.id,
        "move_number": move.move_number,
        "ply": move.ply,
        "san": move.san,
        "uci": move.uci,
        "fen_before": move.fen_before,
        "fen_after": move.fen_after,
        "engine_eval_before": move.engine_eval_before,
        "engine_eval_after": move.engine_eval_after,
        "eval_delta": move.eval_delta,
        "classification": move.classification,
        "phase": move.phase,
        "themes_json": move.themes_json,
    }
