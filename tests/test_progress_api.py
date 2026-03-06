"""Tests for progress tracking endpoints."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import Game, Move, Pattern


@pytest.fixture(autouse=True)
def _setup_and_teardown():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override

    db = Session()

    for i in range(3):
        g = Game(
            pgn="1. e4", white="P", black="O",
            result="1-0", player_color="white",
            source="pgn_upload", analysis_status="analyzed",
            date_played=date(2025, 3, i + 1),
        )
        db.add(g)
        db.flush()
        for j in range(4):
            db.add(Move(
                game_id=g.id, move_number=(j // 2) + 1, ply=j,
                san=f"m{j}", uci=f"u{j}",
                fen_before=f"fb{j}", fen_after=f"fa{j}",
                phase="opening" if j < 2 else "middlegame",
                classification="good" if j < 3 else "mistake",
                eval_delta=10.0 if j < 3 else 80.0,
            ))

    for i in range(2):
        g = Game(
            pgn="1. e4", white="P", black="O",
            result="0-1", player_color="white",
            source="pgn_upload", analysis_status="analyzed",
            date_played=date(2025, 2, i + 1),
        )
        db.add(g)
        db.flush()
        for j in range(4):
            db.add(Move(
                game_id=g.id, move_number=(j // 2) + 1, ply=j,
                san=f"m{j}", uci=f"u{j}",
                fen_before=f"fb{j}", fen_after=f"fa{j}",
                phase="opening" if j < 2 else "endgame",
                classification="mistake",
                eval_delta=100.0,
            ))

    db.add(Pattern(
        label="P1", description="d", category="tactical",
        frequency=3, acknowledged=True,
        post_acknowledgment_count=1,
    ))
    db.add(Pattern(
        label="P2", description="d", category="tactical",
        frequency=2, resolved=True,
    ))

    db.commit()
    db.close()

    yield

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_progress_summary(client):
    resp = client.get("/api/progress/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_games"] == 5
    assert data["accuracy"] > 0
    assert "opening" in data["phase_accuracy"]
    assert data["active_patterns"] == 1
    assert data["acknowledged_patterns"] == 1
    assert data["recurring_patterns"] == 1
    assert data["resolved_patterns"] == 1


def test_sessions(client):
    resp = client.get("/api/progress/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sessions"]) > 0
    session = data["sessions"][0]
    assert "date" in session
    assert "games" in session
    assert "accuracy" in session


def test_compare_periods(client):
    resp = client.get(
        "/api/progress/compare"
        "?from_date=2025-03-01&to_date=2025-03-31"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "current_period" in data
    assert "prior_period" in data
    assert "delta" in data
    assert data["current_period"]["games"] == 3
    assert data["delta"]["accuracy"] > 0


def test_compare_invalid_date(client):
    resp = client.get(
        "/api/progress/compare?from_date=bad&to_date=bad"
    )
    assert resp.status_code == 400
