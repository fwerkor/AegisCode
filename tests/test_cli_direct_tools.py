from __future__ import annotations

import json
from pathlib import Path

from aegiscode.cli import main


def _json_out(capsys):
    return json.loads(capsys.readouterr().out)


def test_cli_shortcut_runs_task(tmp_path: Path, capsys):
    response = '{"action":{"type":"finish","summary":"done"}}'
    code = main(["fix tests", "--workspace", str(tmp_path), "--provider", "mock", "--mock-response", response])
    assert code == 0
    payload = _json_out(capsys)
    assert payload["completed"] is True


def test_file_todo_snapshot_and_approval_cli(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    capsys.readouterr()
    assert main(["file", "write", "hello.txt", "hello"]) == 0
    assert (tmp_path / "hello.txt").read_text() == "hello"
    assert _json_out(capsys)["success"] is True
    assert main(["file", "read", "hello.txt"]) == 0
    assert _json_out(capsys)["message"] == "hello"
    assert main(["todo", "add", "ship cli", "--priority", "high"]) == 0
    todo = _json_out(capsys)["data"]["todo"]
    assert todo["priority"] == "high"
    assert main(["snapshot", "create", "--reason", "test"]) == 0
    snap_id = _json_out(capsys)["data"]["snapshot"]["id"]
    assert snap_id
    assert main(["file", "delete", "hello.txt"]) == 3
    approval = _json_out(capsys)
    assert approval["needs_approval"] is True
    assert approval["action"] == "delete_file"
    assert (tmp_path / "hello.txt").exists()


def test_doctor_reports_capability_matrix(capsys):
    assert main(["doctor"]) == 0
    payload = _json_out(capsys)
    assert payload["tool_matrix"]["file"]
    assert payload["capabilities"]["git"] in {True, False}
