from __future__ import annotations

import json
from pathlib import Path

from aegiscode.cli import main


def test_cli_init_creates_project_files(tmp_path: Path, capsys):
    assert main(["init", "--root", str(tmp_path)]) == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".aegiscode" / "config.toml").exists()
    assert (tmp_path / ".aegiscode" / "subagents.json").exists()
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["written"]) == 3


def test_cli_doctor_reports_aegiscode(capsys):
    assert main(["doctor"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["package"] == "aegiscode"
    assert payload["cli"] == "aegiscode"
    assert "read_file" in payload["tools"]
    assert "git_push" in payload["tools"]


def test_cli_run_mock(tmp_path: Path, capsys):
    response_1 = '{"action":{"type":"write_file","path":"hello.py","content":"print(42)\\n"}}'
    response_2 = '{"action":{"type":"finish","summary":"done"}}'
    code = main(["run", "create hello", "--workspace", str(tmp_path), "--provider", "mock", "--mock-response", response_1, "--mock-response", response_2])
    assert code == 0
    assert (tmp_path / "hello.py").read_text() == "print(42)\n"
    payload = json.loads(capsys.readouterr().out)
    assert payload["completed"] is True
