from __future__ import annotations
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AgentConfig:
    max_steps: int = 8
    workspace: Path = Path(".work")
    stop_on_approval_required: bool = True

@dataclass
class FeedbackConfig:
    commands: list[str] = field(default_factory=list)
    run_after_actions: list[str] = field(default_factory=lambda: ["write_file", "shell", "test"])

@dataclass
class MemoryConfig:
    path: Path = Path(".aegis/memory.json")
    max_results: int = 5

@dataclass
class GuardrailConfig:
    require_approval: bool = True

@dataclass
class HarnessConfig:
    agent: AgentConfig = field(default_factory=AgentConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    guardrails: GuardrailConfig = field(default_factory=GuardrailConfig)

    @classmethod
    def from_file(cls, path: Path) -> "HarnessConfig":
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        cfg = cls()
        agent = raw.get("agent", {})
        cfg.agent.max_steps = int(agent.get("max_steps", cfg.agent.max_steps))
        cfg.agent.workspace = Path(agent.get("workspace", str(cfg.agent.workspace)))
        cfg.agent.stop_on_approval_required = bool(agent.get("stop_on_approval_required", cfg.agent.stop_on_approval_required))
        feedback = raw.get("feedback", {})
        cfg.feedback.commands = list(feedback.get("commands", cfg.feedback.commands))
        cfg.feedback.run_after_actions = list(feedback.get("run_after_actions", cfg.feedback.run_after_actions))
        memory = raw.get("memory", {})
        cfg.memory.path = Path(memory.get("path", str(cfg.memory.path)))
        cfg.memory.max_results = int(memory.get("max_results", cfg.memory.max_results))
        guard = raw.get("guardrails", {})
        cfg.guardrails.require_approval = bool(guard.get("require_approval", cfg.guardrails.require_approval))
        return cfg
