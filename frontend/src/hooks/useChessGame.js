import { useCallback, useEffect, useMemo, useState } from "react";

/**
 * Hook for managing chessboard state and move navigation.
 */
export default function useChessGame(moves = []) {
  const [currentPly, setCurrentPly] = useState(0);

  // Reset ply to 0 when moves change (new game loaded)
  useEffect(() => {
    setCurrentPly(0);
  }, [moves]);

  const currentFen = useMemo(() => {
    const startFen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    if (!moves.length) return startFen;
    if (currentPly === 0) return moves[0]?.fen_before || startFen;
    return moves[currentPly - 1]?.fen_after || startFen;
  }, [moves, currentPly]);

  const currentMove = useMemo(() => {
    if (currentPly === 0 || !moves.length) return null;
    return moves[currentPly - 1];
  }, [moves, currentPly]);

  const goToStart = useCallback(() => setCurrentPly(0), []);
  const goToEnd = useCallback(() => setCurrentPly(moves.length), [moves.length]);
  const goForward = useCallback(
    () => setCurrentPly((p) => Math.min(p + 1, moves.length)),
    [moves.length]
  );
  const goBack = useCallback(
    () => setCurrentPly((p) => Math.max(p - 1, 0)),
    []
  );
  const goToPly = useCallback(
    (ply) => setCurrentPly(Math.max(0, Math.min(ply, moves.length))),
    [moves.length]
  );

  return {
    currentPly,
    currentFen,
    currentMove,
    totalMoves: moves.length,
    goToStart,
    goToEnd,
    goForward,
    goBack,
    goToPly,
  };
}
