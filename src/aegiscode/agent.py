from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .actions import Observation, RunResult
from .approvals import ApprovalQueue
from .audit import AuditLog
from .config import HarnessConfig
from .feedback import FeedbackSensor
from .guardrails import GuardrailEngine
from .llm import LLMClient
from .memory import JsonMemoryStore
from .parser import ActionParseError, parse_action
from .policy import ShellPolicy
from .registry import ToolRegistry
from .snapshots import SnapshotStore
from .tools import ToolDispatcher

SYSTEM_PROMPT = """You are running inside AegisCode.
Return exactly one JSON object each turn, shaped as {{"action":{{"type":"..."}}}}.
AegisCode owns the loop, workspace boundaries, deterministic guardrails, feedback, audit logging, snapshots, approvals, memory, and subagent orchestration.
Available actions:
{tools}
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
        self.registry = ToolRegistry()
        shell_policy = ShellPolicy(
            allow_prefixes=self.config.shell_policy.allow_prefixes,
            approval_patterns=self.config.shell_policy.approval_patterns,
            deny_patterns=self.config.shell_policy.deny_patterns,
            max_command_chars=self.config.shell_policy.max_command_chars,
        )
        self.guardrails = GuardrailEngine(self.workspace, self.config.guardrails.require_approval, shell_policy=shell_policy, registry=self.registry)
        self.feedback = FeedbackSensor(self.workspace, self.config.feedback.commands)
        self.audit = AuditLog(self._state_path(self.config.governance.audit_path))
        self.approvals = ApprovalQueue(self._state_path(self.config.governance.approvals_path))
        self.snapshots = SnapshotStore(self.workspace, self.config.governance.snapshot_dir)
        self.tools = ToolDispatcher(
            self.workspace,
            audit=self.audit,
            snapshots=self.snapshots,
            snapshot_before_mutation=self.config.governance.snapshot_before_mutation,
        )
        mem_path = self._state_path(self.config.memory.path)
        self.memory = JsonMemoryStore(mem_path)

    def _state_path(self, path: Path) -> Path:
        return path if path.is_absolute() else self.workspace / path

    def run(self, task: str) -> RunResult:
        observations: list[Observation] = []
        self.audit.append("run.start", "started run", {"task": task})
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(tools=self.registry.prompt_block())},
            {"role": "user", "content": f"Task: {task}\nRelevant memory:\n{self.memory.context_block(task, self.config.memory.max_results)}"},
        ]
        for step in range(1, self.config.agent.max_steps + 1):
            try:
                action = parse_action(self.llm.complete(messages))
            except ActionParseError as exc:
                obs = Observation("parser", False, str(exc))
                observations.append(obs)
                self.audit.append("parser.error", str(exc), {"step": step})
                messages.append({"role": "user", "content": obs.to_prompt_text()})
                continue
            decision = self.guardrails.check(action, approved=id(action) in self.approved_action_ids)
            if not decision.allowed:
                data = {"needs_approval": decision.needs_approval, "action": action.type, "reasons": decision.reasons}
                if decision.needs_approval:
                    record = self.approvals.submit(action, decision.reasons)
                    data["approval_id"] = record.id
                    self.audit.append("approval.pending", "queued approval", {"approval": asdict(record)})
                obs = Observation("guardrail", False, "; ".join(decision.reasons), data)
                observations.append(obs)
                if decision.needs_approval and self.config.agent.stop_on_approval_required:
                    self.audit.append("run.stop", "approval required", {"step": step, "action": action.type})
                    return RunResult(False, "approval_required", step, observations)
                messages.append({"role": "user", "content": obs.to_prompt_text()})
                continue
            obs = self.tools.dispatch(action)
            observations.append(obs)
            if action.type == "remember" and obs.success:
                self.memory.add(str(action.params.get("text", "")), list(action.params.get("tags", [])))
            if action.type in self.config.feedback.run_after_actions:
                observations.extend(self.feedback.collect())
            if action.type == "finish":
                self.audit.append("run.finish", "finished run", {"step": step, "summary": obs.message})
                return RunResult(True, "finished", step, observations, obs.message)
            feedback_text = "\n".join(o.to_prompt_text() for o in observations[-4:])
            messages.append({"role": "user", "content": feedback_text})
        self.audit.append("run.stop", "max steps reached", {"steps": self.config.agent.max_steps})
        return RunResult(False, "max_steps", self.config.agent.max_steps, observations)
