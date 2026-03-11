"""Tests for condition detection (Phase 4) and scanner."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game, PatternScanLog
from services.classifier import detect_game_conditions
from services.scanner import get_unscanned_games, queue_rescan_for_pattern


def _make_move(**kwargs):
    """Create a SimpleNamespace that mimics a Move ORM object for testing."""
    defaults = {
        "move_number": 1,
        "color": "white",
        "san": "e4",
        "fen_before": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "phase": "opening",
        "cp_eval_before": 30.0,
        "cp_eval_after": -20.0,
        "cp_loss": 0.0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── Game Condition Detection Tests ──────────────────────────────────────


class TestConditionDetection:
    """Tests for detect_game_conditions in classifier.py."""

    def test_gc_006_worse_after_opening(self):
        """GC-006: Total opening cp_loss >= 100 triggers condition."""
        moves = [
            _make_move(phase="opening", color="white", cp_loss=60.0),
            _make_move(phase="opening", color="black", cp_loss=0.0, move_number=1),
            _make_move(phase="opening", color="white", cp_loss=50.0, move_number=2),
        ]
        gc_patterns = [{"id": "GC-006", "axis": "game_condition"}]
        results = detect_game_conditions(
            moves=moves,
            active_gc_patterns=gc_patterns,
            player_color="white",
            game_result="loss",
        )
        assert len(results) == 1
        assert results[0]["registry_pattern_id"] == "GC-006"
        assert results[0]["player_was_worse"] is True

    def test_gc_006_not_triggered_below_threshold(self):
        """GC-006: cp_loss < 100 doesn't trigger."""
        moves = [
            _make_move(phase="opening", color="white", cp_loss=40.0),
            _make_move(phase="opening", color="white", cp_loss=30.0, move_number=2),
        ]
        gc_patterns = [{"id": "GC-006", "axis": "game_condition"}]
        results = detect_game_conditions(
            moves=moves,
            active_gc_patterns=gc_patterns,
            player_color="white",
            game_result="loss",
        )
        assert len(results) == 0

    def test_gc_008_king_safety_deficit(self):
        """GC-008: Player uncastled, opponent castled by move 15."""
        moves = []
        # Opponent castles on move 5
        for i in range(1, 16):
            moves.append(_make_move(
                move_number=i, color="white", san="e4", phase="opening",
            ))
            san = "O-O" if i == 5 else "d5"
            moves.append(_make_move(
                move_number=i, color="black", san=san, phase="opening",
            ))

        gc_patterns = [{"id": "GC-008", "axis": "game_condition"}]
        results = detect_game_conditions(
            moves=moves,
            active_gc_patterns=gc_patterns,
            player_color="white",
            game_result="loss",
        )
        assert len(results) == 1
        assert results[0]["registry_pattern_id"] == "GC-008"

    def test_gc_008_not_triggered_when_player_castles(self):
        """GC-008: Both players castle — no deficit."""
        moves = []
        for i in range(1, 16):
            san_w = "O-O" if i == 4 else "Nf3"
            san_b = "O-O" if i == 5 else "d5"
            moves.append(_make_move(move_number=i, color="white", san=san_w, phase="opening"))
            moves.append(_make_move(move_number=i, color="black", san=san_b, phase="opening"))

        gc_patterns = [{"id": "GC-008", "axis": "game_condition"}]
        results = detect_game_conditions(
            moves=moves,
            active_gc_patterns=gc_patterns,
            player_color="white",
            game_result="draw",
        )
        assert len(results) == 0

    def test_gc_001_rook_pawn_ending(self):
        """GC-001: Only rooks + pawns + kings at endgame start."""
        # FEN with only rooks, pawns, and kings
        rp_fen = "8/5pk1/5p1p/8/1R6/6PP/5PK1/r7 w - - 0 40"
        moves = [
            _make_move(
                phase="endgame", move_number=40,
                fen_before=rp_fen, fen_after=rp_fen,
                cp_eval_before=50.0, color="white",
            ),
        ]
        gc_patterns = [{"id": "GC-001", "axis": "game_condition"}]
        results = detect_game_conditions(
            moves=moves,
            active_gc_patterns=gc_patterns,
            player_color="white",
            game_result="draw",
        )
        assert len(results) == 1
        assert results[0]["registry_pattern_id"] == "GC-001"

    def test_no_detection_for_inactive_patterns(self):
        """Only patterns in active_gc_patterns are checked."""
        moves = [
            _make_move(phase="opening", color="white", cp_loss=200.0),
        ]
        # Empty pattern list — nothing should be detected
        results = detect_game_conditions(
            moves=moves,
            active_gc_patterns=[],
            player_color="white",
            game_result="loss",
        )
        assert len(results) == 0

    def test_empty_moves_returns_empty(self):
        """No moves -> no conditions."""
        gc_patterns = [{"id": "GC-006", "axis": "game_condition"}]
        results = detect_game_conditions(
            moves=[],
            active_gc_patterns=gc_patterns,
            player_color="white",
            game_result="loss",
        )
        assert len(results) == 0


# ── Scanner Tests ───────────────────────────────────────────────────────


class TestScanner:
    """Tests for scanner.py: get_unscanned_games and queue_rescan_for_pattern."""

    @pytest.mark.asyncio
    async def test_get_unscanned_games_all_unscanned(self, db_session: AsyncSession):
        """All engine-complete games returned when no scan logs exist."""
        game = Game(
            lichess_id="test_scan_1",
            pgn="1. e4 *",
            player_color="white",
            result="win",
            engine_status="complete",
            played_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(game)
        await db_session.flush()

        unscanned = await get_unscanned_games(db_session, "GC-099")
        assert game.id in unscanned

    @pytest.mark.asyncio
    async def test_get_unscanned_games_excludes_scanned(self, db_session: AsyncSession):
        """Games with existing scan log are excluded."""
        game = Game(
            lichess_id="test_scan_2",
            pgn="1. e4 *",
            player_color="white",
            result="win",
            engine_status="complete",
            played_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(game)
        await db_session.flush()

        # Add scan log
        log = PatternScanLog(
            game_id=game.id,
            registry_pattern_id="GC-099",
            scanned_at=datetime.now(tz=timezone.utc),
            result="no_match",
            match_count=0,
        )
        db_session.add(log)
        await db_session.flush()

        unscanned = await get_unscanned_games(db_session, "GC-099")
        assert game.id not in unscanned

    @pytest.mark.asyncio
    async def test_get_unscanned_games_excludes_pending_engine(
        self, db_session: AsyncSession
    ):
        """Games with engine_status != 'complete' are excluded."""
        game = Game(
            lichess_id="test_scan_3",
            pgn="1. e4 *",
            player_color="white",
            result="win",
            engine_status="pending",
            played_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(game)
        await db_session.flush()

        unscanned = await get_unscanned_games(db_session, "GC-099")
        assert game.id not in unscanned

    @pytest.mark.asyncio
    async def test_queue_rescan_marks_games(self, db_session: AsyncSession):
        """queue_rescan_for_pattern sets has_unscanned_patterns on unscanned games."""
        game = Game(
            lichess_id="test_scan_4",
            pgn="1. e4 *",
            player_color="white",
            result="win",
            engine_status="complete",
            has_unscanned_patterns=False,
            played_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(game)
        await db_session.flush()

        result = await queue_rescan_for_pattern(db_session, "GC-099")
        assert result["games_queued"] >= 1

        # Verify flag was set
        await db_session.refresh(game)
        assert game.has_unscanned_patterns is True


# ── Admin API Endpoint Tests ────────────────────────────────────────────


class TestAdminEndpoints:
    """Tests for admin API endpoints added in Phase 4."""

    @pytest.mark.asyncio
    async def test_scan_log_endpoint(self, client, db_session):
        resp = await client.get("/api/admin/scan-log")
        assert resp.status_code == 200
        data = resp.json()
        assert "scan_log" in data
        assert "total_games" in data

    @pytest.mark.asyncio
    async def test_stuck_endpoint(self, client):
        resp = await client.get("/api/admin/stuck")
        assert resp.status_code == 200
        data = resp.json()
        assert "stuck_games" in data
        assert "timeout_minutes" in data

    @pytest.mark.asyncio
    async def test_reprocess_game_not_found(self, client):
        resp = await client.post("/api/admin/reprocess/game/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reprocess_pattern_endpoint(self, client):
        resp = await client.post("/api/admin/reprocess/pattern/GC-099")
        assert resp.status_code == 200
        data = resp.json()
        assert "games_queued" in data

    @pytest.mark.asyncio
    async def test_coverage_endpoint(self, client):
        resp = await client.get("/api/admin/coverage")
        assert resp.status_code == 200
        data = resp.json()
        assert "engine" in data
        assert "annotation" in data
        assert "condition" in data

    @pytest.mark.asyncio
    async def test_conditions_endpoint(self, client):
        resp = await client.get("/api/patterns/conditions")
        assert resp.status_code == 200
        data = resp.json()
        assert "conditions" in data
