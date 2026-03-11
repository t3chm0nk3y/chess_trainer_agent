"""Tests for retry worker and reliability (Phase 6)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game
from pipeline.retry import (
    compute_next_retry,
    mark_exceeded_retries,
    reset_stuck_jobs,
    retry_failed_games,
    run_retry_cycle,
)


def _now():
    return datetime.now(tz=timezone.utc)


async def _make_game(db: AsyncSession, lichess_id: str, **kwargs) -> Game:
    defaults = {
        "pgn": "1. e4 *",
        "player_color": "white",
        "result": "loss",
        "played_at": _now(),
        "engine_status": "pending",
    }
    defaults.update(kwargs)
    game = Game(lichess_id=lichess_id, **defaults)
    db.add(game)
    await db.flush()
    return game


class TestComputeNextRetry:
    def test_first_retry_2_minutes(self):
        delay = compute_next_retry(1)
        assert delay.total_seconds() == 120

    def test_second_retry_10_minutes(self):
        delay = compute_next_retry(2)
        assert delay.total_seconds() == 600

    def test_fifth_retry_24_hours(self):
        delay = compute_next_retry(5)
        assert delay.total_seconds() == 86400

    def test_beyond_schedule_defaults_to_24_hours(self):
        delay = compute_next_retry(99)
        assert delay.total_seconds() == 86400


class TestRetryFailedGames:
    @pytest.mark.asyncio
    async def test_retries_failed_engine(self, db_session: AsyncSession):
        game = await _make_game(
            db_session, "retry_1",
            engine_status="failed",
            engine_failure_count=1,
        )
        count = await retry_failed_games(db_session)
        assert count == 1
        await db_session.refresh(game)
        assert game.engine_status == "pending"

    @pytest.mark.asyncio
    async def test_retries_failed_annotation(self, db_session: AsyncSession):
        game = await _make_game(
            db_session, "retry_2",
            engine_status="complete",
            annotation_status="failed",
            engine_failure_count=1,
        )
        count = await retry_failed_games(db_session)
        assert count >= 1
        await db_session.refresh(game)
        assert game.annotation_status == "pending"

    @pytest.mark.asyncio
    async def test_skips_games_at_max_retries(self, db_session: AsyncSession):
        game = await _make_game(
            db_session, "retry_3",
            engine_status="failed",
            engine_failure_count=5,
        )
        await retry_failed_games(db_session)
        # Should NOT retry — at max retries
        await db_session.refresh(game)
        assert game.engine_status == "failed"


class TestMarkExceededRetries:
    @pytest.mark.asyncio
    async def test_marks_needs_manual_review(self, db_session: AsyncSession):
        game = await _make_game(
            db_session, "exceed_1",
            engine_status="failed",
            engine_failure_count=5,
        )
        count = await mark_exceeded_retries(db_session)
        assert count >= 1
        await db_session.refresh(game)
        assert game.engine_status == "needs_manual_review"

    @pytest.mark.asyncio
    async def test_does_not_mark_below_max(self, db_session: AsyncSession):
        game = await _make_game(
            db_session, "exceed_2",
            engine_status="failed",
            engine_failure_count=2,
        )
        await mark_exceeded_retries(db_session)
        await db_session.refresh(game)
        assert game.engine_status == "failed"


class TestResetStuckJobs:
    @pytest.mark.asyncio
    async def test_resets_stuck_engine(self, db_session: AsyncSession):
        game = await _make_game(
            db_session, "stuck_1",
            engine_status="running",
        )
        count = await reset_stuck_jobs(db_session)
        assert count >= 1
        await db_session.refresh(game)
        assert game.engine_status == "pending"

    @pytest.mark.asyncio
    async def test_does_not_reset_completed(self, db_session: AsyncSession):
        game = await _make_game(
            db_session, "stuck_2",
            engine_status="complete",
        )
        await reset_stuck_jobs(db_session)
        await db_session.refresh(game)
        assert game.engine_status == "complete"


class TestRunRetryCycle:
    @pytest.mark.asyncio
    async def test_full_cycle(self, db_session: AsyncSession):
        # One failed, one stuck, one exceeded
        await _make_game(
            db_session, "cycle_1",
            engine_status="failed", engine_failure_count=1,
        )
        await _make_game(
            db_session, "cycle_2",
            engine_status="running",
        )
        await _make_game(
            db_session, "cycle_3",
            engine_status="failed", engine_failure_count=6,
        )

        result = await run_retry_cycle(db_session)
        assert result["exceeded_marked"] >= 1
        assert result["stuck_reset"] >= 1
        assert result["failed_retried"] >= 1


class TestAnalysisEndpoints:
    @pytest.mark.asyncio
    async def test_status_endpoint(self, client):
        resp = await client.get("/api/analysis/status")
        assert resp.status_code == 200
        assert "total_games" in resp.json()

    @pytest.mark.asyncio
    async def test_failed_endpoint(self, client):
        resp = await client.get("/api/analysis/failed")
        assert resp.status_code == 200
        assert "failed_games" in resp.json()

    @pytest.mark.asyncio
    async def test_retry_failed_endpoint(self, client):
        resp = await client.post("/api/analysis/retry-failed")
        assert resp.status_code == 200
        assert "games_retried" in resp.json()

    @pytest.mark.asyncio
    async def test_run_endpoint(self, client):
        resp = await client.post("/api/analysis/run")
        assert resp.status_code == 200
        assert "pending_games" in resp.json()
