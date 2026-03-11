"""Tests for Lichess import deduplication."""

from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Game


@pytest_asyncio.fixture
async def existing_game(db_session: AsyncSession):
    """Insert a game that would conflict on lichess_id."""
    game = Game(
        lichess_id="abc123",
        pgn="1. e4 e5",
        player_color="white",
        opponent_username="Opp",
        result="win",
        played_at=datetime(2026, 1, 1),
        engine_status="pending",
        annotation_status="pending",
        condition_status="pending",
    )
    db_session.add(game)
    await db_session.commit()
    return game


@pytest.mark.asyncio
async def test_duplicate_lichess_id_rejected(db_session, existing_game):
    """Inserting a game with the same lichess_id should fail."""
    from sqlalchemy.exc import IntegrityError

    dup = Game(
        lichess_id="abc123",  # same as existing
        pgn="1. d4 d5",
        player_color="black",
        result="loss",
        played_at=datetime(2026, 2, 1),
        engine_status="pending",
        annotation_status="pending",
        condition_status="pending",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_different_lichess_id_accepted(db_session, existing_game):
    """Games with different lichess_ids should coexist."""
    new_game = Game(
        lichess_id="def456",
        pgn="1. d4 d5",
        player_color="black",
        result="loss",
        played_at=datetime(2026, 2, 1),
        engine_status="pending",
        annotation_status="pending",
        condition_status="pending",
    )
    db_session.add(new_game)
    await db_session.flush()

    result = await db_session.execute(select(Game))
    games = result.scalars().all()
    assert len(games) == 2


@pytest.mark.asyncio
async def test_import_dedup_via_api(client, existing_game):
    """The /api/games endpoint should show the existing game."""
    resp = await client.get("/api/games")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
