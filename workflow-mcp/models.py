"""Data models for the Workflow MCP."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WorkflowParameter:
    name: str
    type: str = "string"
    required: bool = True
    default: str | None = None


@dataclass
class WorkflowStep:
    number: int
    tool: str
    description: str
    input_map: dict = field(default_factory=dict)


@dataclass
class Workflow:
    name: str
    description: str
    trigger: str  # "manual" | "on_import" | "scheduled"
    parameters: list[dict]
    steps: list[dict]
    outputs: list[str] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger,
            "parameters": self.parameters,
            "steps": self.steps,
            "outputs": self.outputs,
            "version": self.version,
        }


@dataclass
class WorkflowRun:
    workflow_name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameters: dict = field(default_factory=dict)
    status: str = "running"  # "running" | "completed" | "failed"
    step_results: list[dict] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "parameters": self.parameters,
            "status": self.status,
            "step_results": self.step_results,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
