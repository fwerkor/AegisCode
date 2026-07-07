from __future__ import annotations
import json, time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4
from .actions import Action

@dataclass
class ApprovalRecord:
    id: str
    action_type: str
    params: dict[str, Any]
    reasons: list[str]
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    decided_at: float | None = None
    note: str = ""

class ApprovalQueue:
    """Durable HITL queue. The agent stops; a human can inspect and decide later."""
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def submit(self, action: Action, reasons: list[str]) -> ApprovalRecord:
        record = ApprovalRecord(id=str(uuid4()), action_type=action.type, params=dict(action.params), reasons=list(reasons))
        records = self._load()
        records.append(record)
        self._save(records)
        return record

    def list(self, status: str | None = None) -> list[ApprovalRecord]:
        records = self._load()
        if status is None:
            return records
        return [record for record in records if record.status == status]

    def decide(self, approval_id: str, approved: bool, note: str = "") -> ApprovalRecord:
        records = self._load()
        for record in records:
            if record.id == approval_id:
                if record.status != "pending":
                    raise ValueError(f"approval {approval_id} is already {record.status}")
                record.status = "approved" if approved else "rejected"
                record.decided_at = time.time()
                record.note = note
                self._save(records)
                return record
        raise KeyError(approval_id)

    def _load(self) -> list[ApprovalRecord]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [ApprovalRecord(**item) for item in raw]

    def _save(self, records: list[ApprovalRecord]) -> None:
        self.path.write_text(json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2), encoding="utf-8")
