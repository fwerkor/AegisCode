from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class RuntimeRecord:
    id: str
    kind: str
    command: str
    name: str = ""
    pid: int | None = None
    tmux_session: str = ""
    log: str = ""
    cwd: str = ""
    status: str = "running"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    returncode: int | None = None
    data: dict[str, Any] = field(default_factory=dict)


class RuntimeStore:
    """Durable process/session metadata for cross-CLI runtime operations."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.records_dir = self.state_dir / "runtime"
        self.logs_dir = self.state_dir / "logs"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def start_job(self, command: str, cwd: Path, name: str = "") -> RuntimeRecord:
        rec_id = str(uuid4())
        log = self.logs_dir / f"{rec_id}.log"
        handle = log.open("ab", buffering=0)
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        rec = RuntimeRecord(
            id=rec_id,
            kind="job",
            command=command,
            name=name,
            pid=proc.pid,
            log=str(log),
            cwd=str(cwd),
            status="running",
        )
        self.save(rec)
        return rec

    def start_shell(self, command: str, cwd: Path, name: str = "") -> RuntimeRecord:
        rec_id = str(uuid4())
        log = self.logs_dir / f"{rec_id}.log"
        tmux = shutil.which("tmux")
        shell_cmd = command or os.environ.get("SHELL") or "/bin/sh"
        if tmux and os.name != "nt":
            session = f"aegiscode-{rec_id[:8]}"
            subprocess.run([tmux, "new-session", "-d", "-s", session, "-c", str(cwd), shell_cmd], check=True)
            # Pipe pane output to a durable log; -o avoids duplicate pipes if retried.
            subprocess.run([tmux, "pipe-pane", "-o", "-t", session, f"cat >> {str(log)!r}"], check=False)
            rec = RuntimeRecord(
                id=rec_id,
                kind="shell",
                command=shell_cmd,
                name=name,
                tmux_session=session,
                log=str(log),
                cwd=str(cwd),
                status="running",
            )
        else:
            # Windows ConPTY can be added later; this fallback still persists metadata.
            handle = log.open("ab", buffering=0)
            proc = subprocess.Popen(
                shell_cmd,
                cwd=cwd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=os.name != "nt",
                text=True,
            )
            rec = RuntimeRecord(
                id=rec_id,
                kind="shell",
                command=shell_cmd,
                name=name,
                pid=proc.pid,
                log=str(log),
                cwd=str(cwd),
                status="running",
                data={"interactive_send_supported": False},
            )
        self.save(rec)
        return rec

    def list(self, kind: str | None = None) -> list[RuntimeRecord]:
        records: list[RuntimeRecord] = []
        for path in sorted(self.records_dir.glob("*.json")):
            try:
                rec = RuntimeRecord(**json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            if kind and rec.kind != kind:
                continue
            records.append(self.refresh(rec))
        return records

    def get(self, rec_id: str) -> RuntimeRecord:
        path = self.records_dir / f"{rec_id}.json"
        if not path.exists():
            matches = list(self.records_dir.glob(f"{rec_id}*.json"))
            if len(matches) == 1:
                path = matches[0]
        if not path.exists():
            raise KeyError(rec_id)
        rec = RuntimeRecord(**json.loads(path.read_text(encoding="utf-8")))
        return self.refresh(rec)

    def save(self, rec: RuntimeRecord) -> None:
        rec.updated_at = time.time()
        (self.records_dir / f"{rec.id}.json").write_text(json.dumps(asdict(rec), ensure_ascii=False, indent=2), encoding="utf-8")

    def refresh(self, rec: RuntimeRecord) -> RuntimeRecord:
        if rec.kind == "shell" and rec.tmux_session:
            tmux = shutil.which("tmux")
            if tmux:
                ok = subprocess.run([tmux, "has-session", "-t", rec.tmux_session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
                rec.status = "running" if ok else "exited"
            return rec
        if rec.pid is None:
            return rec
        alive = self._pid_alive(rec.pid)
        rec.status = "running" if alive else "exited"
        return rec

    def tail(self, rec_id: str, lines: int = 200) -> str:
        rec = self.get(rec_id)
        path = Path(rec.log)
        if not path.exists():
            return ""
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])

    def send(self, rec_id: str, text: str, enter: bool = True) -> RuntimeRecord:
        rec = self.get(rec_id)
        if rec.kind != "shell":
            raise ValueError(f"{rec_id} is not a shell session")
        if rec.tmux_session:
            tmux = shutil.which("tmux")
            if not tmux:
                raise RuntimeError("tmux is not available")
            payload = text + ("\n" if enter else "")
            subprocess.run([tmux, "send-keys", "-t", rec.tmux_session, payload], check=True)
            return self.get(rec_id)
        raise RuntimeError("sending to fallback shell sessions is not supported across CLI processes")

    def kill(self, rec_id: str) -> RuntimeRecord:
        rec = self.get(rec_id)
        if rec.kind == "shell" and rec.tmux_session:
            tmux = shutil.which("tmux")
            if tmux:
                subprocess.run([tmux, "kill-session", "-t", rec.tmux_session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rec.status = "killed"
            self.save(rec)
            return rec
        if rec.pid is not None and self._pid_alive(rec.pid):
            try:
                if os.name == "nt":
                    os.kill(rec.pid, signal.SIGTERM)
                else:
                    os.killpg(rec.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            rec.status = "killed"
            self.save(rec)
        return rec

    def _pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        if sys.platform.startswith("linux"):
            stat = Path(f"/proc/{pid}/stat")
            if stat.exists():
                try:
                    parts = stat.read_text().split()
                    if len(parts) > 2 and parts[2] == "Z":
                        return False
                except OSError:
                    pass
        return True


def records_asdict(records: list[RuntimeRecord]) -> list[dict[str, Any]]:
    return [asdict(item) for item in records]
