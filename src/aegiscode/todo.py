from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class TodoItem:
    id: str
    content: str
    status: str = "open"
    priority: str = "normal"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)


class TodoStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self, status: str | None = None) -> list[TodoItem]:
        items = self._load()
        if status is None:
            return items
        return [item for item in items if item.status == status]

    def add(self, content: str, priority: str = "normal", data: dict[str, Any] | None = None) -> TodoItem:
        items = self._load()
        item = TodoItem(id=str(uuid4()), content=content, priority=priority, data=data or {})
        items.append(item)
        self._save(items)
        return item

    def update(self, item_id: str, *, status: str | None = None, content: str | None = None, priority: str | None = None) -> TodoItem:
        items = self._load()
        for item in items:
            if item.id == item_id:
                if status is not None:
                    item.status = status
                if content is not None:
                    item.content = content
                if priority is not None:
                    item.priority = priority
                item.updated_at = time.time()
                self._save(items)
                return item
        raise KeyError(item_id)

    def remove(self, item_id: str) -> TodoItem:
        items = self._load()
        kept: list[TodoItem] = []
        removed: TodoItem | None = None
        for item in items:
            if item.id == item_id:
                removed = item
            else:
                kept.append(item)
        if removed is None:
            raise KeyError(item_id)
        self._save(kept)
        return removed

    def _load(self) -> list[TodoItem]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [TodoItem(**item) for item in raw]

    def _save(self, items: list[TodoItem]) -> None:
        self.path.write_text(json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2), encoding="utf-8")
