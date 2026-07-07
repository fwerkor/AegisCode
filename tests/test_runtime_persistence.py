from __future__ import annotations

import json
import time
from pathlib import Path

from aegiscode.actions import Action
from aegiscode.tools import ToolDispatcher


def test_job_metadata_persists_across_dispatchers(tmp_path: Path):
    first = ToolDispatcher(tmp_path)
    obs = first.dispatch(Action("job_start", {"command": "python -c 'print(123)'", "name": "once"}))
    assert obs.success
    job_id = obs.data["id"]
    deadline = time.time() + 5
    tail = ""
    second = ToolDispatcher(tmp_path)
    while time.time() < deadline:
        tail = second.dispatch(Action("job_tail", {"id": job_id, "lines": 20})).message
        if "123" in tail:
            break
        time.sleep(0.05)
    assert "123" in tail
    listed = second.dispatch(Action("job_list", {}))
    assert listed.success
    assert job_id in listed.message


def test_runtime_records_are_json(tmp_path: Path):
    tools = ToolDispatcher(tmp_path)
    obs = tools.dispatch(Action("job_start", {"command": "python -c 'print(456)'", "name": "json"}))
    assert obs.success
    job_id = obs.data["id"]
    record = tmp_path / ".aegiscode" / "runtime" / f"{job_id}.json"
    assert record.exists()
    payload = json.loads(record.read_text(encoding="utf-8"))
    assert payload["kind"] == "job"
    assert payload["name"] == "json"
