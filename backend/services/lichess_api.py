"""Direct Lichess API client for game import (used until Lichess MCP is connected)."""

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

LICHESS_API = "https://lichess.org/api"


async def fetch_games(
    username: str,
    since: str | None = None,
    max_games: int | None = None,
    color: str | None = None,
    rated: bool | None = None,
    time_control: str | None = None,
) -> str:
    """Fetch games from Lichess as PGN text.

    Args:
        username: Lichess username.
        since: ISO date string (e.g. "2025-01-01"). Games after this date.
        max_games: Maximum number of games to fetch. None = all games.
        color: "white" or "black" to filter by player color.
        rated: True for rated only, False for casual only, None for both.
        time_control: "bullet", "blitz", "rapid", "classical", "correspondence".

    Returns:
        Raw PGN text of all fetched games.
    """
    params = {
        "pgnInJson": "false",
        "tags": "true",
        "clocks": "false",
        "evals": "false",
        "opening": "true",
    }
    if max_games is not None:
        params["max"] = max_games

    if since:
        # Convert date string to epoch milliseconds
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(since)
            params["since"] = int(dt.timestamp() * 1000)
        except ValueError:
            logger.warning("Invalid since date: %s", since)

    if color and color in ("white", "black"):
        params["color"] = color

    if rated is not None:
        params["rated"] = str(rated).lower()

    if time_control and time_control in ("bullet", "blitz", "rapid", "classical", "correspondence"):
        params["perfType"] = time_control

    headers = {
        "Accept": "application/x-chess-pgn",
    }
    if settings.LICHESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.LICHESS_TOKEN}"

    url = f"{LICHESS_API}/games/user/{username}"
    logger.info("Fetching Lichess games: %s params=%s", url, params)

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        pgn_text = response.text

    logger.info("Fetched %d bytes of PGN from Lichess", len(pgn_text))
    return pgn_text
