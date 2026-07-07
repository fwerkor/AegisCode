from __future__ import annotations

import fnmatch
import html
import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from .actions import Action, Observation
from .audit import AuditLog
from .registry import ToolRegistry
from .runtime import RuntimeStore, records_asdict
from .snapshots import SnapshotStore
from .todo import TodoStore


class ToolDispatcher:
    def __init__(self, workspace: Path, audit: AuditLog | None = None, snapshots: SnapshotStore | None = None, snapshot_before_mutation: bool = False):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.audit = audit
        self.snapshots = snapshots
        self.snapshot_before_mutation = snapshot_before_mutation
        self.registry = ToolRegistry()
        self.state_dir = self.workspace / ".aegiscode"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.runtime = RuntimeStore(self.state_dir)
        self.todos = TodoStore(self.state_dir / "todos.json")

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
            matches = sorted(str(x.relative_to(self.workspace)) for x in self.workspace.glob(str(p.get("pattern", "**/*"))) if ".git" not in x.parts and ".aegiscode" not in x.parts)
            return Observation("tool.glob", True, "\n".join(matches[:500]), {"count": len(matches)})
        if action.type == "grep":
            query = str(p["query"])
            glob_pat = str(p.get("glob", "*"))
            regex = bool(p.get("regex", True))
            results: list[str] = []
            for file in self.workspace.rglob("*"):
                if not file.is_file() or ".git" in file.parts or ".aegiscode" in file.parts:
                    continue
                rel = str(file.relative_to(self.workspace))
                if not fnmatch.fnmatch(file.name, glob_pat) and not fnmatch.fnmatch(rel, glob_pat):
                    continue
                try:
                    for idx, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
                        ok = re.search(query, line) is not None if regex else query in line
                        if ok:
                            results.append(f"{rel}:{idx}:{line}")
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
        if action.type == "shell_session_start":
            rec = self.runtime.start_shell(str(p.get("command", "")), self.workspace, str(p.get("name", "")))
            return Observation("tool.shell_session_start", True, f"started shell {rec.id}", asdict_safe(rec))
        if action.type == "shell_session_list":
            rows = records_asdict(self.runtime.list("shell"))
            return Observation("tool.shell_session_list", True, json.dumps(rows, ensure_ascii=False, indent=2), {"sessions": rows})
        if action.type == "shell_session_read":
            return Observation("tool.shell_session_read", True, self.runtime.tail(str(p["id"]), int(p.get("lines", 200))), {"id": str(p["id"])})
        if action.type == "shell_session_send":
            rec = self.runtime.send(str(p["id"]), str(p.get("input", "")), bool(p.get("enter", True)))
            return Observation("tool.shell_session_send", True, f"sent input to {rec.id}", asdict_safe(rec))
        if action.type == "shell_session_kill":
            rec = self.runtime.kill(str(p["id"]))
            return Observation("tool.shell_session_kill", True, f"terminated {rec.id}", asdict_safe(rec))
        if action.type == "job_start":
            rec = self.runtime.start_job(str(p["command"]), self.workspace, str(p.get("name", "")))
            return Observation("tool.job_start", True, f"started job {rec.id}", asdict_safe(rec))
        if action.type == "job_list":
            rows = records_asdict(self.runtime.list("job"))
            return Observation("tool.job_list", True, json.dumps(rows, ensure_ascii=False, indent=2), {"jobs": rows})
        if action.type == "job_tail":
            return Observation("tool.job_tail", True, self.runtime.tail(str(p["id"]), int(p.get("lines", 200))), {"id": str(p["id"])})
        if action.type == "job_kill":
            rec = self.runtime.kill(str(p["id"]))
            return Observation("tool.job_kill", True, f"terminated {rec.id}", asdict_safe(rec))
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
            return self._playwright_artifact(action.type, p)
        if action.type == "audit_tail":
            events = self.audit.tail(int(p.get("limit", 50))) if self.audit else []
            rows = [asdict_safe(e) for e in events]
            return Observation("tool.audit_tail", True, "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), {"count": len(events)})
        if action.type == "create_snapshot":
            if not self.snapshots:
                return Observation("tool.create_snapshot", False, "snapshots are not configured")
            rec = self.snapshots.create(str(p.get("reason", "manual")))
            return Observation("tool.create_snapshot", True, rec.id, {"snapshot": asdict_safe(rec)})
        if action.type == "list_snapshots":
            rows = [asdict_safe(rec) for rec in self.snapshots.list()] if self.snapshots else []
            return Observation("tool.list_snapshots", True, json.dumps(rows, ensure_ascii=False, indent=2), {"snapshots": rows})
        if action.type == "restore_snapshot":
            if not self.snapshots:
                return Observation("tool.restore_snapshot", False, "snapshots are not configured")
            rec = self.snapshots.restore(str(p["id"]))
            return Observation("tool.restore_snapshot", True, rec.id, {"snapshot": asdict_safe(rec)})
        if action.type == "todo_add":
            item = self.todos.add(str(p["content"]), str(p.get("priority", "normal")))
            return Observation("tool.todo_add", True, item.id, {"todo": asdict_safe(item)})
        if action.type == "todo_list":
            rows = [asdict_safe(item) for item in self.todos.list(p.get("status"))]
            return Observation("tool.todo_list", True, json.dumps(rows, ensure_ascii=False, indent=2), {"todos": rows})
        if action.type == "todo_update":
            item = self.todos.update(str(p["id"]), status=p.get("status"), content=p.get("content"), priority=p.get("priority"))
            return Observation("tool.todo_update", True, item.id, {"todo": asdict_safe(item)})
        if action.type == "todo_remove":
            item = self.todos.remove(str(p["id"]))
            return Observation("tool.todo_remove", True, item.id, {"todo": asdict_safe(item)})
        if action.type == "list_tools":
            tools = self.registry.describe()
            return Observation("tool.list_tools", True, json.dumps(tools, ensure_ascii=False, indent=2), {"tools": tools})
        if action.type == "remember":
            return Observation("tool.remember", True, str(p.get("text", "")), {"tags": p.get("tags", [])})
        if action.type == "finish":
            return Observation("tool.finish", True, str(p.get("summary", "finished")))
        return Observation("tool.unknown", False, f"unknown action: {action.type}")

    def _playwright_artifact(self, action_type: str, params: dict[str, Any]) -> Observation:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            return Observation(f"tool.{action_type}", False, f"Playwright is not installed: {exc}")
        url = str(params["url"])
        output = self._safe_path(str(params.get("output") or ("screenshot.png" if action_type == "browser_screenshot" else "page.pdf")))
        output.parent.mkdir(parents=True, exist_ok=True)
        width = int(params.get("width", 1440))
        height = int(params.get("height", 1000))
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(url, wait_until=str(params.get("wait_until", "networkidle")))
            if action_type == "browser_screenshot":
                page.screenshot(path=str(output), full_page=bool(params.get("full_page", True)))
            else:
                page.pdf(path=str(output), width=f"{width}px", height=f"{height}px")
            browser.close()
        return Observation(f"tool.{action_type}", True, f"wrote {output.relative_to(self.workspace)}", {"path": str(output), "url": url})


def asdict_safe(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(obj)
    return dict(obj)
