import json
from pathlib import Path
from aegis_harness.agent import AgentLoop
from aegis_harness.config import HarnessConfig
from aegis_harness.llm import MockLLM

def test_mock_llm_feedback_loop_repairs_file(tmp_path: Path):
    cfg = HarnessConfig(); cfg.agent.max_steps = 5; cfg.feedback.commands = ["python -m py_compile hello.py"]
    llm = MockLLM([
        json.dumps({"action":{"type":"write_file","path":"hello.py","content":"print('broken'\n"}}),
        json.dumps({"action":{"type":"write_file","path":"hello.py","content":"print('fixed')\n"}}),
        json.dumps({"action":{"type":"finish","summary":"done"}}),
    ])
    result = AgentLoop(llm, cfg, tmp_path).run("write valid python")
    assert result.completed
    assert "fixed" in (tmp_path / "hello.py").read_text()
    assert any(not o.success and o.source == "feedback" for o in result.observations)
    assert any(o.success and o.source == "feedback" for o in result.observations)

def test_mock_llm_guardrail_stops_for_approval(tmp_path: Path):
    cfg = HarnessConfig()
    llm = MockLLM([json.dumps({"action":{"type":"shell","command":"external-deploy production"}})])
    result = AgentLoop(llm, cfg, tmp_path).run("danger")
    assert not result.completed
    assert result.stopped_reason == "approval_required"
    assert result.observations[0].data["needs_approval"] is True

def test_remember_action_persists_memory(tmp_path: Path):
    cfg = HarnessConfig(); cfg.memory.path = tmp_path / "mem.json"
    llm = MockLLM([
        json.dumps({"action":{"type":"remember","text":"Use ruff before release","tags":["quality"]}}),
        json.dumps({"action":{"type":"finish","summary":"ok"}}),
    ])
    result = AgentLoop(llm, cfg, tmp_path).run("store rule")
    assert result.completed
    assert "ruff" in cfg.memory.path.read_text()
