import json
from pathlib import Path
from aegiscode.config import HarnessConfig
from aegiscode.llm import MockLLM
from aegiscode.subagents import SubagentManager, SubagentSpec, SubagentStore


def test_subagent_manager_runs_persisted_queue(tmp_path: Path):
    store = SubagentStore(tmp_path / "subagents.json")
    cfg = HarnessConfig()
    cfg.feedback.commands = []
    def factory(spec):
        return MockLLM([
            json.dumps({"action": {"type": "write_file", "path": "result.txt", "content": spec.role}}),
            json.dumps({"action": {"type": "finish", "summary": "done"}}),
        ])
    manager = SubagentManager(store, tmp_path / "work", cfg, factory)
    manager.register(SubagentSpec(name="reviewer", role="spec-review"))
    task = manager.submit("reviewer", "create result")
    result = manager.run_next()
    assert result is not None
    assert result.id == task.id
    assert result.status == "completed"
    assert (tmp_path / "work" / "reviewer" / "result.txt").read_text() == "spec-review"


def test_subagent_max_steps_does_not_change_parent_config(tmp_path: Path):
    store = SubagentStore(tmp_path / "subagents.json")
    cfg = HarnessConfig()
    cfg.agent.max_steps = 9
    cfg.feedback.commands = []

    def factory(spec):
        return MockLLM([json.dumps({"action": {"type": "finish", "summary": "done"}})])

    manager = SubagentManager(store, tmp_path / "work", cfg, factory)
    manager.register(SubagentSpec(name="short", role="short", max_steps=1))
    manager.submit("short", "finish")
    result = manager.run_next()
    assert result is not None
    assert result.status == "completed"
    assert cfg.agent.max_steps == 9
