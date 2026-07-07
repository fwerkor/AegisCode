from __future__ import annotations

import fnmatch
import html
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from time import time
from uuid import uuid4

from .actions import Action, Observation
from .audit import AuditLog
from .registry import ToolRegistry
from .snapshots import SnapshotStore


class ToolDispatcher:
    def __init__(self, workspace: Path, audit: AuditLog | None = None, snapshots: SnapshotStore | None = None, snapshot_before_mutation: bool = False):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.audit = audit
        self.snapshots = snapshots
        self.snapshot_before_mutation = snapshot_before_mutation
        self.registry = ToolRegistry()
        self.state_dir = self.workspace / ".aegiscode"
        self.jobs_dir = self.state_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._processes: dict[str, subprocess.Popen] = {}
        self._logs: dict[str, Path] = {}

    def _safe_path(self, raw: str) -> Path:
        path = Path(raw)
        target = path.resolve() if path.is_absolute() else (self.workspace / path).resolve()
        if self.workspace not in [target, *target.parents]:
            raise ValueError(f"path escapes workspace: {raw}")
        return target

    def _log(self, kind: str, message: str, data: dict | None = None) -> None:
        if self.audit:
            self.audit.append(kind, message, data or {})

    def _maybe_snapshot(self, action: Action) -> None:
        spec = self.registry.get(action.type)
        if not spec or not spec.mutates_workspace or not self.snapshot_before_mutation or not self.snapshots:
            return
        if action.type in {"create_snapshot"}:
            return
        self.snapshots.create(f"before:{action.type}")

    def _run(self, command: str, timeout: int = 20) -> Observation:
        proc = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return Observation("tool.shell", proc.returncode == 0, proc.stdout + proc.stderr, {"returncode": proc.returncode})

    def _git(self, args: list[str], source: str) -> Observation:
        proc = subprocess.run(["git", *args], cwd=self.workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return Observation(source, proc.returncode == 0, proc.stdout + proc.stderr, {"returncode": proc.returncode})

    def _tail(self, path: Path, lines: int) -> str:
        if not path.exists():
            return ""
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])

    def dispatch(self, action: Action) -> Observation:
        self._log("action.start", action.type, {"action_type": action.type, "params": action.params})
        try:
            self._maybe_snapshot(action)
            obs = self._dispatch(action)
            self._log("action.finish", action.type, {"success": obs.success, "source": obs.source, "data": obs.data})
            return obs
        except Exception as exc:
            obs = Observation(f"tool.{action.type}", False, f"{type(exc).__name__}: {exc}")
            self._log("action.error", action.type, {"error": obs.message})
            return obs

    def _dispatch(self, action: Action) -> Observation:
        p = action.params
        if action.type == "read_file":
            path = self._safe_path(str(p["path"]))
            return Observation("tool.read_file", True, path.read_text(encoding="utf-8"), {"path": str(path)})
        if action.type == "write_file":
            path = self._safe_path(str(p["path"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            content = str(p.get("content", ""))
            path.write_text(content, encoding="utf-8")
            return Observation("tool.write_file", True, f"wrote {path.relative_to(self.workspace)}", {"bytes": len(content.encode())})
        if action.type == "edit_file":
            path = self._safe_path(str(p["path"]))
            old = str(p["old"])
            new = str(p.get("new", ""))
            text = path.read_text(encoding="utf-8")
            count = text.count(old)
            if count == 0:
                return Observation("tool.edit_file", False, "old text not found", {"path": str(path)})
            replace_all = bool(p.get("replace_all", False))
            path.write_text(text.replace(old, new, -1 if replace_all else 1), encoding="utf-8")
            return Observation("tool.edit_file", True, f"edited {path.relative_to(self.workspace)}", {"replacements": count if replace_all else 1})
        if action.type == "patch":
            diff = str(p["diff"])
            proc = subprocess.run("git apply --check - && git apply -", cwd=self.workspace, input=diff, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return Observation("tool.patch", proc.returncode == 0, proc.stdout + proc.stderr, {"returncode": proc.returncode})
        if action.type == "delete_file":
            path = self._safe_path(str(p["path"]))
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return Observation("tool.delete_file", True, f"deleted {path.relative_to(self.workspace)}")
        if action.type == "glob":
            matches = sorted(str(x.relative_to(self.workspace)) for x in self.workspace.glob(str(p.get("pattern", "**/*"))))
            return Observation("tool.glob", True, "\n".join(matches[:500]), {"count": len(matches)})
        if action.type == "grep":
            query = str(p["query"])
            glob_pat = str(p.get("glob", "*"))
            regex = bool(p.get("regex", True))
            results: list[str] = []
            for file in self.workspace.rglob("*"):
                if not file.is_file() or ".git" in file.parts or ".aegiscode" in file.parts:
                    continue
                if not fnmatch.fnmatch(file.name, glob_pat) and not fnmatch.fnmatch(str(file.relative_to(self.workspace)), glob_pat):
                    continue
                try:
                    for idx, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
                        ok = re.search(query, line) is not None if regex else query in line
                        if ok:
                            results.append(f"{file.relative_to(self.workspace)}:{idx}:{line}")
                except UnicodeDecodeError:
                    continue
            return Observation("tool.grep", True, "\n".join(results[:500]), {"count": len(results)})
        if action.type == "tree":
            root = self._safe_path(str(p.get("path", ".")))
            depth = int(p.get("depth", 3))
            rows: list[str] = []
            base_parts = len(root.parts)
            for item in sorted(root.rglob("*")):
                rel_depth = len(item.parts) - base_parts
                if rel_depth > depth or ".git" in item.parts or ".aegiscode" in item.parts:
                    continue
                rows.append("  " * (rel_depth - 1) + item.name + ("/" if item.is_dir() else ""))
            return Observation("tool.tree", True, "\n".join(rows[:500]), {"count": len(rows)})
        if action.type in {"shell", "test"}:
            command = str(p.get("command", "python -m pytest" if action.type == "test" else ""))
            timeout = int(p.get("timeout", 60 if action.type == "test" else 20))
            obs = self._run(command, timeout)
            obs.source = f"tool.{action.type}"
            return obs
        if action.type in {"shell_session_start", "job_start"}:
            jid = str(uuid4())
            log = self.jobs_dir / f"{jid}.log"
            command = str(p["command"])
            fh = log.open("ab")
            proc = subprocess.Popen(command, cwd=self.workspace, shell=True, stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT)
            self._processes[jid] = proc
            self._logs[jid] = log
            meta = self.jobs_dir / f"{jid}.json"
            meta.write_text(str({"id": jid, "command": command, "name": p.get("name", ""), "started_at": time()}), encoding="utf-8")
            return Observation(f"tool.{action.type}", True, f"started {jid}", {"id": jid, "pid": proc.pid, "log": str(log)})
        if action.type in {"shell_session_read", "job_tail"}:
            jid = str(p["id"])
            log = self._logs.get(jid) or self.jobs_dir / f"{jid}.log"
            return Observation(f"tool.{action.type}", True, self._tail(log, int(p.get("lines", 200))), {"id": jid})
        if action.type == "shell_session_send":
            jid = str(p["id"])
            proc = self._processes[jid]
            assert proc.stdin is not None
            proc.stdin.write(str(p.get("input", "")) + ("\n" if p.get("enter", True) else ""))
            proc.stdin.flush()
            return Observation("tool.shell_session_send", True, f"sent input to {jid}", {"id": jid})
        if action.type in {"shell_session_kill", "job_kill"}:
            jid = str(p["id"])
            proc = self._processes.get(jid)
            if proc is None:
                return Observation(f"tool.{action.type}", False, "unknown process id", {"id": jid})
            proc.terminate()
            return Observation(f"tool.{action.type}", True, f"terminated {jid}", {"id": jid})
        if action.type == "job_list":
            rows = []
            for jid, proc in self._processes.items():
                rows.append({"id": jid, "pid": proc.pid, "returncode": proc.poll(), "log": str(self._logs[jid])})
            return Observation("tool.job_list", True, str(rows), {"jobs": rows})
        if action.type == "git_status":
            return self._git(["status", "--short", "--branch"], "tool.git_status")
        if action.type == "git_diff":
            args = ["diff"] + (["--staged"] if p.get("staged", False) else [])
            return self._git(args, "tool.git_diff")
        if action.type == "git_add":
            paths = [str(x) for x in p.get("paths", ["."])]
            return self._git(["add", *paths], "tool.git_add")
        if action.type == "git_commit":
            return self._git(["commit", "-m", str(p["message"])], "tool.git_commit")
        if action.type == "git_push":
            return self._git(["push", str(p.get("remote", "origin")), str(p.get("branch", "HEAD"))], "tool.git_push")
        if action.type == "git_branch":
            return self._git(["branch", "--all"], "tool.git_branch")
        if action.type == "git_log":
            return self._git(["log", f"--max-count={int(p.get('limit', 20))}", "--oneline", "--decorate"], "tool.git_log")
        if action.type == "browser_text":
            url = str(p["url"])
            with urllib.request.urlopen(url, timeout=int(p.get("timeout", 20))) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", raw)
            text = html.unescape(re.sub(r"\s+", " ", text)).strip()
            return Observation("tool.browser_text", True, text[:20000], {"url": url})
        if action.type in {"browser_screenshot", "browser_pdf"}:
            return Observation(f"tool.{action.type}", False, "browser artifact backend is optional; use WebUI or install Playwright for artifact capture")
        if action.type == "audit_tail":
            events = self.audit.tail(int(p.get("limit", 50))) if self.audit else []
            return Observation("tool.audit_tail", True, "\n".join(str(e) for e in events), {"count": len(events)})
        if action.type == "create_snapshot":
            if not self.snapshots:
                return Observation("tool.create_snapshot", False, "snapshots are not configured")
            rec = self.snapshots.create(str(p.get("reason", "manual")))
            return Observation("tool.create_snapshot", True, rec.id, {"archive": rec.archive})
        if action.type == "restore_snapshot":
            if not self.snapshots:
                return Observation("tool.restore_snapshot", False, "snapshots are not configured")
            rec = self.snapshots.restore(str(p["id"]))
            return Observation("tool.restore_snapshot", True, rec.id, {"archive": rec.archive})
        if action.type == "list_tools":
            tools = self.registry.describe()
            return Observation("tool.list_tools", True, str(tools), {"tools": tools})
        if action.type == "remember":
            return Observation("tool.remember", True, str(p.get("text", "")), {"tags": p.get("tags", [])})
        if action.type == "finish":
            return Observation("tool.finish", True, str(p.get("summary", "finished")))
        return Observation("tool.unknown", False, f"unknown action: {action.type}")
