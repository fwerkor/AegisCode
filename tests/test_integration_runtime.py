from __future__ import annotations

import json
from pathlib import Path

from aegiscode.agent import AgentLoop
from aegiscode.actions import Action
from aegiscode.config import HarnessConfig
from aegiscode.llm import MockLLM
from aegiscode.registry import ToolRegistry
from aegiscode.tools import ToolDispatcher


def test_registry_has_requested_feature_surface():
    names = {item["name"] for item in ToolRegistry().describe()}
    expected = {
        "read_file", "write_file", "edit_file", "patch", "delete_file", "glob", "grep", "tree",
        "shell", "shell_session_start", "job_start", "job_tail", "job_kill",
        "git_status", "git_diff", "git_add", "git_commit", "git_push", "git_branch", "git_log",
        "browser_text", "browser_screenshot", "browser_pdf",
        "audit_tail", "create_snapshot", "restore_snapshot", "list_tools",
    }
    assert expected <= names


def test_dispatcher_file_glob_grep_tree(tmp_path: Path):
    tools = ToolDispatcher(tmp_path)
    assert tools.dispatch(Action("write_file", {"path": "src/a.txt", "content": "alpha\n"})).success
    assert tools.dispatch(Action("edit_file", {"path": "src/a.txt", "old": "alpha", "new": "beta"})).success
    grep = tools.dispatch(Action("grep", {"query": "beta", "glob": "*.txt"}))
    assert grep.success and "src/a.txt" in grep.message
    tree = tools.dispatch(Action("tree", {"path": ".", "depth": 2}))
    assert tree.success and "src/" in tree.message


def test_agent_queues_persistent_approval(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.feedback.commands = []
    llm = MockLLM([json.dumps({"action": {"type": "delete_file", "path": "important.txt"}})])
    (tmp_path / "important.txt").write_text("keep")
    result = AgentLoop(llm, cfg, tmp_path).run("delete important file")
    assert result.stopped_reason == "approval_required"
    approvals = tmp_path / ".aegiscode" / "approvals.json"
    assert approvals.exists()
    assert "delete_file" in approvals.read_text(encoding="utf-8")
    assert (tmp_path / "important.txt").exists()
