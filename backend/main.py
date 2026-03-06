from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers import (
    analysis,
    games,
    notifications,
    openings,
    patterns,
    progress,
    reports,
    workflows,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed initial data
    from backend.database import SessionLocal
    from backend.seed import seed_mistake_categories
    db = SessionLocal()
    try:
        seed_mistake_categories(db)
    finally:
        db.close()
    yield
    # Cleanup engine on shutdown
    from backend.services.engine import stockfish
    stockfish.close()


app = FastAPI(title="Chess Trainer Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(openings.router, prefix="/api/openings", tags=["openings"])
app.include_router(analysis.router, prefix="/api/analyze", tags=["analysis"])
app.include_router(patterns.router, prefix="/api/patterns", tags=["patterns"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
