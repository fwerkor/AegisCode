from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .actions import Observation, RunResult
from .config import HarnessConfig
from .feedback import FeedbackSensor
from .guardrails import GuardrailEngine
from .llm import LLMClient
from .memory import JsonMemoryStore
from .parser import ActionParseError, parse_action
from .tools import ToolDispatcher

SYSTEM_PROMPT = """You are running inside Aegis Code Harness.
Return exactly one JSON object each turn:
{"action":{"type":"write_file|read_file|shell|test|remember|finish","path":"...","content":"...","command":"...","summary":"..."}}
The harness, not the prompt, enforces workspace boundaries, dangerous-action approval, feedback collection, and memory retrieval.
"""

@dataclass
class AgentLoop:
    llm: LLMClient
    config: HarnessConfig
    workspace: Path
    approved_action_ids: set[int] = field(default_factory=set)
    def __post_init__(self) -> None:
        self.workspace = self.workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.tools = ToolDispatcher(self.workspace)
        self.guardrails = GuardrailEngine(self.workspace, self.config.guardrails.require_approval)
        self.feedback = FeedbackSensor(self.workspace, self.config.feedback.commands)
        mem_path = self.config.memory.path if self.config.memory.path.is_absolute() else self.workspace / self.config.memory.path
        self.memory = JsonMemoryStore(mem_path)
    def run(self, task: str) -> RunResult:
        observations: list[Observation] = []
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}\nRelevant memory:\n{self.memory.context_block(task, self.config.memory.max_results)}"},
        ]
        for step in range(1, self.config.agent.max_steps + 1):
            try:
                action = parse_action(self.llm.complete(messages))
            except ActionParseError as exc:
                obs = Observation("parser", False, str(exc))
                observations.append(obs)
                messages.append({"role":"user", "content": obs.to_prompt_text()})
                continue
            decision = self.guardrails.check(action, approved=id(action) in self.approved_action_ids)
            if not decision.allowed:
                obs = Observation("guardrail", False, "; ".join(decision.reasons), {"needs_approval": decision.needs_approval, "action": action.type})
                observations.append(obs)
                if decision.needs_approval and self.config.agent.stop_on_approval_required:
                    return RunResult(False, "approval_required", step, observations)
                messages.append({"role":"user", "content": obs.to_prompt_text()})
                continue
            obs = self.tools.dispatch(action)
            observations.append(obs)
            if action.type == "remember" and obs.success:
                self.memory.add(str(action.params.get("text", "")), list(action.params.get("tags", [])))
            if action.type in self.config.feedback.run_after_actions:
                observations.extend(self.feedback.collect())
            if action.type == "finish":
                return RunResult(True, "finished", step, observations, obs.message)
            feedback_text = "\n".join(o.to_prompt_text() for o in observations[-4:])
            messages.append({"role":"user", "content": feedback_text})
        return RunResult(False, "max_steps", self.config.agent.max_steps, observations)
