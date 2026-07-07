from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .actions import Action
from .policy import ShellPolicy
from .registry import ToolRegistry

COMMAND_PARAMS = {
    "shell": "command",
    "test": "command",
    "job_start": "command",
    "shell_session_start": "command",
    "shell_session_send": "input",
}

@dataclass
class GuardDecision:
    allowed: bool
    needs_approval: bool = False
    reasons: list[str] = field(default_factory=list)

class GuardrailEngine:
    """Deterministic governance layer for coding actions."""
    def __init__(self, workspace: Path, require_approval: bool = True, shell_policy: ShellPolicy | None = None, registry: ToolRegistry | None = None):
        self.workspace = workspace.resolve()
        self.require_approval = require_approval
        self.shell_policy = shell_policy or ShellPolicy()
        self.registry = registry or ToolRegistry()

    def check(self, action: Action, approved: bool = False) -> GuardDecision:
        reasons: list[str] = []
        spec = self.registry.get(action.type)
        if spec is None:
            return GuardDecision(False, False, [f"unknown action: {action.type}"])
        if "path" in action.params:
            path = Path(str(action.params.get("path", "")))
            target = path.resolve() if path.is_absolute() else (self.workspace / path).resolve()
            if self.workspace not in [target, *target.parents]:
                return GuardDecision(False, False, [f"path escapes workspace: {path}"])
        command_param = COMMAND_PARAMS.get(action.type)
        if command_param is not None:
            decision = self.shell_policy.check(str(action.params.get(command_param, "")))
            if not decision.allowed and not decision.needs_approval:
                return GuardDecision(False, False, decision.reasons)
            reasons.extend(decision.reasons)
        if spec.requires_approval:
            reasons.append(f"{action.type} requires human approval")
        if reasons and self.require_approval and not approved:
            return GuardDecision(False, True, reasons)
        return GuardDecision(True, False, reasons)
