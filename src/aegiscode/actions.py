from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class Action:
    type: str
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class Observation:
    source: str
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    def to_prompt_text(self) -> str:
        status = "OK" if self.success else "FAIL"
        details = f" data={self.data}" if self.data else ""
        return f"[{status}] {self.source}: {self.message}{details}"

@dataclass
class RunResult:
    completed: bool
    stopped_reason: str
    steps: int
    observations: list[Observation]
    final_summary: str | None = None
