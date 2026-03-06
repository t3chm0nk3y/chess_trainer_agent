"""Claude API integration for pattern recognition and coaching."""

import json
import logging

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

ANNOTATION_SYSTEM_PROMPT = """You are an expert chess coach analyzing a student's game. \
For each mistake or blunder, provide a clear, instructive explanation of what went wrong \
and what the correct idea was. Be specific about the chess concepts involved."""

SYNTHESIS_SYSTEM_PROMPT = """You are an expert chess coach analyzing a student's complete \
game history to identify recurring patterns of mistakes. Group similar errors into named \
patterns, assign severity scores, and provide concrete training recommendations."""


async def annotate_game_mistakes(
    pgn: str,
    mistakes: list[dict],
) -> list[dict]:
    """Pass 1: Per-game annotation. Ask Claude to explain each mistake.

    Args:
        pgn: The game PGN with engine eval annotations.
        mistakes: List of mistake dicts with keys:
            fen, san, best_move, eval_delta, phase, themes

    Returns:
        List of dicts with added 'annotation' field.
    """
    if not mistakes:
        return []

    user_prompt = f"""Here is a chess game with engine analysis:

<pgn>
{pgn}
</pgn>

The following moves were identified as inaccuracies, mistakes, or blunders:

<mistakes>
{json.dumps(mistakes, indent=2)}
</mistakes>

For each mistake, explain:
1. What the player likely intended or overlooked
2. Why the engine's recommended move is better
3. The chess concept or principle that applies

Respond in JSON format: {{ "annotations": [{{ "ply": <ply>, "annotation": "<explanation>" }}] }}"""

    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=ANNOTATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    try:
        response_text = message.content[0].text
        # Extract JSON from response
        parsed = json.loads(response_text)
        return parsed.get("annotations", [])
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error("Failed to parse Claude annotation response: %s", e)
        return []


async def synthesize_patterns(
    game_mistakes: list[dict],
    existing_patterns: list[dict] | None = None,
) -> list[dict]:
    """Pass 2: Cross-game pattern synthesis.

    Args:
        game_mistakes: Aggregated mistakes across all analyzed games.
        existing_patterns: Currently known patterns (for diffing).

    Returns:
        List of pattern dicts with keys:
            label, description, category, severity_score, frequency,
            example_game_ids, training_recommendation
    """
    existing_context = ""
    if existing_patterns:
        existing_context = f"""
The player already has these known patterns:

<existing_patterns>
{json.dumps(existing_patterns, indent=2)}
</existing_patterns>

Update existing patterns if new data changes their severity or frequency.
Identify any new patterns not covered above.
Mark patterns as resolved if they no longer appear in recent games.
"""

    user_prompt = f"""You are analyzing a player's mistake history across multiple games.

Here is a summary of all mistakes from {len(game_mistakes)} analyzed games.
Each entry includes the position (FEN), move played, engine's best move,
eval drop, game phase, and positional theme scores.

<game_mistakes>
{json.dumps(game_mistakes, indent=2)}
</game_mistakes>
{existing_context}
Tasks:
1. Identify recurring PATTERNS of mistakes. Group similar errors together.
2. For each pattern, provide:
   - label: A short name (5-8 words)
   - description: Detailed explanation of the weakness
   - category: tactical | positional | endgame | opening | time_mgmt
   - frequency: How many mistakes fit this pattern
   - severity_score: 0-100 based on frequency x avg eval loss
   - example_game_ids: 2-3 specific game references
   - training_recommendation: Concrete practice advice
3. Rank patterns from most to least severe.

Respond in JSON format: {{ "patterns": [...] }}"""

    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=8192,
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    try:
        response_text = message.content[0].text
        parsed = json.loads(response_text)
        return parsed.get("patterns", [])
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error("Failed to parse Claude synthesis response: %s", e)
        return []


async def compare_new_game(
    new_game_mistakes: list[dict],
    known_patterns: list[dict],
) -> dict:
    """Compare a new game's mistakes against known patterns.

    Returns:
        Dict with matched_patterns, new_patterns, and delta_summary.
    """
    user_prompt = f"""You are analyzing a new chess game against a player's known weakness patterns.

Known patterns:
<patterns>
{json.dumps(known_patterns, indent=2)}
</patterns>

Mistakes from the new game:
<new_mistakes>
{json.dumps(new_game_mistakes, indent=2)}
</new_mistakes>

Tasks:
1. Match each mistake to a known pattern (if applicable).
2. Identify any mistakes that don't fit existing patterns (potential new patterns).
3. For matched patterns, note if this instance is better or worse than the player's average.

Respond in JSON:
{{
  "matched_patterns": [{{ "pattern_label": "...", "mistake_ply": N, "notes": "..." }}],
  "new_patterns": [{{ "label": "...", "description": "...", "category": "...", "mistakes": [...] }}],
  "delta_summary": "Brief overall assessment of improvement or regression"
}}"""

    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=ANNOTATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    try:
        response_text = message.content[0].text
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error("Failed to parse Claude comparison response: %s", e)
        return {"matched_patterns": [], "new_patterns": [], "delta_summary": ""}
