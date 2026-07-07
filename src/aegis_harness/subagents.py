from __future__ import annotations
import json, time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any
from uuid import uuid4
from .actions import RunResult
from .agent import AgentLoop
from .config import HarnessConfig
from .llm import LLMClient

@dataclass
class SubagentSpec:
    name: str
    role: str
    system_hint: str = ""
    max_steps: int | None = None
    labels: list[str] = field(default_factory=list)

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

class SubagentStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_specs(self) -> dict[str, SubagentSpec]:
        raw = self._raw().get("specs", {})
        return {name: SubagentSpec(**spec) for name, spec in raw.items()}

    def save_specs(self, specs: dict[str, SubagentSpec]) -> None:
        raw = self._raw()
        raw["specs"] = {name: asdict(spec) for name, spec in specs.items()}
        self._save(raw)

    def load_tasks(self) -> list[SubagentTask]:
        return [SubagentTask(**item) for item in self._raw().get("tasks", [])]

    def save_tasks(self, tasks: list[SubagentTask]) -> None:
        raw = self._raw()
        raw["tasks"] = [asdict(task) for task in tasks]
        self._save(raw)

    def _raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"specs": {}, "tasks": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, raw: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

class SubagentManager:
    """Durable subagent registry and deterministic worker runner.

    This does not reuse an external agent framework. Each subagent is just a
    named harness configuration plus an injected LLM client factory.
    """
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

    def submit(self, agent_name: str, task: str) -> SubagentTask:
        if agent_name not in self.store.load_specs():
            raise KeyError(agent_name)
        tasks = self.store.load_tasks()
        item = SubagentTask(id=str(uuid4()), agent_name=agent_name, task=task)
        tasks.append(item)
        self.store.save_tasks(tasks)
        return item

    def run_next(self) -> SubagentTask | None:
        tasks = self.store.load_tasks()
        pending = next((task for task in tasks if task.status == "queued"), None)
        if pending is None:
            return None
        pending.status = "running"
        pending.started_at = time.time()
        self.store.save_tasks(tasks)
        try:
            spec = self.store.load_specs()[pending.agent_name]
            cfg = self.config
            if spec.max_steps is not None:
                cfg.agent.max_steps = spec.max_steps
            llm: LLMClient = self.llm_factory(spec)
            run: RunResult = AgentLoop(llm, cfg, self.workspace / pending.agent_name).run(pending.task)
            pending.status = "completed" if run.completed else "stopped"
            pending.result = {"completed": run.completed, "stopped_reason": run.stopped_reason, "steps": run.steps, "observations": [asdict(obs) for obs in run.observations]}
        except Exception as exc:
            pending.status = "failed"
            pending.error = f"{type(exc).__name__}: {exc}"
        pending.finished_at = time.time()
        self.store.save_tasks(tasks)
        return pending

    def run_all_sequential(self) -> list[SubagentTask]:
        done = []
        while True:
            item = self.run_next()
            if item is None:
                return done
            done.append(item)
