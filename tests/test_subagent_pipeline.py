from __future__ import annotations

from pathlib import Path

from aegiscode.config import HarnessConfig
from aegiscode.llm import MockLLM
from aegiscode.subagents import DEFAULT_PIPELINE, SubagentManager, SubagentSpec, SubagentStore


def test_subagent_expanded_spec_and_task_metadata(tmp_path: Path):
    store = SubagentStore(tmp_path / "subagents.json")
    cfg = HarnessConfig()
    manager = SubagentManager(store, tmp_path / "work", cfg, lambda spec: MockLLM(['{"action":{"type":"finish","summary":"done"}}']))
    manager.register(SubagentSpec(name="docs", role="documentation", description="write docs", capabilities=["file"], workspace="docs-work", provider="mock", model="mock-model", priority=7, concurrency=2, default_next="reviewer"))
    manager.submit("docs", "write docs", priority=9, depends_on=["parent"], parent_id="parent", max_attempts=3)
    loaded = store.load_specs()["docs"]
    assert loaded.description == "write docs"
    assert loaded.capabilities == ["file"]
    assert loaded.workspace == "docs-work"
    loaded_task = store.load_tasks()[0]
    assert loaded_task.priority == 9
    assert loaded_task.depends_on == ["parent"]
    assert loaded_task.parent_id == "parent"
    assert loaded_task.max_attempts == 3


def test_default_pipeline_queues_dependencies(tmp_path: Path):
    store = SubagentStore(tmp_path / "subagents.json")
    cfg = HarnessConfig()
    manager = SubagentManager(store, tmp_path / "work", cfg, lambda spec: MockLLM(['{"action":{"type":"finish","summary":"done"}}']))
    tasks = manager.queue_default_pipeline("ship")
    assert [task.agent_name for task in tasks] == DEFAULT_PIPELINE
    assert tasks[0].depends_on == []
    assert tasks[1].depends_on == [tasks[0].id]
    assert store.load_specs()["planner"].default_next == "implementer"
