"""Phase assignment, severity thresholds, condition detection."""

import chess

import config


def assign_phase(board: chess.Board, move_number: int) -> str:
    """Returns: "opening" | "middlegame" | "endgame"

    Per SRS Section 8.6:
    - Opening: move_number <= 15 AND total pieces >= 28
    - Endgame: material <= 26 OR (no queens AND material <= 40)
    - Middlegame: everything else
    """
    piece_map = board.piece_map()
    total_pieces = len(piece_map)

    if move_number <= 15 and total_pieces >= 28:
        return "opening"

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


def assign_severity(cp_loss: float) -> str | None:
    """Returns: "inaccuracy" | "mistake" | "blunder" | None"""
    if cp_loss >= config.CP_LOSS_BLUNDER:
        return "blunder"
    if cp_loss >= config.CP_LOSS_MISTAKE:
        return "mistake"
    if cp_loss >= config.CP_LOSS_INACCURACY:
        return "inaccuracy"
    return None


# ── Game Condition Detection ──────────────────────────────────────────────────

OUTPOST_SQUARES = {chess.C5, chess.D4, chess.D5, chess.E4, chess.E5, chess.F5}


def _board_from_fen(fen: str) -> chess.Board:
    return chess.Board(fen)


def _piece_types_on_board(board: chess.Board) -> set[int]:
    """Return set of piece types (excluding kings) present on the board."""
    return {p.piece_type for p in board.piece_map().values() if p.piece_type != chess.KING}


def _count_pawns(board: chess.Board, color: chess.Color) -> int:
    return len(board.pieces(chess.PAWN, color))


def _player_color(player_color_str: str) -> chess.Color:
    return chess.WHITE if player_color_str == "white" else chess.BLACK


def detect_game_conditions(
    moves: list,
    active_gc_patterns: list[dict],
    player_color: str,
    game_result: str,
) -> list[dict]:
    """Detect game conditions from stored Move data. No Stockfish calls.

    Args:
        moves: List of Move ORM objects (must have fen_before, fen_after, phase,
               cp_loss, cp_eval_before, move_number, color, san).
        active_gc_patterns: List of GC pattern dicts from registry.
        player_color: "white" or "black"
        game_result: "win" | "loss" | "draw"

    Returns:
        List of detected conditions:
        [{ registry_pattern_id, condition_name, detected_at_move,
           player_was_worse, context_note }]
    """
    active_ids = {p["id"] for p in active_gc_patterns}
    results = []
    color = _player_color(player_color)
    opponent_color = not color

    # Build boards at each move for condition checking
    if not moves:
        return results

    # Precompute useful data
    endgame_start_idx = None
    middlegame_start_idx = None
    for i, m in enumerate(moves):
        if m.phase == "endgame" and endgame_start_idx is None:
            endgame_start_idx = i
        if m.phase == "middlegame" and middlegame_start_idx is None:
            middlegame_start_idx = i

    # GC-001: Rook vs Pawn Ending
    if "GC-001" in active_ids and endgame_start_idx is not None:
        board = _board_from_fen(moves[endgame_start_idx].fen_before)
        piece_types = _piece_types_on_board(board)
        if piece_types <= {chess.ROOK, chess.PAWN}:
            player_worse = _is_player_worse(moves[endgame_start_idx], color)
            results.append({
                "registry_pattern_id": "GC-001",
                "condition_name": "Rook vs Pawn Ending",
                "detected_at_move": moves[endgame_start_idx].move_number,
                "player_was_worse": player_worse,
                "context_note": None,
            })

    # GC-002: Opposite-Color Bishop Ending
    if "GC-002" in active_ids and endgame_start_idx is not None:
        board = _board_from_fen(moves[endgame_start_idx].fen_before)
        piece_types = _piece_types_on_board(board)
        if piece_types <= {chess.BISHOP, chess.PAWN}:
            white_bishops = board.pieces(chess.BISHOP, chess.WHITE)
            black_bishops = board.pieces(chess.BISHOP, chess.BLACK)
            if len(white_bishops) == 1 and len(black_bishops) == 1:
                wb_sq = list(white_bishops)[0]
                bb_sq = list(black_bishops)[0]
                if chess.square_color(wb_sq) != chess.square_color(bb_sq):
                    results.append({
                        "registry_pattern_id": "GC-002",
                        "condition_name": "Opposite-Color Bishop Ending",
                        "detected_at_move": moves[endgame_start_idx].move_number,
                        "player_was_worse": _is_player_worse(moves[endgame_start_idx], color),
                        "context_note": None,
                    })

    # GC-003: Knight Outpost Allowed
    if "GC-003" in active_ids:
        consecutive = 0
        outpost_detected = False
        for m in moves:
            if m.phase != "middlegame":
                consecutive = 0
                continue
            board = _board_from_fen(m.fen_after)
            opp_knights = board.pieces(chess.KNIGHT, opponent_color)
            has_outpost = any(sq in OUTPOST_SQUARES for sq in opp_knights)
            if has_outpost:
                consecutive += 1
                if consecutive >= 5 and not outpost_detected:
                    outpost_detected = True
                    results.append({
                        "registry_pattern_id": "GC-003",
                        "condition_name": "Knight Outpost Allowed",
                        "detected_at_move": m.move_number,
                        "player_was_worse": _is_player_worse(m, color),
                        "context_note": f"Opponent knight on outpost for {consecutive}+ moves",
                    })
            else:
                consecutive = 0

    # GC-004: Isolated Queen Pawn
    if "GC-004" in active_ids and middlegame_start_idx is not None:
        board = _board_from_fen(moves[middlegame_start_idx].fen_before)
        player_pawns = board.pieces(chess.PAWN, color)
        has_d_pawn = any(chess.square_file(sq) == 3 for sq in player_pawns)  # d-file = 3
        has_c_pawn = any(chess.square_file(sq) == 2 for sq in player_pawns)
        has_e_pawn = any(chess.square_file(sq) == 4 for sq in player_pawns)
        if has_d_pawn and not has_c_pawn and not has_e_pawn:
            results.append({
                "registry_pattern_id": "GC-004",
                "condition_name": "Isolated Queen Pawn",
                "detected_at_move": moves[middlegame_start_idx].move_number,
                "player_was_worse": _is_player_worse(moves[middlegame_start_idx], color),
                "context_note": None,
            })

    # GC-005: Down Material Entering Endgame
    if "GC-005" in active_ids and endgame_start_idx is not None:
        m = moves[endgame_start_idx]
        if m.cp_eval_before is not None:
            # cp_eval_before is from side-to-move perspective
            # Convert to player perspective
            player_eval = m.cp_eval_before if m.color == player_color else -m.cp_eval_before
            if player_eval <= -150:
                results.append({
                    "registry_pattern_id": "GC-005",
                    "condition_name": "Down Material Entering Endgame",
                    "detected_at_move": m.move_number,
                    "player_was_worse": True,
                    "context_note": f"Player eval: {player_eval:.0f}cp at endgame start",
                })

    # GC-006: Worse After Opening
    if "GC-006" in active_ids:
        opening_cp_loss = sum(
            m.cp_loss for m in moves
            if m.phase == "opening" and m.color == player_color and m.cp_loss is not None
        )
        if opening_cp_loss >= 100:
            results.append({
                "registry_pattern_id": "GC-006",
                "condition_name": "Worse After Opening",
                "detected_at_move": None,
                "player_was_worse": True,
                "context_note": f"Total opening cp_loss: {opening_cp_loss:.0f}",
            })

    # GC-007: Exchange Sacrifice Received — skip for now (complex material tracking)

    # GC-008: King Safety Deficit
    if "GC-008" in active_ids:
        player_castled = False
        opponent_castled = False
        for m in moves:
            if m.move_number > 15:
                break
            san = m.san
            if "O-O" in san or "O-O-O" in san:
                if m.color == player_color:
                    player_castled = True
                else:
                    opponent_castled = True
        if not player_castled and opponent_castled:
            results.append({
                "registry_pattern_id": "GC-008",
                "condition_name": "King Safety Deficit",
                "detected_at_move": 15,
                "player_was_worse": False,
                "context_note": "Player uncastled at move 15, opponent castled",
            })

    # GC-009: Pawn Minority in Endgame
    if "GC-009" in active_ids and endgame_start_idx is not None:
        board = _board_from_fen(moves[endgame_start_idx].fen_before)
        player_pawns = _count_pawns(board, color)
        opp_pawns = _count_pawns(board, opponent_color)
        if player_pawns < opp_pawns:
            results.append({
                "registry_pattern_id": "GC-009",
                "condition_name": "Pawn Minority in Endgame",
                "detected_at_move": moves[endgame_start_idx].move_number,
                "player_was_worse": _is_player_worse(moves[endgame_start_idx], color),
                "context_note": f"Player {player_pawns} pawns vs opponent {opp_pawns}",
            })

    # GC-010: Perpetual King Attack
    if "GC-010" in active_ids and len(moves) >= 10:
        last_10 = moves[-10:]
        checks = 0
        for m in last_10:
            if m.color != player_color:  # opponent's moves
                board = _board_from_fen(m.fen_after)
                if board.is_check():
                    checks += 1
        if checks >= 3:
            results.append({
                "registry_pattern_id": "GC-010",
                "condition_name": "Perpetual King Attack",
                "detected_at_move": last_10[0].move_number,
                "player_was_worse": True,
                "context_note": f"Player's king checked {checks} times in last 10 moves",
            })

    return results


def _is_player_worse(move, color: chess.Color) -> bool:
    """Check if player was worse at this point based on cp_eval."""
    if move.cp_eval_before is None:
        return False
    # cp_eval_before is relative to side-to-move
    player_color_str = "white" if color == chess.WHITE else "black"
    if move.color == player_color_str:
        return move.cp_eval_before < -100
    else:
        return move.cp_eval_before > 100
