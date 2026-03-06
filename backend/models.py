import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MistakeCategory(Base):
    __tablename__ = "mistake_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("mistake_categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detection_method: Mapped[str] = mapped_column(
        String, nullable=False, default="hybrid"
    )  # engine | ai | hybrid
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    children: Mapped[list["MistakeCategory"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped["MistakeCategory | None"] = relationship(
        back_populates="children", remote_side=[id]
    )


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    pgn: Mapped[str] = mapped_column(Text, nullable=False)
    white: Mapped[str] = mapped_column(String, nullable=False)
    black: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)  # "1-0", "0-1", "1/2-1/2"
    date_played: Mapped[date | None] = mapped_column(Date, nullable=True)
    opening_eco: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_name: Mapped[str | None] = mapped_column(String, nullable=True)
    player_color: Mapped[str] = mapped_column(String, nullable=False)  # "white" | "black"
    source: Mapped[str] = mapped_column(String, nullable=False)  # lichess|chesscom|pgn_upload
    source_id: Mapped[str | None] = mapped_column(String, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    analysis_status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending|analyzed|error

    moves: Mapped[list["Move"]] = relationship(back_populates="game", cascade="all, delete-orphan")


class Move(Base):
    __tablename__ = "moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), nullable=False)
    move_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ply: Mapped[int] = mapped_column(Integer, nullable=False)
    san: Mapped[str] = mapped_column(String, nullable=False)
    uci: Mapped[str] = mapped_column(String, nullable=False)
    fen_before: Mapped[str] = mapped_column(String, nullable=False)
    fen_after: Mapped[str] = mapped_column(String, nullable=False)
    engine_eval_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    engine_eval_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_move_uci: Mapped[str | None] = mapped_column(String, nullable=True)
    classification: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # best|good|inaccuracy|mistake|blunder
    phase: Mapped[str | None] = mapped_column(String, nullable=True)  # opening|middlegame|endgame
    mistake_type: Mapped[str | None] = mapped_column(String, nullable=True)  # tactical|strategic
    themes_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="moves")
    pattern_instances: Mapped[list["PatternInstance"]] = relationship(back_populates="move")


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    label: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String, nullable=False
    )  # tactical|positional|endgame|opening|time_mgmt
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("mistake_categories.id"), nullable=True
    )
    mistake_type: Mapped[str | None] = mapped_column(String, nullable=True)  # tactical|strategic
    severity_score: Mapped[float] = mapped_column(Float, default=0.0)
    frequency: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_seen: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    post_acknowledgment_count: Mapped[int] = mapped_column(Integer, default=0)
    example_game_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    training_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    mistake_category: Mapped["MistakeCategory | None"] = relationship()
    instances: Mapped[list["PatternInstance"]] = relationship(
        back_populates="pattern", cascade="all, delete-orphan"
    )
    acknowledgments: Mapped[list["PatternAcknowledgment"]] = relationship(
        back_populates="pattern", cascade="all, delete-orphan"
    )


class PatternInstance(Base):
    __tablename__ = "pattern_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pattern_id: Mapped[str] = mapped_column(String, ForeignKey("patterns.id"), nullable=False)
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), nullable=False)
    move_id: Mapped[int] = mapped_column(Integer, ForeignKey("moves.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pattern: Mapped["Pattern"] = relationship(back_populates="instances")
    move: Mapped["Move"] = relationship(back_populates="pattern_instances")


class PatternAcknowledgment(Base):
    __tablename__ = "pattern_acknowledgments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pattern_id: Mapped[str] = mapped_column(String, ForeignKey("patterns.id"), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    player_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    pattern: Mapped["Pattern"] = relationship(back_populates="acknowledgments")


class OpeningStats(Base):
    __tablename__ = "opening_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eco_code: Mapped[str] = mapped_column(String, nullable=False)
    opening_name: Mapped[str] = mapped_column(String, nullable=False)
    variation_name: Mapped[str | None] = mapped_column(String, nullable=True)
    move_sequence: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of SAN moves
    total_games: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    avg_cp_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    divergence_move: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProgressSnapshot(Base):
    __tablename__ = "progress_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_games: Mapped[int] = mapped_column(Integer, default=0)
    avg_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy_opening: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_middlegame: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_endgame: Mapped[float | None] = mapped_column(Float, nullable=True)
    acknowledged_patterns: Mapped[int] = mapped_column(Integer, default=0)
    recurring_patterns: Mapped[int] = mapped_column(Integer, default=0)
    resolved_patterns: Mapped[int] = mapped_column(Integer, default=0)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    patterns_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    workflow_name: Mapped[str] = mapped_column(String, nullable=False)
    parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")  # running|completed|failed
    step_results_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
