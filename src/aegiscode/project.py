from __future__ import annotations

from pathlib import Path

DEFAULT_AGENTS = """# AGENTS.md

This repository is configured for AegisCode.

## Project rules

- Plan before mutating code.
- Keep changes small and reviewable.
- Run deterministic tests before claiming completion.
- Use subagents for planning, implementation, review, testing, and release work.
- Queue high-risk actions through persistent approvals.
- Keep audit logs and snapshots enabled for agent-initiated changes.

## Default subagents

- planner: decomposes work into tasks and verification steps.
- implementer: performs focused code changes.
- reviewer: checks spec compliance and maintainability.
- tester: runs verification and classifies failures.
- release: prepares packages, artifacts, release notes, and release checks.
"""

DEFAULT_CONFIG = """[agent]
max_steps = 12
workspace = "."
stop_on_approval_required = true

[provider]
default = "mock"
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1/chat/completions"

[feedback]
commands = ["python -m pytest -q"]
run_after_actions = ["write_file", "edit_file", "patch", "delete_file", "shell", "test"]

[memory]
path = ".aegiscode/memory.json"
max_results = 8

[guardrails]
require_approval = true

[governance]
audit_path = ".aegiscode/audit.jsonl"
approvals_path = ".aegiscode/approvals.json"
snapshot_dir = ".aegiscode/snapshots"
snapshot_before_mutation = true

[shell_policy]
allow_prefixes = []
approval_patterns = ["external-deploy", "release-prod", "cloud-admin", "git push", "gh release", "twine upload"]
deny_patterns = []
max_command_chars = 800
"""

DEFAULT_SUBAGENTS = """{
  "specs": {
    "planner": {"name": "planner", "role": "planning", "system_hint": "Create a concise implementation plan before edits.", "max_steps": 6, "labels": ["plan"]},
    "implementer": {"name": "implementer", "role": "implementation", "system_hint": "Make one focused code change and keep tests passing.", "max_steps": 10, "labels": ["code"]},
    "reviewer": {"name": "reviewer", "role": "review", "system_hint": "Review for spec compliance, safety, and maintainability.", "max_steps": 6, "labels": ["review"]},
    "tester": {"name": "tester", "role": "verification", "system_hint": "Run validators, classify failures, and propose minimal fixes.", "max_steps": 6, "labels": ["test"]},
    "release": {"name": "release", "role": "release", "system_hint": "Prepare changelog, artifacts, and release checks.", "max_steps": 6, "labels": ["release"]}
  },
  "tasks": []
}
"""


def init_project(root: Path, force: bool = False) -> list[Path]:
    root = root.resolve()
    written: list[Path] = []
    targets = {
        root / "AGENTS.md": DEFAULT_AGENTS,
        root / ".aegiscode" / "config.toml": DEFAULT_CONFIG,
        root / ".aegiscode" / "subagents.json": DEFAULT_SUBAGENTS,
    }
    for path, content in targets.items():
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
