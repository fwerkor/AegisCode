from __future__ import annotations
import json, zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from time import time
from uuid import uuid4

@dataclass
class SnapshotRecord:
    id: str
    archive: str
    created_at: float
    reason: str

class SnapshotStore:
    """Workspace snapshot/restore support for reversible agent changes."""
    def __init__(self, workspace: Path, path: Path):
        self.workspace = workspace.resolve()
        self.path = path if path.is_absolute() else self.workspace / path
        self.path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.path / "index.json"

    def create(self, reason: str = "manual") -> SnapshotRecord:
        snap_id = str(uuid4())
        archive = self.path / f"{snap_id}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in self.workspace.rglob("*"):
                if not file.is_file() or file.is_symlink():
                    continue
                if self.path in [file, *file.parents]:
                    continue
                if ".git" in file.parts:
                    continue
                resolved = file.resolve()
                if self.workspace not in [resolved, *resolved.parents]:
                    continue
                rel = file.relative_to(self.workspace)
                zf.write(file, rel.as_posix())
        record = SnapshotRecord(id=snap_id, archive=str(archive), created_at=time(), reason=reason)
        records = self._load()
        records.append(record)
        self._save(records)
        return record

    def list(self) -> list[SnapshotRecord]:
        return self._load()

    def restore(self, snap_id: str) -> SnapshotRecord:
        record = next((item for item in self._load() if item.id == snap_id), None)
        if record is None:
            raise KeyError(snap_id)
        with zipfile.ZipFile(record.archive, "r") as zf:
            members = [name for name in zf.namelist() if name and not name.endswith("/")]
            member_paths = {Path(name) for name in members}
            self._remove_files_not_in(member_paths)
            for name in members:
                target = (self.workspace / name).resolve()
                if self.workspace not in [target, *target.parents]:
                    raise ValueError(f"snapshot member escapes workspace: {name}")
            zf.extractall(self.workspace, members)
        return record

    def _remove_files_not_in(self, keep: set[Path]) -> None:
        for file in sorted(self.workspace.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if self.path in [file, *file.parents] or ".git" in file.parts:
                continue
            rel = file.relative_to(self.workspace)
            if file.is_file() or file.is_symlink():
                if rel not in keep:
                    file.unlink()
            elif file.is_dir():
                try:
                    next(file.iterdir())
                except StopIteration:
                    file.rmdir()


    def _load(self) -> list[SnapshotRecord]:
        if not self.index_path.exists():
            return []
        return [SnapshotRecord(**item) for item in json.loads(self.index_path.read_text(encoding="utf-8"))]

    def _save(self, records: list[SnapshotRecord]) -> None:
        self.index_path.write_text(json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2), encoding="utf-8")
