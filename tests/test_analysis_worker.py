"""End-to-end test: import PGN -> analyze -> moves have evals and classifications."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Game, Move
from backend.services.pgn_parser import parse_pgn
from backend.tasks.analysis_worker import _analyze_game_sync

SAMPLE_PGN = """[Event "Rated Blitz game"]
[Site "https://lichess.org/abcd1234"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]
[Date "2025.03.15"]
[ECO "B20"]
[Opening "Sicilian Defense"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 1-0"""


def _setup_db_with_game():
    """Parse a sample game, store it, and return db session + game_id + session factory."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    db = Session()

    parsed = parse_pgn(SAMPLE_PGN)
    pg = parsed[0]

    game = Game(
        pgn=pg.pgn, white=pg.white, black=pg.black, result=pg.result,
        date_played=pg.date_played, opening_eco=pg.opening_eco,
        opening_name=pg.opening_name, player_color="white",
        source="pgn_upload",
    )
    db.add(game)
    db.flush()

    for pm in pg.moves:
        move = Move(
            game_id=game.id, move_number=pm.move_number, ply=pm.ply,
            san=pm.san, uci=pm.uci, fen_before=pm.fen_before, fen_after=pm.fen_after,
        )
        db.add(move)

    db.commit()
    return db, game.id, Session


def test_e2e_analysis():
    """Full pipeline: import -> analyze -> verify moves have engine data."""
    db, game_id, Session = _setup_db_with_game()

    _analyze_game_sync(game_id, session_factory=Session)

    # Refresh session to see committed changes from the worker
    db.expire_all()

    game = db.query(Game).filter(Game.id == game_id).first()
    assert game.analysis_status == "analyzed"

    moves = db.query(Move).filter(Move.game_id == game_id).order_by(Move.ply).all()
    assert len(moves) == 10

    # Every move should have phase detection
    for move in moves:
        assert move.phase in ("opening", "middlegame", "endgame"), f"Move {move.ply} missing phase"

    # With Stockfish available, moves should have engine evals
    analyzed_moves = [m for m in moves if m.engine_eval_before is not None]
    assert len(analyzed_moves) > 0, "No moves received engine evaluations"

    # Moves with evals should have classifications
    for move in analyzed_moves:
        assert move.classification in ("best", "good", "inaccuracy", "mistake", "blunder"), (
            f"Move {move.ply} has eval but no classification"
        )
        assert move.eval_delta is not None
        assert move.best_move_uci is not None

    db.close()
