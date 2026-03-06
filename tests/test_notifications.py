"""Tests for notifications and acknowledgment endpoints."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    Game,
    Move,
    Pattern,
    PatternInstance,
)


@pytest.fixture(autouse=True)
def _setup_and_teardown():
    """Seed test data, clean up after."""
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

    # Create a game with moves
    game = Game(
        id="game-1", pgn="1. e4",
        white="Player", black="Opp", result="0-1",
        player_color="white", source="pgn_upload",
        analysis_status="analyzed",
        date_played=date(2025, 3, 15),
    )
    db.add(game)
    db.flush()

    moves = []
    for i in range(4):
        m = Move(
            game_id="game-1", move_number=(i // 2) + 1, ply=i,
            san=f"m{i}", uci=f"u{i}",
            fen_before=f"fb{i}", fen_after=f"fa{i}",
            phase="opening", eval_delta=50.0,
            classification="mistake",
        )
        db.add(m)
        db.flush()
        moves.append(m)

    # Create patterns
    p1 = Pattern(
        id="pat-1", label="Missed fork",
        description="Repeatedly misses knight forks",
        category="tactical", frequency=5,
        severity_score=70, acknowledged=True,
        post_acknowledgment_count=2,
    )
    p2 = Pattern(
        id="pat-2", label="Bad pawn push",
        description="Premature pawn push",
        category="strategic", frequency=3,
        severity_score=40,
    )
    p3 = Pattern(
        id="pat-3", label="New issue",
        description="First time seen",
        category="tactical", frequency=1,
        severity_score=20,
    )
    db.add_all([p1, p2, p3])
    db.flush()

    # Link patterns to moves
    db.add(PatternInstance(
        pattern_id="pat-1", game_id="game-1",
        move_id=moves[0].id,
    ))
    db.add(PatternInstance(
        pattern_id="pat-2", game_id="game-1",
        move_id=moves[1].id,
    ))
    db.add(PatternInstance(
        pattern_id="pat-3", game_id="game-1",
        move_id=moves[2].id,
    ))

    db.commit()
    db.close()

    yield

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


# --- Notification tests ---

def test_game_notifications(client):
    resp = client.get("/api/games/game-1/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["game_id"] == "game-1"
    assert data["summary"]["total_matched"] == 3
    assert data["summary"]["recurring_acknowledged"] == 1
    assert data["summary"]["new_patterns"] == 1

    # First notification should be the recurring acknowledged one
    notifs = data["notifications"]
    assert notifs[0]["pattern_label"] == "Missed fork"
    assert notifs[0]["priority_label"] == "recurring_acknowledged"


def test_game_notifications_priority_order(client):
    resp = client.get("/api/games/game-1/notifications")
    notifs = resp.json()["notifications"]
    priorities = [n["priority"] for n in notifs]
    assert priorities == sorted(priorities)


def test_game_not_found(client):
    resp = client.get("/api/games/nonexistent/notifications")
    assert resp.status_code == 404


def test_recent_notifications(client):
    resp = client.get("/api/notifications/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["game_id"] == "game-1"
    assert data["summary"]["total_matched"] == 3


# --- Acknowledgment tests ---

def test_acknowledge_pattern(client):
    resp = client.post(
        "/api/patterns/pat-2/acknowledge",
        json={"player_note": "Will study forks"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"

    # Verify it shows up in acknowledged list
    resp = client.get("/api/patterns/acknowledged")
    assert resp.status_code == 200
    labels = [p["label"] for p in resp.json()["patterns"]]
    assert "Bad pawn push" in labels


def test_acknowledge_not_found(client):
    resp = client.post("/api/patterns/nonexistent/acknowledge")
    assert resp.status_code == 404


def test_revoke_acknowledgment(client):
    # First acknowledge
    client.post("/api/patterns/pat-3/acknowledge")
    # Then revoke
    resp = client.delete("/api/patterns/pat-3/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"


def test_resolve_pattern(client):
    resp = client.post("/api/patterns/pat-3/resolve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_acknowledged_list(client):
    resp = client.get("/api/patterns/acknowledged")
    assert resp.status_code == 200
    data = resp.json()
    # pat-1 is already acknowledged in seed
    assert any(
        p["label"] == "Missed fork" for p in data["patterns"]
    )


def test_acknowledged_list_excludes_resolved(client):
    # Resolve pat-1
    client.post("/api/patterns/pat-1/resolve")

    resp = client.get("/api/patterns/acknowledged")
    data = resp.json()
    labels = [p["label"] for p in data["patterns"]]
    assert "Missed fork" not in labels
