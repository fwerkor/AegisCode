from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from .actions import Action

@dataclass
class GuardDecision:
    allowed: bool
    needs_approval: bool = False
    reasons: list[str] = field(default_factory=list)

class GuardrailEngine:
    """Deterministic governance layer for coding actions."""
    dangerous_patterns = [
        re.compile(r"external-deploy"),
        re.compile(r"\b(pip|npm|cargo)\s+publish\b"),
        re.compile(r"\bterraform\s+apply\b"),
        re.compile(r"\b(kubectl|helm)\s+.*\b(delete|apply)\b"),
        re.compile(r"\bmkfs(?:\.|\s)"),
        re.compile(r"\bdd\s+.*\bof=/dev/"),
    ]
    def __init__(self, workspace: Path, require_approval: bool = True):
        self.workspace = workspace.resolve()
        self.require_approval = require_approval
    def check(self, action: Action, approved: bool = False) -> GuardDecision:
        reasons: list[str] = []
        if action.type in {"write_file", "read_file", "delete_file"}:
            path = Path(str(action.params.get("path", "")))
            target = path.resolve() if path.is_absolute() else (self.workspace / path).resolve()
            if self.workspace not in [target, *target.parents]:
                return GuardDecision(False, False, [f"path escapes workspace: {path}"])
        if action.type == "shell":
            command = str(action.params.get("command", ""))
            for pattern in self.dangerous_patterns:
                if pattern.search(command):
                    reasons.append(f"dangerous command pattern: {pattern.pattern}")
        if action.type == "delete_file":
            reasons.append("delete_file requires human approval")
        if reasons and self.require_approval and not approved:
            return GuardDecision(False, True, reasons)
        return GuardDecision(True, False, reasons)
