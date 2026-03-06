from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers import analysis, games, patterns, progress, workflows


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Chess Trainer Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(analysis.router, prefix="/api/analyze", tags=["analysis"])
app.include_router(patterns.router, prefix="/api/patterns", tags=["patterns"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
