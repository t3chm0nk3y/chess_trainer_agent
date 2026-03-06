"""Direct Stockfish integration via python-chess engine interface."""

import logging
from dataclasses import dataclass, field

import chess
import chess.engine

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EngineEval:
    """Result from engine position analysis."""

    score_cp: float  # centipawns from white's perspective
    best_move: str | None = None  # UCI format
    mate_in: int | None = None  # moves to mate (positive = white mates)
    pv: list[str] = field(default_factory=list)  # principal variation


class StockfishEngine:
    """Manages a Stockfish process for position analysis."""

    def __init__(self):
        self._engine: chess.engine.SimpleEngine | None = None

    def _ensure_engine(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            try:
                self._engine = chess.engine.SimpleEngine.popen_uci(settings.STOCKFISH_PATH)
                logger.info("Stockfish engine started: %s", settings.STOCKFISH_PATH)
            except FileNotFoundError:
                raise RuntimeError(
                    f"Stockfish not found at '{settings.STOCKFISH_PATH}'. "
                    "Install Stockfish and set STOCKFISH_PATH in .env"
                )
        return self._engine

    def analyze_position(self, fen: str, depth: int | None = None) -> EngineEval:
        """Analyze a single position and return evaluation.

        Args:
            fen: FEN string of the position.
            depth: Search depth (defaults to settings.ENGINE_DEPTH).

        Returns:
            EngineEval with score in centipawns from white's perspective.
        """
        if depth is None:
            depth = settings.ENGINE_DEPTH

        engine = self._ensure_engine()
        board = chess.Board(fen)

        info = engine.analyse(board, chess.engine.Limit(depth=depth))

        score = info["score"].white()
        pv_moves = info.get("pv", [])

        mate_in = None
        if score.is_mate():
            mate_in = score.mate()
            score_cp = 10000.0 if mate_in > 0 else -10000.0
        else:
            score_cp = float(score.score())

        best_move = pv_moves[0].uci() if pv_moves else None
        pv_uci = [m.uci() for m in pv_moves[:5]]

        return EngineEval(
            score_cp=score_cp,
            best_move=best_move,
            mate_in=mate_in,
            pv=pv_uci,
        )

    def analyze_game_positions(
        self, fens: list[str], depth: int | None = None
    ) -> list[EngineEval]:
        """Analyze multiple positions (all moves in a game).

        Args:
            fens: List of FEN strings to analyze.
            depth: Search depth.

        Returns:
            List of EngineEval results, one per position.
        """
        results = []
        for fen in fens:
            try:
                results.append(self.analyze_position(fen, depth))
            except Exception as e:
                logger.error("Engine error on FEN %s: %s", fen, e)
                results.append(EngineEval(score_cp=0.0))
        return results

    def close(self):
        """Shut down the engine process."""
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
            logger.info("Stockfish engine stopped")


# Singleton instance
stockfish = StockfishEngine()
