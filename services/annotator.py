"""Claude API — per-mistake pattern classification."""

import json
import logging

import anthropic

import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a chess coach analyzing a player's mistake.
Given a position, the move played, the best move, and a list of pattern IDs with descriptions,
identify which pattern best matches this mistake.

Rules:
- Return ONLY a JSON object — no prose, no markdown fences
- registry_pattern_id MUST exactly match one of the IDs in the provided list
- If no pattern fits precisely, return the closest match — never return null or an unknown ID
- annotation must be specific: name the pieces and squares involved, state the consequence
- annotation must be 80 words or fewer
- Do not include game_condition patterns (IDs starting with GC-)

Response format:
{"registry_pattern_id": "XX-000", "annotation": "..."}"""

RETRY_APPEND = "\nReturn only raw JSON, nothing else"

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from response."""
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


async def annotate_mistake(
    fen: str,
    played_move_san: str,
    best_move_san: str,
    cp_loss: float,
    phase: str,
    candidate_patterns: list[dict],
) -> dict:
    """Classify a mistake against candidate registry patterns.

    Returns: { registry_pattern_id: str, annotation: str }
    registry_pattern_id will always be one of the IDs in candidate_patterns.
    annotation is max 80 words.
    Never raises — returns UNCLASSIFIED on persistent failure.
    """
    patterns_json = json.dumps(
        [{"id": p["id"], "name": p["name"], "description": p["description"]}
         for p in candidate_patterns]
    )

    user_msg = (
        f"Phase: {phase}\n"
        f"FEN: {fen}\n"
        f"Move played: {played_move_san}\n"
        f"Best move: {best_move_san}\n"
        f"Centipawn loss: {cp_loss}\n\n"
        f"Available patterns:\n{patterns_json}"
    )

    client = _get_client()

    # First attempt
    try:
        result = _call_claude(client, user_msg)
        if result is not None:
            return result
    except Exception as e:
        logger.warning("Annotator first attempt failed: %s", e)

    # Retry with explicit instruction
    try:
        result = _call_claude(client, user_msg + RETRY_APPEND)
        if result is not None:
            return result
    except Exception as e:
        logger.warning("Annotator retry failed: %s", e)

    return {
        "registry_pattern_id": "UNCLASSIFIED",
        "annotation": "Classification failed",
    }


def _call_claude(client: anthropic.Anthropic, user_msg: str) -> dict | None:
    """Make a single Claude call and parse the JSON response.

    Returns parsed dict or None on parse failure.
    """
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = message.content[0].text
    text = _strip_fences(text)

    try:
        parsed = json.loads(text)
        pid = parsed.get("registry_pattern_id")
        annotation = parsed.get("annotation", "")
        if pid and annotation:
            return {"registry_pattern_id": pid, "annotation": annotation}
        logger.warning("Annotator returned incomplete JSON: %s", parsed)
        return None
    except json.JSONDecodeError as e:
        logger.warning("Annotator JSON parse error: %s — response: %s", e, text[:200])
        return None
