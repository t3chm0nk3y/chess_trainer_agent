"""FastAPI app, router registration, scheduler startup."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_db, init_db
from routers import admin, analysis, games, openings, patterns, reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing database")
    await init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(title="Chess Trainer Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router)
app.include_router(analysis.router)
app.include_router(patterns.router)
app.include_router(openings.router)
app.include_router(admin.router)
app.include_router(reports.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/config")
async def get_config():
    import config
    token = config.LICHESS_TOKEN
    masked = token[:8] + "..." if len(token) > 8 else "***"
    return {
        "username": config.LICHESS_USERNAME,
        "lichess_token_masked": masked,
        "stockfish_depth": config.STOCKFISH_DEPTH,
    }


@app.put("/api/config")
async def update_config(body: dict):
    """Update .env file with new config values."""
    import pathlib

    env_path = pathlib.Path(".env")
    if not env_path.exists():
        return {"error": ".env file not found"}, 404

    lines = env_path.read_text().splitlines()
    updated_keys = set()

    allowed = {"LICHESS_USERNAME", "LICHESS_TOKEN", "STOCKFISH_DEPTH"}
    updates = {k: v for k, v in body.items() if k in allowed and v}

    new_lines = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    # Append any new keys not already in file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n")
    return {"updated": list(updates.keys()), "note": "Restart required for changes to take effect"}


@app.post("/api/restart")
async def restart_app():
    """Restart the backend process."""
    import os
    import signal
    import threading

    def _restart():
        os.kill(os.getpid(), signal.SIGHUP)

    # Delay slightly so the response can be sent
    threading.Timer(0.5, _restart).start()
    return {"status": "restarting"}


@app.get("/api/dashboard")
async def dashboard(db=Depends(get_db)):
    """Single endpoint for dashboard: recent games, top patterns, pipeline status."""
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from models import Game, OpeningStats, Pattern

    # Total games
    total_q = await db.execute(sa_select(func.count(Game.id)))
    total = total_q.scalar_one()

    # Pipeline status counts
    engine_q = await db.execute(
        sa_select(Game.engine_status, func.count(Game.id)).group_by(Game.engine_status)
    )
    engine = {r[0]: r[1] for r in engine_q.all()}

    annotation_q = await db.execute(
        sa_select(Game.annotation_status, func.count(Game.id)).group_by(Game.annotation_status)
    )
    annotation = {r[0]: r[1] for r in annotation_q.all()}

    condition_q = await db.execute(
        sa_select(Game.condition_status, func.count(Game.id)).group_by(Game.condition_status)
    )
    condition = {r[0]: r[1] for r in condition_q.all()}

    # Recent 10 games
    recent_q = await db.execute(
        sa_select(Game).order_by(Game.played_at.desc()).limit(10)
    )
    recent_games = [
        {
            "id": g.id,
            "played_at": g.played_at.isoformat() if g.played_at else None,
            "result": g.result,
            "opponent_username": g.opponent_username,
            "opening_name": g.opening_name,
            "eco_code": g.eco_code,
            "time_control": g.time_control,
            "engine_status": g.engine_status,
            "annotation_status": g.annotation_status,
        }
        for g in recent_q.scalars().all()
    ]

    # Top 10 recurring patterns (exclude game_condition axis)
    patterns_q = await db.execute(
        sa_select(Pattern)
        .where(Pattern.axis != "game_condition")
        .order_by(Pattern.frequency.desc())
        .limit(10)
    )
    top_patterns = [
        {
            "id": p.id,
            "registry_pattern_id": p.registry_pattern_id,
            "name": p.name,
            "phase": p.phase,
            "axis": p.axis,
            "frequency": p.frequency,
            "games_affected": p.games_affected,
            "example_annotation": p.example_annotation,
        }
        for p in patterns_q.scalars().all()
    ]

    # Opening stats count
    openings_q = await db.execute(sa_select(func.count(OpeningStats.id)))
    openings_computed = openings_q.scalar_one()

    return {
        "total_games": total,
        "pipeline": {
            "engine": engine,
            "annotation": annotation,
            "condition": condition,
        },
        "recent_games": recent_games,
        "top_patterns": top_patterns,
        "openings_computed": openings_computed,
    }
