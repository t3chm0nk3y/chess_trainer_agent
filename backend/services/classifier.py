"""Move classification based on engine eval deltas."""

# Classification thresholds in centipawns
THRESHOLDS = {
    "best": 10,
    "good": 30,
    "inaccuracy": 70,
    "mistake": 150,
}


def classify_move(eval_delta: float | None) -> str | None:
    """Classify a move based on the absolute eval delta (centipawns).

    Args:
        eval_delta: Difference in evaluation caused by this move (always positive for losses).

    Returns:
        Classification string or None if eval_delta is not available.
    """
    if eval_delta is None:
        return None

    delta = abs(eval_delta)

    if delta <= THRESHOLDS["best"]:
        return "best"
    elif delta <= THRESHOLDS["good"]:
        return "good"
    elif delta <= THRESHOLDS["inaccuracy"]:
        return "inaccuracy"
    elif delta <= THRESHOLDS["mistake"]:
        return "mistake"
    else:
        return "blunder"


def detect_phase(fen: str) -> str:
    """Detect game phase from a FEN string using piece count heuristics.

    Args:
        fen: FEN string of the position.

    Returns:
        "opening", "middlegame", or "endgame"
    """
    piece_part = fen.split()[0]
    move_number = int(fen.split()[-1]) if fen.split()[-1].isdigit() else 1

    # Count non-pawn, non-king pieces
    minor_major = sum(1 for c in piece_part if c in "rnbqRNBQ")

    if move_number <= 15 and minor_major >= 10:
        return "opening"
    elif minor_major <= 6:
        return "endgame"
    else:
        return "middlegame"
