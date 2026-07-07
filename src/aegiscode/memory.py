from __future__ import annotations
import json, time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

@dataclass
class MemoryRecord:
    id: str
    text: str
    tags: list[str]
    created_at: float

class JsonMemoryStore:
    """Framework-free lexical memory store with deterministic retrieval."""
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def _load(self) -> list[MemoryRecord]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [MemoryRecord(**item) for item in raw]
    def _save(self, records: list[MemoryRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([r.__dict__ for r in records], ensure_ascii=False, indent=2), encoding="utf-8")
    def add(self, text: str, tags: list[str] | None = None) -> MemoryRecord:
        records = self._load()
        rec = MemoryRecord(id=str(uuid4()), text=text, tags=tags or [], created_at=time.time())
        records.append(rec)
        self._save(records)
        return rec
    def search(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        tokens = {t.lower() for t in query.replace('_', ' ').replace('-', ' ').split() if t.strip()}
        scored: list[tuple[int, MemoryRecord]] = []
        for rec in self._load():
            hay = set(rec.text.lower().replace('_',' ').replace('-',' ').split()) | {t.lower() for t in rec.tags}
            score = len(tokens & hay)
            if score:
                scored.append((score, rec))
        scored.sort(key=lambda it: (-it[0], -it[1].created_at))
        return [rec for _, rec in scored[:limit]]
    def context_block(self, query: str, limit: int = 5) -> str:
        found = self.search(query, limit)
        if not found:
            return "No relevant memory."
        return "\n".join(f"- ({','.join(r.tags) or 'untagged'}) {r.text}" for r in found)
