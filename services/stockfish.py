"""Stockfish subprocess wrapper — position evaluation."""

import logging

import chess
import chess.engine

import config

logger = logging.getLogger(__name__)


class StockfishEngine:
    """Manages a persistent Stockfish process. One instance per analysis session."""

    def __init__(self):
        self._engine: chess.engine.SimpleEngine | None = None

    def start(self) -> None:
        """Launch subprocess, reuse across moves."""
        if self._engine is not None:
            return
        try:
            self._engine = chess.engine.SimpleEngine.popen_uci(config.STOCKFISH_PATH)
            logger.info("Stockfish started: %s", config.STOCKFISH_PATH)
        except FileNotFoundError:
            raise RuntimeError(
                f"Stockfish not found at '{config.STOCKFISH_PATH}'. "
                "Set STOCKFISH_PATH in .env"
            )

    def stop(self) -> None:
        """Shut down the engine process."""
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
            logger.info("Stockfish stopped")

    def evaluate(self, fen: str, depth: int | None = None) -> dict:
        """Evaluate a position.

        Returns: { cp_eval: float, best_move_san: str }
        cp_eval is from the perspective of the side to move.
        Mate scores map to ±10000.
        """
        if depth is None:
            depth = config.STOCKFISH_DEPTH

        if self._engine is None:
            self.start()

        board = chess.Board(fen)
        info = self._engine.analyse(board, chess.engine.Limit(depth=depth))

        score = info["score"].relative
        pv_moves = info.get("pv", [])

        if score.is_mate():
            mate_in = score.mate()
            cp_eval = 10000.0 if mate_in > 0 else -10000.0
        else:
            cp_eval = float(score.score())

        best_move_san = None
        if pv_moves:
            best_move_san = board.san(pv_moves[0])

        return {"cp_eval": cp_eval, "best_move_san": best_move_san}
