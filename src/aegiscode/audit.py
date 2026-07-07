from __future__ import annotations
import json, time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

SENSITIVE_KEYS = {"content", "api_key", "credential", "secret", "token", "password"}

@dataclass
class AuditEvent:
    id: str
    ts: float
    kind: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

class AuditLog:
    """Append-only JSONL audit log with basic redaction."""
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, kind: str, message: str, data: dict[str, Any] | None = None) -> AuditEvent:
        event = AuditEvent(id=str(uuid4()), ts=time.time(), kind=kind, message=message, data=self._redact(data or {}))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event

    def tail(self, limit: int = 50) -> list[AuditEvent]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [AuditEvent(**json.loads(line)) for line in lines if line.strip()]

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for key, item in value.items():
                if str(key).lower() in SENSITIVE_KEYS:
                    out[str(key)] = "<redacted>"
                else:
                    out[str(key)] = self._redact(item)
            return out
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        return value
