from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    mutates_workspace: bool
    requires_approval: bool
    description: str
    params: list[str]
    group: str = "runtime"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        rows = [
            ("read_file", False, False, "Read a UTF-8 file inside the workspace", ["path"], "file"),
            ("write_file", True, False, "Write a UTF-8 file inside the workspace", ["path", "content"], "file"),
            ("edit_file", True, False, "Replace exact text in a workspace file", ["path", "old", "new"], "file"),
            ("patch", True, False, "Apply a unified diff to the workspace", ["diff"], "file"),
            ("delete_file", True, True, "Remove a file or directory after approval", ["path"], "file"),
            ("glob", False, False, "Find files by glob pattern", ["pattern"], "file"),
            ("grep", False, False, "Search workspace files", ["query", "glob"], "file"),
            ("tree", False, False, "Return a compact directory tree", ["path", "depth"], "file"),
            ("shell", True, False, "Run one bounded shell command", ["command", "timeout"], "shell"),
            ("shell_session_start", True, False, "Start a persistent shell-backed session", ["command", "name"], "shell"),
            ("shell_session_list", False, False, "List persistent shell-backed sessions", [], "shell"),
            ("shell_session_read", False, False, "Read recent persistent session output", ["id", "lines"], "shell"),
            ("shell_session_send", True, False, "Send input to a persistent session", ["id", "input"], "shell"),
            ("shell_session_kill", True, True, "Terminate a persistent session", ["id"], "shell"),
            ("job_start", True, False, "Start a tracked long-running job", ["command", "name"], "job"),
            ("job_list", False, False, "List tracked jobs", [], "job"),
            ("job_tail", False, False, "Read recent job output", ["id", "lines"], "job"),
            ("job_kill", True, True, "Terminate a tracked job", ["id"], "job"),
            ("git_status", False, False, "Show git status", [], "git"),
            ("git_diff", False, False, "Show git diff", ["staged"], "git"),
            ("git_add", True, False, "Stage git paths", ["paths"], "git"),
            ("git_commit", True, True, "Create a git commit", ["message"], "git"),
            ("git_push", True, True, "Push git commits", ["remote", "branch"], "git"),
            ("git_branch", False, False, "Show branches", [], "git"),
            ("git_log", False, False, "Show recent commits", ["limit"], "git"),
            ("browser_text", False, False, "Fetch visible text from a URL", ["url"], "browser"),
            ("browser_screenshot", False, False, "Create a screenshot artifact when Playwright is available", ["url", "output"], "browser"),
            ("browser_pdf", False, False, "Create a PDF artifact when Playwright is available", ["url", "output"], "browser"),
            ("audit_tail", False, False, "Read recent JSONL audit events", ["limit"], "audit"),
            ("create_snapshot", False, False, "Create a workspace snapshot", ["reason"], "snapshot"),
            ("list_snapshots", False, False, "List workspace snapshots", [], "snapshot"),
            ("restore_snapshot", True, True, "Restore a workspace snapshot after approval", ["id"], "snapshot"),
            ("todo_add", True, False, "Add a durable project todo item", ["content", "priority"], "todo"),
            ("todo_list", False, False, "List durable project todo items", ["status"], "todo"),
            ("todo_update", True, False, "Update a durable project todo item", ["id", "status", "content", "priority"], "todo"),
            ("todo_remove", True, False, "Remove a durable project todo item", ["id"], "todo"),
            ("list_tools", False, False, "List available tool capabilities", [], "runtime"),
            ("test", False, False, "Run a validator command and capture output", ["command", "timeout"], "runtime"),
            ("remember", False, False, "Persist a project memory record", ["text", "tags"], "runtime"),
            ("finish", False, False, "Stop the run with a summary", ["summary"], "runtime"),
        ]
        for row in rows:
            self.register(ToolSpec(*row))

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def describe(self) -> list[dict]:
        return [asdict(spec) for spec in sorted(self._tools.values(), key=lambda item: (item.group, item.name))]

    def by_group(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for item in self.describe():
            grouped.setdefault(item["group"], []).append(item)
        return grouped

    def prompt_block(self) -> str:
        lines = []
        for spec in sorted(self._tools.values(), key=lambda item: (item.group, item.name)):
            approval = " approval" if spec.requires_approval else ""
            lines.append(f"- {spec.name} [{spec.group}]: {spec.description}; params={','.join(spec.params) or 'none'};{approval}")
        return "\n".join(lines)
