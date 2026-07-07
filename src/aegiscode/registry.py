from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    mutates_workspace: bool
    requires_approval: bool
    description: str
    params: list[str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for spec in [
            ToolSpec("read_file", False, False, "Read a UTF-8 file inside the workspace", ["path"]),
            ToolSpec("write_file", True, False, "Write a UTF-8 file inside the workspace", ["path", "content"]),
            ToolSpec("edit_file", True, False, "Replace exact text in a workspace file", ["path", "old", "new"]),
            ToolSpec("patch", True, False, "Apply a unified diff to the workspace", ["diff"]),
            ToolSpec("delete_file", True, True, "Remove a file or directory after HITL approval", ["path"]),
            ToolSpec("glob", False, False, "Find files by glob pattern", ["pattern"]),
            ToolSpec("grep", False, False, "Search workspace files for a regex or literal string", ["query", "glob"]),
            ToolSpec("tree", False, False, "Return a compact directory tree", ["path", "depth"]),
            ToolSpec("shell", True, False, "Run one bounded shell command", ["command", "timeout"]),
            ToolSpec("shell_session_start", True, False, "Start a persistent shell-backed session", ["command", "name"]),
            ToolSpec("shell_session_read", False, False, "Read recent persistent session output", ["id"]),
            ToolSpec("shell_session_send", True, False, "Send input to a persistent session", ["id", "input"]),
            ToolSpec("shell_session_kill", True, True, "Terminate a persistent session", ["id"]),
            ToolSpec("job_start", True, False, "Start a tracked long-running job", ["command", "name"]),
            ToolSpec("job_list", False, False, "List tracked jobs", []),
            ToolSpec("job_tail", False, False, "Read recent job output", ["id", "lines"]),
            ToolSpec("job_kill", True, True, "Terminate a tracked job", ["id"]),
            ToolSpec("git_status", False, False, "Show git status", []),
            ToolSpec("git_diff", False, False, "Show git diff", ["staged"]),
            ToolSpec("git_add", True, False, "Stage git paths", ["paths"]),
            ToolSpec("git_commit", True, True, "Create a git commit", ["message"]),
            ToolSpec("git_push", True, True, "Push git commits", ["remote", "branch"]),
            ToolSpec("git_branch", False, False, "Show branches", []),
            ToolSpec("git_log", False, False, "Show recent commits", ["limit"]),
            ToolSpec("browser_text", False, False, "Fetch text from a URL", ["url"]),
            ToolSpec("browser_screenshot", False, False, "Create a basic screenshot artifact when browser backend is available", ["url", "output"]),
            ToolSpec("browser_pdf", False, False, "Create a basic PDF artifact when browser backend is available", ["url", "output"]),
            ToolSpec("audit_tail", False, False, "Read recent JSONL audit events", ["limit"]),
            ToolSpec("create_snapshot", False, False, "Create a workspace snapshot", ["reason"]),
            ToolSpec("restore_snapshot", True, True, "Restore a workspace snapshot after HITL approval", ["id"]),
            ToolSpec("list_tools", False, False, "List available tool capabilities", []),
            ToolSpec("test", False, False, "Run a validator command and capture output", ["command", "timeout"]),
            ToolSpec("remember", False, False, "Persist a project memory record", ["text", "tags"]),
            ToolSpec("finish", False, False, "Stop the run with a summary", ["summary"]),
        ]:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def describe(self) -> list[dict]:
        return [asdict(spec) for spec in sorted(self._tools.values(), key=lambda item: item.name)]

    def prompt_block(self) -> str:
        lines = []
        for spec in sorted(self._tools.values(), key=lambda item: item.name):
            approval = " approval" if spec.requires_approval else ""
            lines.append(f"- {spec.name}: {spec.description}; params={','.join(spec.params) or 'none'};{approval}")
        return "\n".join(lines)
