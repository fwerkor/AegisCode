from pathlib import Path
from aegis_harness.actions import Action
from aegis_harness.guardrails import GuardrailEngine

def test_guardrail_requires_approval_for_publish_like_command(tmp_path: Path):
    decision = GuardrailEngine(tmp_path).check(Action("shell", {"command":"external-deploy production"}))
    assert not decision.allowed
    assert decision.needs_approval

def test_guardrail_blocks_path_escape(tmp_path: Path):
    decision = GuardrailEngine(tmp_path).check(Action("write_file", {"path":"../escape.txt", "content":"x"}))
    assert not decision.allowed
    assert not decision.needs_approval

def test_safe_workspace_write_allowed(tmp_path: Path):
    decision = GuardrailEngine(tmp_path).check(Action("write_file", {"path":"src/a.py", "content":"x"}))
    assert decision.allowed
