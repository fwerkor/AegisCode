from pathlib import Path
from aegiscode.actions import Action
from aegiscode.approvals import ApprovalQueue
from aegiscode.audit import AuditLog
from aegiscode.policy import ShellPolicy
from aegiscode.registry import ToolRegistry
from aegiscode.snapshots import SnapshotStore


def test_approval_queue_persists_decisions(tmp_path: Path):
    queue = ApprovalQueue(tmp_path / "approvals.json")
    rec = queue.submit(Action("delete_file", {"path": "old.txt"}), ["requires review"])
    assert queue.list("pending")[0].id == rec.id
    decided = queue.decide(rec.id, approved=False, note="not needed")
    assert decided.status == "rejected"
    assert queue.list("pending") == []


def test_audit_log_redacts_sensitive_fields(tmp_path: Path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append("tool", "ran", {"content": "private", "nested": {"password": "pw"}, "ok": True})
    event = log.tail(1)[0]
    assert event.data["content"] == "<redacted>"
    assert event.data["nested"]["password"] == "<redacted>"
    assert event.data["ok"] is True


def test_snapshot_store_can_restore_file(tmp_path: Path):
    (tmp_path / "a.txt").write_text("before")
    store = SnapshotStore(tmp_path, tmp_path / ".state" / "snapshots")
    rec = store.create("test")
    (tmp_path / "a.txt").write_text("after")
    store.restore(rec.id)
    assert (tmp_path / "a.txt").read_text() == "before"


def test_policy_allowlist_and_approval_patterns():
    policy = ShellPolicy(allow_prefixes=["python", "pytest"], approval_patterns=["release-prod"])
    assert policy.check("node build.js").allowed is False
    decision = policy.check("python release-prod.py")
    assert decision.needs_approval is True


def test_tool_registry_describes_capabilities():
    tools = ToolRegistry().describe()
    names = {item["name"] for item in tools}
    assert {"read_file", "write_file", "list_tools", "create_snapshot", "restore_snapshot"} <= names
