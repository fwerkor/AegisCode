from __future__ import annotations
import re
from dataclasses import dataclass, field

@dataclass
class PolicyDecision:
    allowed: bool
    needs_approval: bool = False
    reasons: list[str] = field(default_factory=list)

@dataclass
class ShellPolicy:
    allow_prefixes: list[str] = field(default_factory=list)
    approval_patterns: list[str] = field(default_factory=lambda: [
        r"external-deploy",
        r"release-prod",
        r"cloud-admin",
    ])
    deny_patterns: list[str] = field(default_factory=list)
    max_command_chars: int = 400

    def check(self, command: str) -> PolicyDecision:
        if len(command) > self.max_command_chars:
            return PolicyDecision(False, False, ["shell command exceeds configured length limit"])
        if self.allow_prefixes and not any(command.strip().startswith(prefix) for prefix in self.allow_prefixes):
            return PolicyDecision(False, False, ["shell command does not match any allowed prefix"])
        reasons: list[str] = []
        for pattern in self.deny_patterns:
            if re.search(pattern, command):
                return PolicyDecision(False, False, [f"deny pattern matched: {pattern}"])
        for pattern in self.approval_patterns:
            if re.search(pattern, command):
                reasons.append(f"approval pattern matched: {pattern}")
        if reasons:
            return PolicyDecision(False, True, reasons)
        return PolicyDecision(True, False, [])
