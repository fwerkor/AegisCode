from pathlib import Path
from aegiscode.actions import Action
from aegiscode.guardrails import GuardrailEngine
from aegiscode.policy import ShellPolicy

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


def test_command_like_actions_share_shell_policy(tmp_path: Path):
    from aegiscode.actions import Action
    from aegiscode.guardrails import GuardrailEngine

    policy = ShellPolicy(allow_prefixes=["python", "pytest"], approval_patterns=["release-prod"])
    guard = GuardrailEngine(tmp_path, require_approval=True, shell_policy=policy)

    denied = guard.check(Action("job_start", {"command": "node build.js"}))
    assert denied.allowed is False
    assert denied.needs_approval is False

    for action_type in ["shell", "test", "job_start", "shell_session_start"]:
        decision = guard.check(Action(action_type, {"command": "python release-prod.py"}))
        assert decision.allowed is False
        assert decision.needs_approval is True

    send = guard.check(Action("shell_session_send", {"input": "python release-prod.py"}))
    assert send.needs_approval is True
