"""Tests for opening stats computation and API (Phase 5)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game, Move, OpeningStats
from services.opening_stats import compute_opening_stats


def _now():
    return datetime.now(tz=timezone.utc)


async def _create_game(
    db: AsyncSession,
    lichess_id: str,
    eco_code: str,
    opening_name: str,
    variation_name: str | None,
    result: str,
    player_color: str = "white",
) -> Game:
    game = Game(
        lichess_id=lichess_id,
        pgn="1. e4 e5 *",
        player_color=player_color,
        result=result,
        played_at=_now(),
        eco_code=eco_code,
        opening_name=opening_name,
        variation_name=variation_name,
        engine_status="complete",
    )
    db.add(game)
    await db.flush()
    return game


async def _create_move(
    db: AsyncSession,
    game_id: int,
    move_number: int,
    phase: str = "opening",
    cp_loss: float = 10.0,
    mistake_severity: str | None = None,
    san: str = "e4",
    color: str = "white",
) -> Move:
    move = Move(
        game_id=game_id,
        move_number=move_number,
        color=color,
        san=san,
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        phase=phase,
        cp_loss=cp_loss,
        mistake_severity=mistake_severity,
    )
    db.add(move)
    await db.flush()
    return move


class TestComputeOpeningStats:
    @pytest.mark.asyncio
    async def test_basic_wld_counts(self, db_session: AsyncSession):
        """W/L/D counts are correct for a 3-game opening line."""
        for i, res in enumerate(["win", "loss", "draw"]):
            g = await _create_game(
                db_session, f"open_wld_{i}", "B08", "Pirc Defense", "Classical", res
            )
            await _create_move(db_session, g.id, 1)

        count = await compute_opening_stats(db_session)
        assert count >= 1

        result = await db_session.execute(
            select(OpeningStats).where(OpeningStats.eco_code == "B08")
        )
        stats = result.scalar_one()
        assert stats.total_games == 3
        assert stats.wins == 1
        assert stats.losses == 1
        assert stats.draws == 1
        assert abs(stats.loss_rate - 1 / 3) < 0.01

    @pytest.mark.asyncio
    async def test_fewer_than_3_games_excluded(self, db_session: AsyncSession):
        """Lines with < 3 games are excluded."""
        for i in range(2):
            g = await _create_game(
                db_session, f"open_few_{i}", "A00", "Uncommon", None, "win"
            )
            await _create_move(db_session, g.id, 1)

        await compute_opening_stats(db_session)

        result = await db_session.execute(
            select(OpeningStats).where(OpeningStats.eco_code == "A00")
        )
        stats = result.scalar_one_or_none()
        assert stats is None

    @pytest.mark.asyncio
    async def test_avg_cp_loss_opening(self, db_session: AsyncSession):
        """avg_cp_loss_opening is the mean of opening-phase cp_loss."""
        for i in range(3):
            g = await _create_game(
                db_session, f"open_cp_{i}", "C50", "Italian Game", "Main", "loss"
            )
            # Each game has 2 opening moves with cp_loss 20 and 40
            await _create_move(db_session, g.id, 1, cp_loss=20.0)
            await _create_move(db_session, g.id, 2, cp_loss=40.0)

        await compute_opening_stats(db_session)

        result = await db_session.execute(
            select(OpeningStats).where(OpeningStats.eco_code == "C50")
        )
        stats = result.scalar_one()
        # Mean of [20, 40, 20, 40, 20, 40] = 30
        assert stats.avg_cp_loss_opening == 30.0

    @pytest.mark.asyncio
    async def test_divergence_move(self, db_session: AsyncSession):
        """divergence_move is most common move number of first mistake."""
        for i in range(3):
            g = await _create_game(
                db_session, f"open_div_{i}", "D00", "Queen Pawn", "Main", "loss"
            )
            # First mistake at move 5 for games 0,1 and move 8 for game 2
            mistake_move = 5 if i < 2 else 8
            await _create_move(db_session, g.id, 1)
            await _create_move(
                db_session, g.id, mistake_move,
                mistake_severity="mistake", san="Nbd7",
            )

        await compute_opening_stats(db_session)

        result = await db_session.execute(
            select(OpeningStats).where(OpeningStats.eco_code == "D00")
        )
        stats = result.scalar_one()
        assert stats.divergence_move == 5
        assert stats.divergence_san == "Nbd7"

    @pytest.mark.asyncio
    async def test_no_divergence_when_no_mistakes(self, db_session: AsyncSession):
        """No divergence if no opening mistakes exist."""
        for i in range(3):
            g = await _create_game(
                db_session, f"open_nodiv_{i}", "E00", "Catalan", None, "win"
            )
            await _create_move(db_session, g.id, 1, cp_loss=5.0)

        await compute_opening_stats(db_session)

        result = await db_session.execute(
            select(OpeningStats).where(OpeningStats.eco_code == "E00")
        )
        stats = result.scalar_one()
        assert stats.divergence_move is None
        assert stats.divergence_san is None

    @pytest.mark.asyncio
    async def test_recompute_replaces_old_data(self, db_session: AsyncSession):
        """Running compute twice replaces old stats."""
        for i in range(3):
            g = await _create_game(
                db_session, f"open_recomp_{i}", "B01", "Scandinavian", None, "win"
            )
            await _create_move(db_session, g.id, 1)

        await compute_opening_stats(db_session)
        await compute_opening_stats(db_session)

        # Should have same count both times, not doubled
        result = await db_session.execute(
            select(OpeningStats).where(OpeningStats.eco_code == "B01")
        )
        all_stats = result.scalars().all()
        assert len(all_stats) == 1


class TestOpeningsAPI:
    @pytest.mark.asyncio
    async def test_list_openings(self, client):
        resp = await client.get("/api/openings")
        assert resp.status_code == 200
        assert "openings" in resp.json()

    @pytest.mark.asyncio
    async def test_get_opening_not_found(self, client):
        resp = await client.get("/api/openings/Z99")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_compute_endpoint(self, client):
        resp = await client.post("/api/openings/compute")
        assert resp.status_code == 200
        assert "lines_computed" in resp.json()
