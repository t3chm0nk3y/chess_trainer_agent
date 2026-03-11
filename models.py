"""All ORM models — single file."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lichess_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    pgn: Mapped[str] = mapped_column(Text, nullable=False)
    player_color: Mapped[str] = mapped_column(String, nullable=False)
    opponent_username: Mapped[str | None] = mapped_column(String, nullable=True)
    result: Mapped[str] = mapped_column(String, nullable=False)
    played_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    eco_code: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_name: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_name: Mapped[str | None] = mapped_column(String, nullable=True)
    time_control: Mapped[str | None] = mapped_column(String, nullable=True)
    total_moves: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Engine layer status
    engine_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    engine_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    engine_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engine_next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Annotation layer status
    annotation_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    annotation_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Condition layer status
    condition_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    condition_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Registry tracking
    registry_version_at_last_scan: Mapped[str | None] = mapped_column(String, nullable=True)
    has_unscanned_patterns: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships
    moves: Mapped[list["Move"]] = relationship(back_populates="game", cascade="all, delete-orphan")
    conditions: Mapped[list["GameCondition"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )


class Move(Base):
    __tablename__ = "moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    move_number: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)
    san: Mapped[str] = mapped_column(String, nullable=False)
    fen_before: Mapped[str] = mapped_column(String, nullable=False)
    fen_after: Mapped[str] = mapped_column(String, nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False)

    # Engine fields — immutable after engine_status = complete
    cp_eval_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    cp_eval_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    cp_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_move_san: Mapped[str | None] = mapped_column(String, nullable=True)
    mistake_severity: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    game: Mapped["Game"] = relationship(back_populates="moves")
    pattern_matches: Mapped[list["MovePatternMatch"]] = relationship(
        back_populates="move", cascade="all, delete-orphan"
    )


class MovePatternMatch(Base):
    __tablename__ = "move_pattern_matches"
    __table_args__ = (
        UniqueConstraint("move_id", "registry_pattern_id", name="uq_move_pattern"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    move_id: Mapped[int] = mapped_column(Integer, ForeignKey("moves.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    registry_pattern_id: Mapped[str] = mapped_column(String, nullable=False)
    annotation: Mapped[str] = mapped_column(Text, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    registry_version_at_match: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    move: Mapped["Move"] = relationship(back_populates="pattern_matches")


class PatternScanLog(Base):
    __tablename__ = "pattern_scan_log"
    __table_args__ = (
        UniqueConstraint("game_id", "registry_pattern_id", name="uq_game_pattern_scan"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    registry_pattern_id: Mapped[str] = mapped_column(String, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    result: Mapped[str] = mapped_column(String, nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    registry_pattern_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False)
    axis: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_affected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    first_seen_game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id"), nullable=False
    )
    last_seen_game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id"), nullable=False
    )
    example_fen: Mapped[str | None] = mapped_column(String, nullable=True)
    example_annotation: Mapped[str | None] = mapped_column(Text, nullable=True)


class GameCondition(Base):
    __tablename__ = "game_conditions"
    __table_args__ = (
        UniqueConstraint("game_id", "registry_pattern_id", name="uq_game_condition"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    registry_pattern_id: Mapped[str] = mapped_column(String, nullable=False)
    condition_name: Mapped[str] = mapped_column(String, nullable=False)
    detected_at_move: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_was_worse: Mapped[bool] = mapped_column(Boolean, nullable=False)
    game_result: Mapped[str] = mapped_column(String, nullable=False)
    context_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    game: Mapped["Game"] = relationship(back_populates="conditions")


class OpeningStats(Base):
    __tablename__ = "opening_stats"
    __table_args__ = (
        UniqueConstraint(
            "eco_code", "opening_name", "variation_name", name="uq_opening_line"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eco_code: Mapped[str] = mapped_column(String, nullable=False)
    opening_name: Mapped[str] = mapped_column(String, nullable=False)
    variation_name: Mapped[str | None] = mapped_column(String, nullable=True)
    total_games: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    loss_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_cp_loss_opening: Mapped[float | None] = mapped_column(Float, nullable=True)
    divergence_move: Mapped[int | None] = mapped_column(Integer, nullable=True)
    divergence_san: Mapped[str | None] = mapped_column(String, nullable=True)
    last_computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("report_type", "report_key", name="uq_report_type_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    report_key: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_coverage: Mapped[str | None] = mapped_column(String, nullable=True)
