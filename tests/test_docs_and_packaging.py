from __future__ import annotations

from aegiscode.registry import ToolRegistry
from scripts import build_docs, validate_packaging


def test_docs_link_check():
    assert build_docs.main() == 0


def test_packaging_manifest_validation():
    assert validate_packaging.main() == 0


def test_tool_surface_snapshot():
    names = {item["name"] for item in ToolRegistry().describe()}
    expected = {
        "read_file", "write_file", "edit_file", "patch", "delete_file", "glob", "grep", "tree",
        "shell", "shell_session_start", "shell_session_list", "shell_session_read", "shell_session_send", "shell_session_kill",
        "job_start", "job_list", "job_tail", "job_kill",
        "git_status", "git_diff", "git_add", "git_commit", "git_push", "git_branch", "git_log",
        "browser_text", "browser_screenshot", "browser_pdf",
        "audit_tail", "create_snapshot", "list_snapshots", "restore_snapshot",
        "todo_add", "todo_list", "todo_update", "todo_remove",
    }
    assert expected <= names
