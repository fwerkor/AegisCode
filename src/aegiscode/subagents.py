from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from .actions import RunResult
from .agent import AgentLoop
from .config import HarnessConfig
from .llm import LLMClient

DEFAULT_PIPELINE = ["planner", "implementer", "tester", "reviewer", "release"]


@dataclass
class SubagentSpec:
    name: str
    role: str
    system_hint: str = ""
    max_steps: int | None = None
    labels: list[str] = field(default_factory=list)
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    workspace: str = ""
    provider: str = ""
    model: str = ""
    priority: int = 0
    concurrency: int = 1
    handoff: str = ""
    default_next: str = ""


@dataclass
class SubagentTask:
    id: str
    agent_name: str
    task: str
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str = ""
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)
    parent_id: str | None = None
    attempts: int = 0
    max_attempts: int = 1
    artifacts: list[str] = field(default_factory=list)


class SubagentStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_specs(self) -> dict[str, SubagentSpec]:
        raw = self._raw().get("specs", {})
        return {name: SubagentSpec(**self._spec_defaults(spec)) for name, spec in raw.items()}

    def save_specs(self, specs: dict[str, SubagentSpec]) -> None:
        raw = self._raw()
        raw["specs"] = {name: asdict(spec) for name, spec in specs.items()}
        self._save(raw)

    def load_tasks(self) -> list[SubagentTask]:
        return [SubagentTask(**self._task_defaults(item)) for item in self._raw().get("tasks", [])]

    def save_tasks(self, tasks: list[SubagentTask]) -> None:
        raw = self._raw()
        raw["tasks"] = [asdict(task) for task in tasks]
        self._save(raw)

    def _raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"specs": {}, "tasks": [], "pipelines": {"default": DEFAULT_PIPELINE}}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        raw.setdefault("specs", {})
        raw.setdefault("tasks", [])
        raw.setdefault("pipelines", {"default": DEFAULT_PIPELINE})
        return raw

    def _save(self, raw: dict[str, Any]) -> None:
        raw.setdefault("pipelines", {"default": DEFAULT_PIPELINE})
        self.path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    def _spec_defaults(self, spec: dict[str, Any]) -> dict[str, Any]:
        out = dict(spec)
        for key, value in {
            "system_hint": "",
            "max_steps": None,
            "labels": [],
            "description": "",
            "capabilities": [],
            "workspace": "",
            "provider": "",
            "model": "",
            "priority": 0,
            "concurrency": 1,
            "handoff": "",
            "default_next": "",
        }.items():
            out.setdefault(key, value)
        return out

    def _task_defaults(self, task: dict[str, Any]) -> dict[str, Any]:
        out = dict(task)
        for key, value in {
            "priority": 0,
            "depends_on": [],
            "parent_id": None,
            "attempts": 0,
            "max_attempts": 1,
            "artifacts": [],
        }.items():
            out.setdefault(key, value)
        return out


class SubagentManager:
    """Durable subagent registry, queues, retries, dependencies, and default pipelines."""

    def __init__(self, store: SubagentStore, workspace: Path, config: HarnessConfig, llm_factory):
        self.store = store
        self.workspace = workspace
        self.config = config
        self.llm_factory = llm_factory

    def register(self, spec: SubagentSpec) -> SubagentSpec:
        specs = self.store.load_specs()
        specs[spec.name] = spec
        self.store.save_specs(specs)
        return spec

    def ensure_default_pipeline(self) -> dict[str, SubagentSpec]:
        specs = self.store.load_specs()
        defaults = {
            "planner": SubagentSpec("planner", "planning", description="Break a request into tasks and verification steps.", capabilities=["planning", "risk-analysis"], max_steps=6, priority=50, default_next="implementer", labels=["plan"]),
            "implementer": SubagentSpec("implementer", "implementation", description="Make focused source changes.", capabilities=["file", "shell", "git"], max_steps=10, priority=40, default_next="tester", labels=["code"]),
            "tester": SubagentSpec("tester", "verification", description="Run tests and classify failures.", capabilities=["shell", "job", "audit"], max_steps=8, priority=30, default_next="reviewer", labels=["test"]),
            "reviewer": SubagentSpec("reviewer", "review", description="Review implementation quality, safety, and spec compliance.", capabilities=["file", "grep", "audit"], max_steps=6, priority=20, default_next="release", labels=["review"]),
            "release": SubagentSpec("release", "release", description="Prepare release checks and artifacts.", capabilities=["git", "shell", "audit"], max_steps=6, priority=10, labels=["release"]),
        }
        changed = False
        for name, spec in defaults.items():
            if name not in specs:
                specs[name] = spec
                changed = True
        if changed:
            self.store.save_specs(specs)
        return specs

    def submit(self, agent_name: str, task: str, *, priority: int | None = None, depends_on: list[str] | None = None, parent_id: str | None = None, max_attempts: int = 1) -> SubagentTask:
        specs = self.store.load_specs()
        if agent_name not in specs:
            raise KeyError(agent_name)
        tasks = self.store.load_tasks()
        item = SubagentTask(
            id=str(uuid4()),
            agent_name=agent_name,
            task=task,
            priority=specs[agent_name].priority if priority is None else priority,
            depends_on=depends_on or [],
            parent_id=parent_id,
            max_attempts=max(1, max_attempts),
        )
        tasks.append(item)
        self.store.save_tasks(tasks)
        return item

    def show(self, task_id: str) -> SubagentTask:
        for task in self.store.load_tasks():
            if task.id == task_id:
                return task
        raise KeyError(task_id)

    def cancel(self, task_id: str) -> SubagentTask:
        tasks = self.store.load_tasks()
        for task in tasks:
            if task.id == task_id:
                if task.status not in {"completed", "failed", "cancelled"}:
                    task.status = "cancelled"
                    task.finished_at = time.time()
                self.store.save_tasks(tasks)
                return task
        raise KeyError(task_id)

    def retry(self, task_id: str) -> SubagentTask:
        tasks = self.store.load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.status = "queued"
                task.started_at = None
                task.finished_at = None
                task.error = ""
                task.result = None
                task.max_attempts = max(task.max_attempts, task.attempts + 1)
                self.store.save_tasks(tasks)
                return task
        raise KeyError(task_id)

    def queue_default_pipeline(self, task: str = "Run the default AegisCode pipeline") -> list[SubagentTask]:
        self.ensure_default_pipeline()
        created: list[SubagentTask] = []
        parent_id: str | None = None
        depends: list[str] = []
        for name in DEFAULT_PIPELINE:
            item = self.submit(name, f"{task}\nPipeline stage: {name}", depends_on=depends, parent_id=parent_id)
            created.append(item)
            parent_id = created[0].id
            depends = [item.id]
        return created

    def run_next(self, agent_name: str | None = None) -> SubagentTask | None:
        tasks = self.store.load_tasks()
        pending = self._select_next(tasks, agent_name)
        if pending is None:
            return None
        pending.status = "running"
        pending.started_at = time.time()
        pending.attempts += 1
        self.store.save_tasks(tasks)
        try:
            spec = self.store.load_specs()[pending.agent_name]
            cfg = self.config
            if spec.max_steps is not None:
                cfg.agent.max_steps = spec.max_steps
            llm: LLMClient = self.llm_factory(spec)
            workspace = self.workspace / (spec.workspace or pending.agent_name)
            run: RunResult = AgentLoop(llm, cfg, workspace).run(pending.task)
            pending.status = "completed" if run.completed else "stopped"
            pending.result = {"completed": run.completed, "stopped_reason": run.stopped_reason, "steps": run.steps, "observations": [asdict(obs) for obs in run.observations]}
            pending.artifacts = self._collect_artifacts(workspace)
        except Exception as exc:
            pending.status = "failed"
            pending.error = f"{type(exc).__name__}: {exc}"
            if pending.attempts < pending.max_attempts:
                pending.status = "queued"
        pending.finished_at = time.time() if pending.status != "queued" else None
        self.store.save_tasks(tasks)
        return pending

    def run_all_sequential(self, *, max_count: int | None = None, agent_name: str | None = None) -> list[SubagentTask]:
        done = []
        while max_count is None or len(done) < max_count:
            item = self.run_next(agent_name=agent_name)
            if item is None:
                return done
            done.append(item)
        return done

    def _select_next(self, tasks: list[SubagentTask], agent_name: str | None = None) -> SubagentTask | None:
        completed = {task.id for task in tasks if task.status == "completed"}
        candidates = [
            task for task in tasks
            if task.status == "queued"
            and (agent_name is None or task.agent_name == agent_name)
            and all(dep in completed for dep in task.depends_on)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (-item.priority, item.created_at))[0]

    def _collect_artifacts(self, workspace: Path) -> list[str]:
        if not workspace.exists():
            return []
        artifacts: list[str] = []
        for file in workspace.rglob("*"):
            if file.is_file() and ".aegiscode" not in file.parts and ".git" not in file.parts:
                artifacts.append(str(file.relative_to(workspace)))
                if len(artifacts) >= 100:
                    break
        return artifacts
