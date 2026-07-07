from __future__ import annotations
import subprocess
from pathlib import Path
from .actions import Action, Observation

class ToolDispatcher:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
    def _safe_path(self, raw: str) -> Path:
        path = Path(raw)
        target = path.resolve() if path.is_absolute() else (self.workspace / path).resolve()
        if self.workspace not in [target, *target.parents]:
            raise ValueError(f"path escapes workspace: {raw}")
        return target
    def dispatch(self, action: Action) -> Observation:
        try:
            if action.type == "read_file":
                path = self._safe_path(str(action.params["path"]))
                return Observation("tool.read_file", True, path.read_text(encoding="utf-8"), {"path": str(path)})
            if action.type == "write_file":
                path = self._safe_path(str(action.params["path"]))
                path.parent.mkdir(parents=True, exist_ok=True)
                content = str(action.params.get("content", ""))
                path.write_text(content, encoding="utf-8")
                return Observation("tool.write_file", True, f"wrote {path.relative_to(self.workspace)}", {"bytes": len(content.encode())})
            if action.type == "delete_file":
                path = self._safe_path(str(action.params["path"]))
                path.unlink()
                return Observation("tool.delete_file", True, f"deleted {path.relative_to(self.workspace)}")
            if action.type == "shell":
                command = str(action.params["command"])
                proc = subprocess.run(command, cwd=self.workspace, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=int(action.params.get("timeout", 20)))
                return Observation("tool.shell", proc.returncode == 0, proc.stdout + proc.stderr, {"returncode": proc.returncode})
            if action.type == "test":
                command = str(action.params.get("command", "python -m pytest"))
                proc = subprocess.run(command, cwd=self.workspace, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=int(action.params.get("timeout", 60)))
                return Observation("tool.test", proc.returncode == 0, proc.stdout + proc.stderr, {"returncode": proc.returncode})
            if action.type == "remember":
                return Observation("tool.remember", True, str(action.params.get("text", "")), {"tags": action.params.get("tags", [])})
            if action.type == "finish":
                return Observation("tool.finish", True, str(action.params.get("summary", "finished")))
            return Observation("tool.unknown", False, f"unknown action: {action.type}")
        except Exception as exc:
            return Observation(f"tool.{action.type}", False, f"{type(exc).__name__}: {exc}")
