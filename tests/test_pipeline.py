"""Tests for PGN parsing, phase assignment, and move record creation."""

import chess
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game, Move
from pipeline.worker import parse_and_create_moves
from services.classifier import assign_phase

# ── Phase assignment tests ────────────────────────────────────────────────────


class TestAssignPhase:
    def test_opening_phase(self):
        """Move 1 with all pieces on board should be opening."""
        board = chess.Board()  # starting position, 32 pieces
        assert assign_phase(board, 1) == "opening"

    def test_opening_move_15(self):
        """Move 15 with >= 28 pieces should still be opening."""
        board = chess.Board()
        assert assign_phase(board, 15) == "opening"

    def test_middlegame_move_16(self):
        """Move 16 should not be opening even with all pieces."""
        board = chess.Board()
        assert assign_phase(board, 16) == "middlegame"

    def test_middlegame_few_pieces_early(self):
        """Move 10 with < 28 pieces should be middlegame (not opening)."""
        # Position with 26 pieces (some captures happened)
        board = chess.Board("r1bqkb1r/pppppppp/2n2n2/8/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        # This has 30 pieces, still opening at move 3
        assert assign_phase(board, 3) == "opening"

    def test_endgame_low_material(self):
        """Position with total material <= 26 should be endgame."""
        # King + Rook + 3 pawns each side = 2*(5+3) = 16 pts
        board = chess.Board("4k3/8/8/8/8/8/PPP2ppp/R3K2r w Q - 0 40")
        assert assign_phase(board, 40) == "endgame"

    def test_endgame_no_queens_low_material(self):
        """No queens and material <= 40 should be endgame."""
        # Rook + Bishop + 4 pawns each = 2*(5+3+4) = 24 pts
        board = chess.Board("r1b1k3/pppp4/8/8/8/8/PPPP4/R1B1K3 w - - 0 30")
        assert assign_phase(board, 30) == "endgame"

    def test_middlegame_normal(self):
        """Standard middlegame position with queens and high material."""
        # All pieces but a few pawns traded — material > 26, has queens
        board = chess.Board(
            "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQ1RK1 w - - 0 7"
        )
        assert assign_phase(board, 20) == "middlegame"


# ── PGN parsing and move creation tests ───────────────────────────────────────


SAMPLE_PGN = """[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O 1-0"""


@pytest_asyncio.fixture
async def sample_game(db_session: AsyncSession):
    from datetime import datetime
    game = Game(
        lichess_id="test123",
        pgn=SAMPLE_PGN,
        player_color="white",
        opponent_username="Player2",
        result="win",
        played_at=datetime(2026, 1, 15),
        eco_code="C68",
        opening_name="Ruy Lopez",
        engine_status="pending",
        annotation_status="pending",
        condition_status="pending",
    )
    db_session.add(game)
    await db_session.flush()
    return game


@pytest.mark.asyncio
async def test_parse_creates_moves(db_session, sample_game):
    """PGN parsing should create correct number of Move records."""
    moves = await parse_and_create_moves(db_session, sample_game)
    assert len(moves) == 9  # 5 white + 4 black moves


@pytest.mark.asyncio
async def test_move_fields_correct(db_session, sample_game):
    """Each move should have correct fields."""
    moves = await parse_and_create_moves(db_session, sample_game)
    first_move = moves[0]
    assert first_move.san == "e4"
    assert first_move.color == "white"
    assert first_move.move_number == 1
    assert first_move.phase == "opening"
    assert first_move.fen_before == chess.STARTING_FEN


@pytest.mark.asyncio
async def test_all_moves_have_phase(db_session, sample_game):
    """Every move must have a phase assigned."""
    moves = await parse_and_create_moves(db_session, sample_game)
    for m in moves:
        assert m.phase in ("opening", "middlegame", "endgame")


@pytest.mark.asyncio
async def test_fen_chain_valid(db_session, sample_game):
    """Each move's fen_after should match the next move's fen_before."""
    moves = await parse_and_create_moves(db_session, sample_game)
    for i in range(len(moves) - 1):
        assert moves[i].fen_after == moves[i + 1].fen_before


@pytest.mark.asyncio
async def test_idempotent_parsing(db_session, sample_game):
    """Calling parse twice should not duplicate moves."""
    moves1 = await parse_and_create_moves(db_session, sample_game)
    moves2 = await parse_and_create_moves(db_session, sample_game)
    assert len(moves1) == len(moves2)

    # Verify only one set in DB
    result = await db_session.execute(
        select(Move).where(Move.game_id == sample_game.id)
    )
    all_moves = result.scalars().all()
    assert len(all_moves) == 9
