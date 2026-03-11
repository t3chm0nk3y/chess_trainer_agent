"""Tests for phase assignment logic."""

import chess

from services.classifier import assign_phase


class TestPhaseAssignment:
    """Test phase assignment per SRS Section 8.6."""

    def test_starting_position_is_opening(self):
        board = chess.Board()
        assert assign_phase(board, 1) == "opening"

    def test_move_15_with_all_pieces_is_opening(self):
        board = chess.Board()
        assert assign_phase(board, 15) == "opening"

    def test_move_16_is_not_opening(self):
        """Move 16 exceeds the opening threshold."""
        board = chess.Board()
        assert assign_phase(board, 16) != "opening"

    def test_king_rook_pawn_endgame(self):
        """K+R+3P vs K+R+3P = 2*(5+3) = 16 pts -> endgame."""
        board = chess.Board("4k2r/ppp5/8/8/8/8/PPP5/4K2R w K - 0 40")
        assert assign_phase(board, 40) == "endgame"

    def test_queen_endgame_high_material(self):
        """Queens present with material > 26 is not endgame."""
        # Q+R+4P each = 2*(9+5+4) = 36 pts, queens present -> middlegame
        board = chess.Board("r2qk3/pppp4/8/8/8/8/PPPP4/R2QK3 w - - 0 30")
        assert assign_phase(board, 30) == "middlegame"

    def test_no_queens_moderate_material(self):
        """No queens, material <= 40 -> endgame."""
        # R+B+N+5P each = 2*(5+3+3+5) = 32 pts, no queens -> endgame
        board = chess.Board("rnb1k3/ppppp3/8/8/8/8/PPPPP3/RNB1K3 w - - 0 25")
        assert assign_phase(board, 25) == "endgame"

    def test_few_pieces_middlegame(self):
        """< 28 pieces but high material with queens -> middlegame."""
        # Q+R+B+N+5P each = 2*(9+5+3+3+5) = 50 pts with queens -> middlegame
        board = chess.Board(
            "rnbqk3/ppppp3/8/8/8/8/PPPPP3/RNBQK3 w - - 0 20"
        )
        assert assign_phase(board, 20) == "middlegame"
