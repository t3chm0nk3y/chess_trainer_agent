"""Registry loader — parse patterns.yaml and provide lookup functions."""

import logging
from pathlib import Path

import yaml

import config

logger = logging.getLogger(__name__)

_registry_cache: dict | None = None


def load_registry(path: str | None = None) -> dict:
    """Load and cache the pattern registry YAML.

    Returns the full parsed dict with keys: registry_version, last_updated, patterns.
    """
    global _registry_cache

    if path is None:
        path = config.REGISTRY_PATH

    registry_path = Path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Registry not found: {registry_path}")

    with open(registry_path) as f:
        data = yaml.safe_load(f)

    _registry_cache = data
    logger.info(
        "Loaded registry v%s with %d patterns",
        data.get("registry_version"),
        len(data.get("patterns", [])),
    )
    return data


def get_registry() -> dict:
    """Get the cached registry, loading if needed."""
    if _registry_cache is None:
        return load_registry()
    return _registry_cache


def get_registry_version() -> str:
    """Return the current registry version string."""
    return get_registry().get("registry_version", "unknown")


def get_active_patterns(
    exclude_axes: set[str] | None = None,
) -> list[dict]:
    """Return all active patterns, optionally excluding certain axes.

    Args:
        exclude_axes: Set of axis values to exclude (e.g. {"game_condition", "opening_line"})
    """
    registry = get_registry()
    patterns = registry.get("patterns", [])
    exclude = exclude_axes or set()
    return [
        p for p in patterns
        if p.get("active", True) and p.get("axis") not in exclude
    ]


def get_candidate_patterns_for_move(phase: str, cp_loss: float) -> list[dict]:
    """Get patterns that could apply to a move based on phase and cp_loss.

    Returns patterns where:
    - active is True
    - axis is not game_condition or opening_line
    - phase matches or is "all"
    - cp_loss >= cp_loss_min
    """
    patterns = get_active_patterns(exclude_axes={"game_condition", "opening_line"})
    return [
        p for p in patterns
        if (p["phase"] == phase or p["phase"] == "all")
        and cp_loss >= p.get("cp_loss_min", 0)
    ]


def reload_registry() -> dict:
    """Force reload the registry from disk."""
    global _registry_cache
    _registry_cache = None
    return load_registry()
