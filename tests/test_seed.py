"""Tests for database seeding."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import MistakeCategory
from backend.seed import seed_mistake_categories


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_seed_creates_categories():
    db = _make_db()
    seed_mistake_categories(db)

    top_level = db.query(MistakeCategory).filter(MistakeCategory.parent_id.is_(None)).all()
    assert len(top_level) == 2
    names = {c.name for c in top_level}
    assert "tactical" in names
    assert "strategic" in names
    db.close()


def test_seed_creates_children():
    db = _make_db()
    seed_mistake_categories(db)

    tactical = db.query(MistakeCategory).filter(MistakeCategory.name == "tactical").first()
    assert len(tactical.children) == 4

    child_names = {c.name for c in tactical.children}
    assert "missed_tactic" in child_names
    assert "hung_piece" in child_names
    db.close()


def test_seed_idempotent():
    db = _make_db()
    seed_mistake_categories(db)
    count_after_first = db.query(MistakeCategory).count()

    seed_mistake_categories(db)
    count_after_second = db.query(MistakeCategory).count()

    assert count_after_first == count_after_second
    db.close()
