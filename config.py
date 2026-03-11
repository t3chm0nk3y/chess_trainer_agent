"""All configuration via environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


STOCKFISH_PATH: str = _require("STOCKFISH_PATH")
LICHESS_TOKEN: str = _require("LICHESS_TOKEN")
LICHESS_USERNAME: str = os.getenv("LICHESS_USERNAME", "")
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chess_trainer.db")
STOCKFISH_DEPTH: int = int(os.getenv("STOCKFISH_DEPTH", "18"))
CP_LOSS_INACCURACY: float = float(os.getenv("CP_LOSS_INACCURACY", "50"))
CP_LOSS_MISTAKE: float = float(os.getenv("CP_LOSS_MISTAKE", "100"))
CP_LOSS_BLUNDER: float = float(os.getenv("CP_LOSS_BLUNDER", "200"))
REGISTRY_PATH: str = os.getenv("REGISTRY_PATH", "registry/patterns.yaml")
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
RETRY_INTERVAL_SECONDS: int = int(os.getenv("RETRY_INTERVAL_SECONDS", "300"))
