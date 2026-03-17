"""Report generation service — creates structured JSON reports for chat agent context."""

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import Integer, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Game,
    GameCondition,
    Move,
    MovePatternMatch,
    OpeningStats,
    Pattern,
    Report,
)

logger = logging.getLogger(__name__)

# (report_type, report_key, title, category, data_dict, coverage)
ReportTuple = tuple[str, str, str, str, dict, str]


def _sanitize_key(s: str) -> str:
    """Sanitize a string for use as a report key."""
    key = s.lower().replace(" ", "_").replace(":", "").replace("'", "")
    key = re.sub(r"[^a-z0-9_]", "", key)
    return key[:100]


async def generate_all_reports(db: AsyncSession) -> int:
    """Generate all report categories. Returns total report count."""
    all_reports: list[ReportTuple] = []

    generators = [
        generate_player_profile,
        generate_opening_reports,
        generate_pattern_reports,
        generate_monthly_reports,
        generate_phase_reports,
        generate_game_condition_reports,
        generate_weakness_reports,
    ]

    for gen in generators:
        try:
            reports = await gen(db)
            all_reports.extend(reports)
            logger.info("%s: %d reports", gen.__name__, len(reports))
        except Exception as e:
            logger.error("%s failed: %s", gen.__name__, e)

    count = await _upsert_reports(db, all_reports)
    logger.info("Total reports generated: %d", count)
    return count


async def _upsert_reports(db: AsyncSession, reports: list[ReportTuple]) -> int:
    """Insert or update reports by (report_type, report_key). Returns count."""
    count = 0
    for report_type, report_key, title, category, data_dict, coverage in reports:
        result = await db.execute(
            select(Report).where(
                Report.report_type == report_type,
                Report.report_key == report_key,
            )
        )
        existing = result.scalar_one_or_none()

        data_json = json.dumps(data_dict, default=str)
        now = datetime.now(tz=timezone.utc)

        if existing:
            existing.title = title
            existing.category = category
            existing.data = data_json
            existing.generated_at = now
            existing.data_coverage = coverage
        else:
            db.add(Report(
                report_type=report_type,
                report_key=report_key,
                title=title,
                category=category,
                data=data_json,
                generated_at=now,
                data_coverage=coverage,
            ))
        count += 1

    await db.commit()
    return count


async def _detect_coverage(db: AsyncSession) -> str:
    """Detect data coverage level based on pipeline completion."""
    total_q = await db.execute(select(func.count(Game.id)))
    total = total_q.scalar_one()
    if total == 0:
        return "engine_only"

    ann_q = await db.execute(
        select(func.count(Game.id)).where(Game.annotation_status == "complete")
    )
    annotated = ann_q.scalar_one()

    cond_q = await db.execute(
        select(func.count(Game.id)).where(Game.condition_status == "complete")
    )
    conditions = cond_q.scalar_one()

    ann_pct = annotated / total
    cond_pct = conditions / total
    if ann_pct >= 0.95 and cond_pct >= 0.95:
        return "full"
    elif annotated > 0 or conditions > 0:
        return "partial_annotations"
    return "engine_only"


# ---------------------------------------------------------------------------
# 1. Player Profile
# ---------------------------------------------------------------------------


async def generate_player_profile(db: AsyncSession) -> list[ReportTuple]:
    """Single player profile report."""
    import config

    coverage = await _detect_coverage(db)

    # Total games and results
    total_q = await db.execute(select(func.count(Game.id)))
    total = total_q.scalar_one()

    result_q = await db.execute(
        select(Game.result, func.count(Game.id)).group_by(Game.result)
    )
    results = {r[0]: r[1] for r in result_q.all()}
    wins = results.get("win", 0)
    losses = results.get("loss", 0)
    draws = results.get("draw", 0)

    # Color performance
    color_q = await db.execute(
        select(Game.player_color, Game.result, func.count(Game.id))
        .group_by(Game.player_color, Game.result)
    )
    color_data = {}
    for color, result, cnt in color_q.all():
        if color not in color_data:
            color_data[color] = {"games": 0, "wins": 0, "losses": 0, "draws": 0}
        color_data[color]["games"] += cnt
        if result == "win":
            color_data[color]["wins"] = cnt
        elif result == "loss":
            color_data[color]["losses"] = cnt
        elif result == "draw":
            color_data[color]["draws"] = cnt
    for c in color_data.values():
        c["win_rate"] = round(c["wins"] / c["games"] * 100, 1) if c["games"] else 0

    # Time control breakdown
    tc_q = await db.execute(
        select(Game.time_control, Game.result, func.count(Game.id))
        .group_by(Game.time_control, Game.result)
    )
    tc_data: dict[str, dict] = {}
    for tc, result, cnt in tc_q.all():
        tc_key = tc or "unknown"
        if tc_key not in tc_data:
            tc_data[tc_key] = {"time_control": tc_key, "games": 0, "wins": 0}
        tc_data[tc_key]["games"] += cnt
        if result == "win":
            tc_data[tc_key]["wins"] += cnt
    time_controls = sorted(tc_data.values(), key=lambda x: x["games"], reverse=True)
    for tc in time_controls:
        tc["win_rate"] = round(tc["wins"] / tc["games"] * 100, 1) if tc["games"] else 0

    # Accuracy by phase
    phase_q = await db.execute(
        select(Move.phase, func.avg(Move.cp_loss), func.count(Move.id))
        .where(Move.cp_loss.isnot(None))
        .group_by(Move.phase)
    )
    accuracy_by_phase = {}
    for phase, avg_loss, move_count in phase_q.all():
        accuracy_by_phase[phase] = {
            "avg_cp_loss": round(float(avg_loss), 1),
            "move_count": move_count,
        }

    # Severity distribution
    sev_q = await db.execute(
        select(Move.mistake_severity, func.count(Move.id))
        .where(Move.mistake_severity.isnot(None))
        .group_by(Move.mistake_severity)
    )
    severity = {r[0]: r[1] for r in sev_q.all()}

    # Top 10 openings
    opening_q = await db.execute(
        select(
            Game.eco_code,
            Game.opening_name,
            func.count(Game.id).label("games"),
            func.sum(func.cast(Game.result == "win", Integer)).label("wins"),
        )
        .where(Game.opening_name.isnot(None))
        .group_by(Game.eco_code, Game.opening_name)
        .order_by(func.count(Game.id).desc())
        .limit(10)
    )
    top_openings = []
    for eco, name, games, opening_wins in opening_q.all():
        top_openings.append({
            "eco_code": eco,
            "opening_name": name,
            "games": games,
            "win_rate": round(opening_wins / games * 100, 1) if games else 0,
        })

    # Pipeline status
    eng_q = await db.execute(
        select(func.count(Game.id)).where(Game.engine_status == "complete")
    )
    ann_q = await db.execute(
        select(func.count(Game.id)).where(Game.annotation_status == "complete")
    )
    cond_q = await db.execute(
        select(func.count(Game.id)).where(Game.condition_status == "complete")
    )

    data = {
        "username": config.LICHESS_USERNAME,
        "total_games": total,
        "results": {"wins": wins, "losses": losses, "draws": draws},
        "result_pcts": {
            "win": round(wins / total * 100, 1) if total else 0,
            "loss": round(losses / total * 100, 1) if total else 0,
            "draw": round(draws / total * 100, 1) if total else 0,
        },
        "color_performance": color_data,
        "time_controls": time_controls[:8],
        "accuracy_by_phase": accuracy_by_phase,
        "severity_distribution": severity,
        "top_openings": top_openings,
        "games_analyzed": {
            "engine": eng_q.scalar_one(),
            "annotated": ann_q.scalar_one(),
            "conditions": cond_q.scalar_one(),
        },
    }

    return [("player_profile", "overview", "Player Profile", "Player Profile", data, coverage)]


# ---------------------------------------------------------------------------
# 2. Opening Reports
# ---------------------------------------------------------------------------


async def generate_opening_reports(db: AsyncSession) -> list[ReportTuple]:
    """One report per opening line from OpeningStats."""
    coverage = await _detect_coverage(db)

    # Check if OpeningStats exist, compute if empty
    count_q = await db.execute(select(func.count(OpeningStats.id)))
    if count_q.scalar_one() == 0:
        from services.opening_stats import compute_opening_stats
        await compute_opening_stats(db)

    result = await db.execute(select(OpeningStats).order_by(OpeningStats.loss_rate.desc()))
    all_stats = result.scalars().all()

    reports: list[ReportTuple] = []
    for s in all_stats:
        key_parts = [s.eco_code, s.opening_name]
        if s.variation_name:
            key_parts.append(s.variation_name)
        report_key = _sanitize_key("_".join(key_parts))

        title = f"{s.eco_code} {s.opening_name}"
        if s.variation_name:
            title += f": {s.variation_name}"

        # Get severity counts for opening phase moves in these games
        game_q = await db.execute(
            select(Game.id).where(
                Game.eco_code == s.eco_code,
                Game.opening_name == s.opening_name,
                Game.engine_status == "complete",
            )
        )
        game_ids = [r[0] for r in game_q.all()]

        sev_counts = {}
        if game_ids:
            sev_q = await db.execute(
                select(Move.mistake_severity, func.count(Move.id))
                .where(
                    Move.game_id.in_(game_ids),
                    Move.phase == "opening",
                    Move.mistake_severity.isnot(None),
                )
                .group_by(Move.mistake_severity)
            )
            sev_counts = {r[0]: r[1] for r in sev_q.all()}

        total_mistakes = sum(sev_counts.values())
        avg_mistakes = round(total_mistakes / s.total_games, 2) if s.total_games else 0

        data = {
            "eco_code": s.eco_code,
            "opening_name": s.opening_name,
            "variation_name": s.variation_name,
            "total_games": s.total_games,
            "results": {"wins": s.wins, "losses": s.losses, "draws": s.draws},
            "win_rate": round(s.win_rate * 100, 1),
            "loss_rate": round(s.loss_rate * 100, 1),
            "avg_cp_loss_opening": s.avg_cp_loss_opening,
            "divergence_move": s.divergence_move,
            "divergence_san": s.divergence_san,
            "severity_in_opening": sev_counts,
            "avg_mistakes_per_game": avg_mistakes,
        }

        reports.append(("opening", report_key, title, "Opening", data, coverage))

    return reports


# ---------------------------------------------------------------------------
# 3. Pattern Reports
# ---------------------------------------------------------------------------


async def generate_pattern_reports(db: AsyncSession) -> list[ReportTuple]:
    """One report per Pattern record."""
    coverage = await _detect_coverage(db)

    result = await db.execute(
        select(Pattern).order_by(Pattern.frequency.desc())
    )
    patterns = result.scalars().all()

    reports: list[ReportTuple] = []
    for p in patterns:
        # Get 5 most recent occurrences
        occ_q = await db.execute(
            select(MovePatternMatch)
            .where(MovePatternMatch.registry_pattern_id == p.registry_pattern_id)
            .order_by(MovePatternMatch.matched_at.desc())
            .limit(5)
        )
        occurrences = []
        for m in occ_q.scalars().all():
            # Get the move details
            move_q = await db.execute(select(Move).where(Move.id == m.move_id))
            move = move_q.scalar_one_or_none()
            occurrences.append({
                "game_id": m.game_id,
                "move_number": move.move_number if move else None,
                "san": move.san if move else None,
                "annotation": m.annotation,
            })

        report_key = _sanitize_key(p.registry_pattern_id)

        data = {
            "registry_pattern_id": p.registry_pattern_id,
            "name": p.name,
            "phase": p.phase,
            "axis": p.axis,
            "frequency": p.frequency,
            "games_affected": p.games_affected,
            "first_seen": p.first_seen_at.isoformat() if p.first_seen_at else None,
            "last_seen": p.last_seen_at.isoformat() if p.last_seen_at else None,
            "example_fen": p.example_fen,
            "example_annotation": p.example_annotation,
            "recent_occurrences": occurrences,
        }

        reports.append(("pattern", report_key, p.name, "Pattern", data, coverage))

    return reports


# ---------------------------------------------------------------------------
# 4. Monthly Reports
# ---------------------------------------------------------------------------


async def generate_monthly_reports(db: AsyncSession) -> list[ReportTuple]:
    """One report per calendar month with games."""
    coverage = await _detect_coverage(db)

    # Get all games with played_at
    games_q = await db.execute(
        select(Game).where(Game.played_at.isnot(None)).order_by(Game.played_at)
    )
    all_games = games_q.scalars().all()

    # Group by year-month
    months: dict[str, list[Game]] = {}
    for g in all_games:
        key = g.played_at.strftime("%Y-%m")
        months.setdefault(key, []).append(g)

    reports: list[ReportTuple] = []
    for month_key, games in months.items():
        total = len(games)
        wins = sum(1 for g in games if g.result == "win")
        losses = sum(1 for g in games if g.result == "loss")
        draws = sum(1 for g in games if g.result == "draw")

        game_ids = [g.id for g in games]

        # Avg cp_loss by phase
        phase_q = await db.execute(
            select(Move.phase, func.avg(Move.cp_loss))
            .where(Move.game_id.in_(game_ids), Move.cp_loss.isnot(None))
            .group_by(Move.phase)
        )
        avg_cp_by_phase = {r[0]: round(float(r[1]), 1) for r in phase_q.all()}

        overall_q = await db.execute(
            select(func.avg(Move.cp_loss))
            .where(Move.game_id.in_(game_ids), Move.cp_loss.isnot(None))
        )
        overall_avg = overall_q.scalar_one()

        # Severity counts
        sev_q = await db.execute(
            select(Move.mistake_severity, func.count(Move.id))
            .where(
                Move.game_id.in_(game_ids),
                Move.mistake_severity.isnot(None),
            )
            .group_by(Move.mistake_severity)
        )
        severity = {r[0]: r[1] for r in sev_q.all()}
        blunders = severity.get("blunder", 0)

        # Best/worst openings (min 3 games)
        opening_groups: dict[str, dict] = {}
        for g in games:
            name = g.opening_name or "Unknown"
            if name not in opening_groups:
                opening_groups[name] = {"opening_name": name, "games": 0, "wins": 0}
            opening_groups[name]["games"] += 1
            if g.result == "win":
                opening_groups[name]["wins"] += 1

        qualified = [
            {**o, "win_rate": round(o["wins"] / o["games"] * 100, 1)}
            for o in opening_groups.values()
            if o["games"] >= 3
        ]
        best = sorted(qualified, key=lambda x: x["win_rate"], reverse=True)[:3]
        worst = sorted(qualified, key=lambda x: x["win_rate"])[:3]

        # Patterns first seen this month
        year, mon = month_key.split("-")
        pat_q = await db.execute(
            select(Pattern.registry_pattern_id, Pattern.name)
            .where(
                extract("year", Pattern.first_seen_at) == int(year),
                extract("month", Pattern.first_seen_at) == int(mon),
            )
        )
        new_patterns = [
            {"registry_pattern_id": r[0], "name": r[1]} for r in pat_q.all()
        ]

        data = {
            "month": month_key,
            "games_played": total,
            "results": {"wins": wins, "losses": losses, "draws": draws},
            "win_rate": round(wins / total * 100, 1) if total else 0,
            "avg_cp_loss": {
                "overall": round(float(overall_avg), 1) if overall_avg else None,
                **avg_cp_by_phase,
            },
            "severity_counts": severity,
            "blunder_rate_per_game": round(blunders / total, 2) if total else 0,
            "best_openings": best,
            "worst_openings": worst,
            "new_patterns_detected": new_patterns,
        }

        title = f"Monthly Summary — {month_key}"
        reports.append(("monthly", month_key, title, "Monthly", data, coverage))

    return reports


# ---------------------------------------------------------------------------
# 5. Phase Reports
# ---------------------------------------------------------------------------


async def generate_phase_reports(db: AsyncSession) -> list[ReportTuple]:
    """Three reports: opening, middlegame, endgame."""
    coverage = await _detect_coverage(db)

    # Get total games and median played_at for trend split
    total_q = await db.execute(select(func.count(Game.id)))
    total_games = total_q.scalar_one()

    # Find median game by played_at for trend comparison
    median_q = await db.execute(
        select(Game.played_at)
        .order_by(Game.played_at)
        .limit(1)
        .offset(total_games // 2)
    )
    median_date = median_q.scalar_one_or_none()

    reports: list[ReportTuple] = []
    for phase in ("opening", "middlegame", "endgame"):
        # Overall stats
        stats_q = await db.execute(
            select(
                func.count(Move.id),
                func.avg(Move.cp_loss),
            )
            .where(Move.phase == phase, Move.cp_loss.isnot(None))
        )
        row = stats_q.one()
        total_moves = row[0]
        avg_cp_loss = round(float(row[1]), 1) if row[1] else 0

        # Severity distribution
        sev_q = await db.execute(
            select(Move.mistake_severity, func.count(Move.id))
            .where(Move.phase == phase, Move.mistake_severity.isnot(None))
            .group_by(Move.mistake_severity)
        )
        severity = {r[0]: r[1] for r in sev_q.all()}

        total_mistakes = sum(severity.values())
        mistakes_per_game = round(total_mistakes / total_games, 2) if total_games else 0

        # Top patterns in this phase
        pat_q = await db.execute(
            select(Pattern)
            .where(Pattern.phase == phase, Pattern.axis != "game_condition")
            .order_by(Pattern.frequency.desc())
            .limit(5)
        )
        top_patterns = [
            {"name": p.name, "frequency": p.frequency, "axis": p.axis}
            for p in pat_q.scalars().all()
        ]

        # Trend: recent vs older (split at median date)
        trend = {}
        if median_date:
            recent_q = await db.execute(
                select(func.avg(Move.cp_loss))
                .join(Game, Move.game_id == Game.id)
                .where(
                    Move.phase == phase,
                    Move.cp_loss.isnot(None),
                    Game.played_at >= median_date,
                )
            )
            older_q = await db.execute(
                select(func.avg(Move.cp_loss))
                .join(Game, Move.game_id == Game.id)
                .where(
                    Move.phase == phase,
                    Move.cp_loss.isnot(None),
                    Game.played_at < median_date,
                )
            )
            recent_avg = recent_q.scalar_one()
            older_avg = older_q.scalar_one()

            if recent_avg is not None and older_avg is not None:
                r = round(float(recent_avg), 1)
                o = round(float(older_avg), 1)
                direction = "improving" if r < o else "worsening" if r > o else "stable"
                trend = {
                    "recent_avg_cp_loss": r,
                    "older_avg_cp_loss": o,
                    "direction": direction,
                }

        data = {
            "phase": phase,
            "total_moves": total_moves,
            "avg_cp_loss": avg_cp_loss,
            "severity_distribution": severity,
            "mistakes_per_game": mistakes_per_game,
            "top_patterns": top_patterns,
            "trend": trend,
        }

        title = f"{phase.title()} Phase Analysis"
        reports.append(("phase", phase, title, "Phase", data, coverage))

    return reports


# ---------------------------------------------------------------------------
# 6. Game Condition Reports
# ---------------------------------------------------------------------------


async def generate_game_condition_reports(db: AsyncSession) -> list[ReportTuple]:
    """One report per game condition type detected."""
    coverage = await _detect_coverage(db)

    # Get overall loss rate for comparison
    total_q = await db.execute(select(func.count(Game.id)))
    total_games = total_q.scalar_one()
    loss_q = await db.execute(
        select(func.count(Game.id)).where(Game.result == "loss")
    )
    total_losses = loss_q.scalar_one()
    overall_loss_rate = round(total_losses / total_games * 100, 1) if total_games else 0

    # Get condition patterns
    pat_q = await db.execute(
        select(Pattern).where(Pattern.axis == "game_condition")
    )
    condition_patterns = pat_q.scalars().all()

    reports: list[ReportTuple] = []
    for p in condition_patterns:
        # Get all GameCondition records for this pattern
        gc_q = await db.execute(
            select(GameCondition)
            .where(GameCondition.registry_pattern_id == p.registry_pattern_id)
        )
        conditions = gc_q.scalars().all()

        if not conditions:
            continue

        total = len(conditions)
        wins = sum(1 for c in conditions if c.game_result == "win")
        losses = sum(1 for c in conditions if c.game_result == "loss")
        draws = sum(1 for c in conditions if c.game_result == "draw")
        loss_rate = round(losses / total * 100, 1) if total else 0
        worse_count = sum(1 for c in conditions if c.player_was_worse)

        moves_detected = [c.detected_at_move for c in conditions if c.detected_at_move]
        avg_move = round(sum(moves_detected) / len(moves_detected), 1) if moves_detected else None

        report_key = _sanitize_key(p.registry_pattern_id)

        data = {
            "registry_pattern_id": p.registry_pattern_id,
            "condition_name": p.name,
            "total_occurrences": total,
            "results": {"wins": wins, "losses": losses, "draws": draws},
            "loss_rate": loss_rate,
            "overall_loss_rate": overall_loss_rate,
            "loss_rate_delta": round(loss_rate - overall_loss_rate, 1),
            "player_was_worse_pct": round(worse_count / total * 100, 1) if total else 0,
            "avg_detected_at_move": avg_move,
        }

        reports.append((
            "game_condition", report_key, f"Condition: {p.name}",
            "Game Condition", data, coverage,
        ))

    return reports


# ---------------------------------------------------------------------------
# 7. Weakness Reports
# ---------------------------------------------------------------------------


async def generate_weakness_reports(db: AsyncSession) -> list[ReportTuple]:
    """Synthesized weakness reports."""
    coverage = await _detect_coverage(db)
    reports: list[ReportTuple] = []

    # Tactical weaknesses
    tac_q = await db.execute(
        select(Pattern)
        .where(Pattern.axis == "tactical")
        .order_by(Pattern.frequency.desc())
        .limit(10)
    )
    tactical_items = [
        {
            "name": p.name,
            "frequency": p.frequency,
            "games_affected": p.games_affected,
            "phase": p.phase,
        }
        for p in tac_q.scalars().all()
    ]
    reports.append((
        "weakness", "tactical",
        "Tactical Weaknesses", "Weakness",
        {"weakness_type": "tactical", "summary": "Top tactical weaknesses by frequency",
         "items": tactical_items},
        coverage,
    ))

    # Strategic weaknesses
    str_q = await db.execute(
        select(Pattern)
        .where(Pattern.axis == "strategic")
        .order_by(Pattern.frequency.desc())
        .limit(10)
    )
    strategic_items = [
        {
            "name": p.name,
            "frequency": p.frequency,
            "games_affected": p.games_affected,
            "phase": p.phase,
        }
        for p in str_q.scalars().all()
    ]
    reports.append((
        "weakness", "strategic",
        "Strategic Weaknesses", "Weakness",
        {"weakness_type": "strategic", "summary": "Top strategic weaknesses by frequency",
         "items": strategic_items},
        coverage,
    ))

    # Worst openings
    opening_q = await db.execute(
        select(OpeningStats)
        .where(OpeningStats.total_games >= 5)
        .order_by(OpeningStats.loss_rate.desc())
        .limit(5)
    )
    worst_openings = [
        {
            "eco_code": s.eco_code,
            "opening_name": s.opening_name,
            "variation_name": s.variation_name,
            "games": s.total_games,
            "loss_rate": round(s.loss_rate * 100, 1),
            "avg_cp_loss": s.avg_cp_loss_opening,
        }
        for s in opening_q.scalars().all()
    ]
    reports.append((
        "weakness", "openings",
        "Worst Openings", "Weakness",
        {"weakness_type": "openings", "summary": "Openings with highest loss rate (min 5 games)",
         "items": worst_openings},
        coverage,
    ))

    # Color comparison
    color_q = await db.execute(
        select(Game.player_color, Game.result, func.count(Game.id))
        .group_by(Game.player_color, Game.result)
    )
    color_stats: dict[str, dict] = {}
    for color, result, cnt in color_q.all():
        if color not in color_stats:
            color_stats[color] = {"games": 0, "wins": 0, "losses": 0, "draws": 0}
        color_stats[color]["games"] += cnt
        if result == "win":
            color_stats[color]["wins"] = cnt
        elif result == "loss":
            color_stats[color]["losses"] = cnt
        elif result == "draw":
            color_stats[color]["draws"] = cnt

    # Add avg cp_loss per color
    for color in color_stats:
        cp_q = await db.execute(
            select(func.avg(Move.cp_loss))
            .join(Game, Move.game_id == Game.id)
            .where(Game.player_color == color, Move.cp_loss.isnot(None))
        )
        avg = cp_q.scalar_one()
        color_stats[color]["avg_cp_loss"] = round(float(avg), 1) if avg else None
        g = color_stats[color]["games"]
        color_stats[color]["win_rate"] = round(
            color_stats[color]["wins"] / g * 100, 1
        ) if g else 0

    reports.append((
        "weakness", "color",
        "Color Performance Comparison", "Weakness",
        {"weakness_type": "color", "summary": "White vs black performance",
         "comparison": color_stats},
        coverage,
    ))

    # Time control comparison
    tc_q = await db.execute(
        select(Game.time_control, Game.result, func.count(Game.id))
        .group_by(Game.time_control, Game.result)
    )
    tc_stats: dict[str, dict] = {}
    for tc, result, cnt in tc_q.all():
        tc_key = tc or "unknown"
        if tc_key not in tc_stats:
            tc_stats[tc_key] = {"time_control": tc_key, "games": 0, "wins": 0, "losses": 0}
        tc_stats[tc_key]["games"] += cnt
        if result == "win":
            tc_stats[tc_key]["wins"] += cnt
        elif result == "loss":
            tc_stats[tc_key]["losses"] += cnt

    tc_items = []
    for tc in sorted(tc_stats.values(), key=lambda x: x["games"], reverse=True):
        g = tc["games"]
        tc["win_rate"] = round(tc["wins"] / g * 100, 1) if g else 0
        tc["loss_rate"] = round(tc["losses"] / g * 100, 1) if g else 0
        tc_items.append(tc)

    reports.append((
        "weakness", "time_control",
        "Time Control Performance", "Weakness",
        {"weakness_type": "time_control",
         "summary": "Performance comparison across time controls",
         "items": tc_items[:10]},
        coverage,
    ))

    return reports
