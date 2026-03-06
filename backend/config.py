import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    LICHESS_TOKEN: str = os.getenv("LICHESS_TOKEN", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{Path(__file__).resolve().parent / 'chess_trainer.db'}",
    )
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    ENGINE_DEPTH: int = int(os.getenv("ENGINE_DEPTH", "20"))
    STOCKFISH_PATH: str = os.getenv("STOCKFISH_PATH", "stockfish")
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
