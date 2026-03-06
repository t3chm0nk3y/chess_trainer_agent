"""Tests for the openings API endpoints."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import Game, Move
from backend.services.opening_analyzer import compute_opening_stats


@pytest.fixture(autouse=True)
def _seed_data():
    """Seed test data before each test, clean up after."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def _override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    db = Session()

    for i, (eco, name, result) in enumerate([
        ("B20", "Sicilian Defense", "0-1"),
        ("B20", "Sicilian Defense", "0-1"),
        ("B20", "Sicilian Defense", "1-0"),
        ("C50", "Italian Game", "1-0"),
        ("C50", "Italian Game", "1-0"),
    ]):
        game = Game(
            pgn="1. e4",
            white="Player", black="Opp",
            result=result,
            date_played=date(2025, 3, i + 1),
            opening_eco=eco, opening_name=name,
            player_color="white", source="pgn_upload",
            analysis_status="analyzed",
        )
        db.add(game)
        db.flush()
        move = Move(
            game_id=game.id, move_number=1, ply=0,
            san="e4", uci="e2e4",
            fen_before="start", fen_after="after",
            phase="opening", eval_delta=15.0,
            classification="good",
        )
        db.add(move)

    db.commit()
    compute_opening_stats(db)
    db.close()

    yield

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_list_openings(client):
    resp = client.get("/api/openings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    openings = data["openings"]
    # Sorted by loss_pct desc: B20 (66.7%) > C50 (0%)
    assert openings[0]["eco_code"] == "B20"
    assert openings[0]["loss_pct"] > openings[1]["loss_pct"]


def test_list_openings_sort_by_games(client):
    resp = client.get("/api/openings?sort_by=total_games")
    assert resp.status_code == 200
    data = resp.json()
    assert (
        data["openings"][0]["total_games"]
        >= data["openings"][1]["total_games"]
    )


def test_get_opening_detail(client):
    resp = client.get("/api/openings/B20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["eco_code"] == "B20"
    assert len(data["lines"]) == 1
    assert data["lines"][0]["total_games"] == 3


def test_get_opening_not_found(client):
    resp = client.get("/api/openings/Z99")
    assert resp.status_code == 404


def test_refresh_openings(client):
    resp = client.post("/api/openings/refresh")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["openings_computed"] == 2
