"""Opening line analysis: win/loss stats, divergence detection."""

import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import Game, Move, OpeningStats

logger = logging.getLogger(__name__)


def _player_result(game: Game) -> str:
    """Determine if the player won, lost, or drew."""
    if game.result == "1/2-1/2":
        return "draw"
    player_won = (
        (game.player_color == "white" and game.result == "1-0")
        or (game.player_color == "black" and game.result == "0-1")
    )
    return "win" if player_won else "loss"


def _extract_opening_key(game: Game) -> tuple[str, str, str | None]:
    """Extract (eco_code, opening_name, variation_name) from a game.

    Splits opening names like 'Sicilian Defense: Najdorf Variation'
    into base name and variation.
    """
    eco = game.opening_eco or "???"
    full_name = game.opening_name or "Unknown"

    if ":" in full_name:
        parts = full_name.split(":", 1)
        return (eco, parts[0].strip(), parts[1].strip())
    return (eco, full_name, None)


def _get_opening_moves(db: Session, game_id: str) -> list[str]:
    """Get the SAN moves from the opening phase of a game."""
    moves = (
        db.query(Move)
        .filter(Move.game_id == game_id, Move.phase == "opening")
        .order_by(Move.ply)
        .all()
    )
    return [m.san for m in moves]


def _compute_opening_cp_loss(
    db: Session, game_id: str, player_color: str
) -> float | None:
    """Compute average centipawn loss during opening for the player's moves."""
    moves = (
        db.query(Move)
        .filter(
            Move.game_id == game_id,
            Move.phase == "opening",
            Move.eval_delta.isnot(None),
        )
        .order_by(Move.ply)
        .all()
    )

    # Filter to only the player's moves
    player_moves = [
        m for m in moves
        if (m.ply % 2 == 0) == (player_color == "white")
    ]

    if not player_moves:
        return None
    return sum(m.eval_delta for m in player_moves) / len(player_moves)


def compute_opening_stats(db: Session) -> list[OpeningStats]:
    """Aggregate win/loss/draw stats per opening from all analyzed games.

    Returns the list of OpeningStats objects that were created/updated.
    """
    games = (
        db.query(Game)
        .filter(Game.analysis_status == "analyzed")
        .all()
    )

    if not games:
        return []

    # Group games by opening key
    grouped: dict[tuple, list[Game]] = defaultdict(list)
    for game in games:
        key = _extract_opening_key(game)
        grouped[key].append(game)

    # Clear existing stats and rebuild
    db.query(OpeningStats).delete()

    results = []
    for (eco, name, variation), group_games in grouped.items():
        wins = sum(1 for g in group_games if _player_result(g) == "win")
        losses = sum(
            1 for g in group_games if _player_result(g) == "loss"
        )
        draws = sum(
            1 for g in group_games if _player_result(g) == "draw"
        )

        # Compute average CP loss across all games in this opening
        cp_losses = []
        move_sequences = []
        for g in group_games:
            cp = _compute_opening_cp_loss(db, g.id, g.player_color)
            if cp is not None:
                cp_losses.append(cp)
            seq = _get_opening_moves(db, g.id)
            if seq:
                move_sequences.append(seq)

        avg_cp = (
            round(sum(cp_losses) / len(cp_losses), 1)
            if cp_losses else None
        )

        # Find divergence move
        div_move = _find_divergence_move(
            db, group_games, move_sequences
        )

        # Use the longest common prefix as the representative sequence
        representative_seq = _longest_common_prefix(move_sequences)

        stats = OpeningStats(
            eco_code=eco,
            opening_name=name,
            variation_name=variation,
            move_sequence=(
                json.dumps(representative_seq) if representative_seq
                else None
            ),
            total_games=len(group_games),
            wins=wins,
            losses=losses,
            draws=draws,
            avg_cp_loss=avg_cp,
            divergence_move=div_move,
            last_updated=datetime.utcnow(),
        )
        db.add(stats)
        results.append(stats)

    db.commit()
    for s in results:
        db.refresh(s)

    logger.info(
        "Computed opening stats for %d opening lines", len(results)
    )
    return results


def _longest_common_prefix(sequences: list[list[str]]) -> list[str]:
    """Find the longest common prefix of move sequences."""
    if not sequences:
        return []
    prefix = list(sequences[0])
    for seq in sequences[1:]:
        i = 0
        while i < len(prefix) and i < len(seq) and prefix[i] == seq[i]:
            i += 1
        prefix = prefix[:i]
    return prefix


def _find_divergence_move(
    db: Session,
    games: list[Game],
    move_sequences: list[list[str]],
) -> int | None:
    """Find the move where losses diverge from wins.

    Compares the move sequences of won games vs lost games.
    The divergence move is the earliest ply where the lost games
    tend to play a different move than the won games.
    """
    if len(games) < 2:
        return None

    won_seqs = []
    lost_seqs = []
    for game, seq in zip(games, move_sequences):
        if not seq:
            continue
        result = _player_result(game)
        if result == "win":
            won_seqs.append(seq)
        elif result == "loss":
            lost_seqs.append(seq)

    if not won_seqs or not lost_seqs:
        return None

    # Find earliest ply where lost games diverge from won games
    max_ply = min(
        max((len(s) for s in won_seqs), default=0),
        max((len(s) for s in lost_seqs), default=0),
    )

    for ply in range(max_ply):
        won_moves = {s[ply] for s in won_seqs if ply < len(s)}
        lost_moves = {s[ply] for s in lost_seqs if ply < len(s)}

        # If the lost games play moves the won games never play
        divergent = lost_moves - won_moves
        if divergent:
            # Return as move number (1-indexed)
            return (ply // 2) + 1

    return None


def get_opening_stats_ranked(
    db: Session, sort_by: str = "loss_pct"
) -> list[dict]:
    """Get opening stats ranked by loss percentage (or other metric).

    Returns list of dicts ready for API response.
    """
    stats = db.query(OpeningStats).all()

    result = []
    for s in stats:
        loss_pct = (
            round(s.losses / s.total_games * 100, 1)
            if s.total_games > 0 else 0.0
        )
        win_pct = (
            round(s.wins / s.total_games * 100, 1)
            if s.total_games > 0 else 0.0
        )
        draw_pct = (
            round(s.draws / s.total_games * 100, 1)
            if s.total_games > 0 else 0.0
        )

        result.append({
            "id": s.id,
            "eco_code": s.eco_code,
            "opening_name": s.opening_name,
            "variation_name": s.variation_name,
            "move_sequence": (
                json.loads(s.move_sequence) if s.move_sequence
                else []
            ),
            "total_games": s.total_games,
            "wins": s.wins,
            "losses": s.losses,
            "draws": s.draws,
            "win_pct": win_pct,
            "loss_pct": loss_pct,
            "draw_pct": draw_pct,
            "avg_cp_loss": s.avg_cp_loss,
            "divergence_move": s.divergence_move,
            "last_updated": s.last_updated.isoformat(),
        })

    if sort_by == "loss_pct":
        result.sort(key=lambda x: x["loss_pct"], reverse=True)
    elif sort_by == "total_games":
        result.sort(key=lambda x: x["total_games"], reverse=True)
    elif sort_by == "avg_cp_loss":
        result.sort(
            key=lambda x: x["avg_cp_loss"] or 0, reverse=True
        )

    return result


def get_opening_detail(
    db: Session, eco_code: str
) -> dict | None:
    """Get detailed opening info including game list and divergence.

    Returns all opening lines matching the eco_code with their games.
    """
    stats_list = (
        db.query(OpeningStats)
        .filter(OpeningStats.eco_code == eco_code)
        .all()
    )

    if not stats_list:
        return None

    lines = []
    for s in stats_list:
        # Find all games in this opening line
        query = db.query(Game).filter(
            Game.analysis_status == "analyzed",
            Game.opening_eco == eco_code,
        )
        if s.variation_name:
            full_name = f"{s.opening_name}: {s.variation_name}"
            query = query.filter(Game.opening_name == full_name)
        else:
            query = query.filter(Game.opening_name == s.opening_name)

        game_list = query.order_by(Game.date_played.desc()).all()

        game_summaries = []
        for g in game_list:
            game_summaries.append({
                "id": g.id,
                "white": g.white,
                "black": g.black,
                "result": g.result,
                "player_color": g.player_color,
                "player_result": _player_result(g),
                "date_played": (
                    str(g.date_played) if g.date_played else None
                ),
            })

        loss_pct = (
            round(s.losses / s.total_games * 100, 1)
            if s.total_games > 0 else 0.0
        )

        lines.append({
            "eco_code": s.eco_code,
            "opening_name": s.opening_name,
            "variation_name": s.variation_name,
            "move_sequence": (
                json.loads(s.move_sequence) if s.move_sequence
                else []
            ),
            "total_games": s.total_games,
            "wins": s.wins,
            "losses": s.losses,
            "draws": s.draws,
            "loss_pct": loss_pct,
            "avg_cp_loss": s.avg_cp_loss,
            "divergence_move": s.divergence_move,
            "games": game_summaries,
        })

    # Sort lines by loss percentage
    lines.sort(key=lambda x: x["loss_pct"], reverse=True)

    return {
        "eco_code": eco_code,
        "lines": lines,
    }
