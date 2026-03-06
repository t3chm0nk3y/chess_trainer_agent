"""Storage layer for workflow definitions and runs."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import yaml

from workflow_mcp.models import Workflow, WorkflowRun

logger = logging.getLogger(__name__)

WORKFLOWS_DIR = Path(__file__).parent / "workflows"


class WorkflowStore:
    """In-memory store backed by YAML files for definitions and SQLite for runs."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._runs: dict[str, WorkflowRun] = {}

    def load_defaults(self) -> None:
        """Load all YAML workflow definitions from the workflows/ directory."""
        if not WORKFLOWS_DIR.exists():
            logger.warning("Workflows directory not found: %s", WORKFLOWS_DIR)
            return

        for yaml_file in WORKFLOWS_DIR.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                if data:
                    w = Workflow(
                        name=data["name"],
                        description=data["description"],
                        trigger=data.get("trigger", "manual"),
                        parameters=data.get("parameters", []),
                        steps=data.get("steps", []),
                        outputs=data.get("outputs", []),
                        version=data.get("version", 1),
                    )
                    self._workflows[w.name] = w
                    logger.info("Loaded workflow: %s (v%d)", w.name, w.version)
            except Exception as e:
                logger.error("Failed to load workflow %s: %s", yaml_file, e)

    def list_workflows(self) -> list[Workflow]:
        return list(self._workflows.values())

    def get_workflow(self, name: str) -> Workflow | None:
        return self._workflows.get(name)

    def save_workflow(self, workflow: Workflow) -> None:
        self._workflows[workflow.name] = workflow

    def create_run(self, workflow_name: str, params: dict) -> WorkflowRun:
        run = WorkflowRun(workflow_name=workflow_name, parameters=params)
        self._runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return self._runs.get(run_id)

    def update_step(self, run_id: str, step: int, result: dict) -> WorkflowRun | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        run.step_results.append({"step": step, "result": result})

        # Check if all steps are done
        workflow = self._workflows.get(run.workflow_name)
        if workflow and len(run.step_results) >= len(workflow.steps):
            run.status = "completed"
            run.completed_at = datetime.utcnow()

        return run

    def list_runs(self, workflow_name: str, limit: int = 10) -> list[WorkflowRun]:
        runs = [r for r in self._runs.values() if r.workflow_name == workflow_name]
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[:limit]
