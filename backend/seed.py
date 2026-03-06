"""Seed the database with initial mistake taxonomy."""

import logging

from sqlalchemy.orm import Session

from backend.models import MistakeCategory

logger = logging.getLogger(__name__)

# Initial two-axis taxonomy: Phase (axis 1) x Type (axis 2)
# Top-level categories are the phase, children are the mistake types within that phase.
INITIAL_TAXONOMY = [
    {
        "name": "tactical",
        "description": "Mistakes involving concrete calculation: missed tactics, hung pieces, "
        "failed combinations, missed forks/pins/skewers.",
        "detection_method": "engine",
        "children": [
            {
                "name": "missed_tactic",
                "description": (
                    "Failed to find a winning tactical sequence "
                    "available in the position."
                ),
                "detection_method": "engine",
            },
            {
                "name": "hung_piece",
                "description": (
                    "Left a piece undefended or moved it to a "
                    "square where it can be captured."
                ),
                "detection_method": "engine",
            },
            {
                "name": "failed_combination",
                "description": (
                    "Attempted a tactical combination that does "
                    "not work due to a missed defensive resource."
                ),
                "detection_method": "engine",
            },
            {
                "name": "missed_checkmate",
                "description": "Failed to see a checkmate or checkmate threat.",
                "detection_method": "engine",
            },
        ],
    },
    {
        "name": "strategic",
        "description": "Mistakes involving positional judgment: bad pawn structure, poor piece "
        "placement, weak square control, choosing the wrong plan.",
        "detection_method": "ai",
        "children": [
            {
                "name": "bad_pawn_structure",
                "description": (
                    "Created unnecessary pawn weaknesses "
                    "(doubled, isolated, backward pawns)."
                ),
                "detection_method": "ai",
            },
            {
                "name": "poor_piece_placement",
                "description": "Placed a piece on a passive or ineffective square.",
                "detection_method": "ai",
            },
            {
                "name": "wrong_plan",
                "description": "Chose a plan that does not suit the position's requirements.",
                "detection_method": "ai",
            },
            {
                "name": "weak_square_control",
                "description": "Failed to control or exploit key squares in the position.",
                "detection_method": "ai",
            },
        ],
    },
]


def seed_mistake_categories(db: Session) -> None:
    """Seed the MistakeCategory table if empty."""
    existing = db.query(MistakeCategory).count()
    if existing > 0:
        logger.info("Mistake categories already seeded (%d entries), skipping", existing)
        return

    logger.info("Seeding initial mistake categories...")
    for cat_data in INITIAL_TAXONOMY:
        parent = MistakeCategory(
            name=cat_data["name"],
            description=cat_data["description"],
            detection_method=cat_data["detection_method"],
        )
        db.add(parent)
        db.flush()

        for child_data in cat_data.get("children", []):
            child = MistakeCategory(
                parent_id=parent.id,
                name=child_data["name"],
                description=child_data["description"],
                detection_method=child_data["detection_method"],
            )
            db.add(child)

    db.commit()
    logger.info("Seeded %d top-level mistake categories", len(INITIAL_TAXONOMY))
