from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentConfig:
    max_steps: int = 8
    workspace: Path = Path(".")
    stop_on_approval_required: bool = True


@dataclass
class ProviderConfig:
    default: str = "mock"
    model: str = "gpt-4.1-mini"
    base_url: str = "https://api.openai.com/v1/chat/completions"


@dataclass
class FeedbackConfig:
    commands: list[str] = field(default_factory=list)
    run_after_actions: list[str] = field(default_factory=lambda: ["write_file", "edit_file", "patch", "delete_file", "shell", "test"])


@dataclass
class MemoryConfig:
    path: Path = Path(".aegiscode/memory.json")
    max_results: int = 5


@dataclass
class GuardrailConfig:
    require_approval: bool = True


@dataclass
class GovernanceConfig:
    audit_path: Path = Path(".aegiscode/audit.jsonl")
    approvals_path: Path = Path(".aegiscode/approvals.json")
    snapshot_dir: Path = Path(".aegiscode/snapshots")
    snapshot_before_mutation: bool = True


@dataclass
class ShellPolicyConfig:
    allow_prefixes: list[str] = field(default_factory=list)
    approval_patterns: list[str] = field(default_factory=lambda: ["external-deploy", "release-prod", "cloud-admin", "git push", "gh release", "twine upload"])
    deny_patterns: list[str] = field(default_factory=list)
    max_command_chars: int = 800


@dataclass
class HarnessConfig:
    agent: AgentConfig = field(default_factory=AgentConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    guardrails: GuardrailConfig = field(default_factory=GuardrailConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    shell_policy: ShellPolicyConfig = field(default_factory=ShellPolicyConfig)

    @classmethod
    def from_file(cls, path: Path) -> "HarnessConfig":
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        cfg = cls()
        agent = raw.get("agent", {})
        cfg.agent.max_steps = int(agent.get("max_steps", cfg.agent.max_steps))
        cfg.agent.workspace = Path(agent.get("workspace", str(cfg.agent.workspace)))
        cfg.agent.stop_on_approval_required = bool(agent.get("stop_on_approval_required", cfg.agent.stop_on_approval_required))
        provider = raw.get("provider", {})
        cfg.provider.default = str(provider.get("default", cfg.provider.default))
        cfg.provider.model = str(provider.get("model", cfg.provider.model))
        cfg.provider.base_url = str(provider.get("base_url", cfg.provider.base_url))
        feedback = raw.get("feedback", {})
        cfg.feedback.commands = list(feedback.get("commands", cfg.feedback.commands))
        cfg.feedback.run_after_actions = list(feedback.get("run_after_actions", cfg.feedback.run_after_actions))
        memory = raw.get("memory", {})
        cfg.memory.path = Path(memory.get("path", str(cfg.memory.path)))
        cfg.memory.max_results = int(memory.get("max_results", cfg.memory.max_results))
        guard = raw.get("guardrails", {})
        cfg.guardrails.require_approval = bool(guard.get("require_approval", cfg.guardrails.require_approval))
        gov = raw.get("governance", {})
        cfg.governance.audit_path = Path(gov.get("audit_path", str(cfg.governance.audit_path)))
        cfg.governance.approvals_path = Path(gov.get("approvals_path", str(cfg.governance.approvals_path)))
        cfg.governance.snapshot_dir = Path(gov.get("snapshot_dir", str(cfg.governance.snapshot_dir)))
        cfg.governance.snapshot_before_mutation = bool(gov.get("snapshot_before_mutation", cfg.governance.snapshot_before_mutation))
        policy = raw.get("shell_policy", {})
        cfg.shell_policy.allow_prefixes = list(policy.get("allow_prefixes", cfg.shell_policy.allow_prefixes))
        cfg.shell_policy.approval_patterns = list(policy.get("approval_patterns", cfg.shell_policy.approval_patterns))
        cfg.shell_policy.deny_patterns = list(policy.get("deny_patterns", cfg.shell_policy.deny_patterns))
        cfg.shell_policy.max_command_chars = int(policy.get("max_command_chars", cfg.shell_policy.max_command_chars))
        return cfg

    @classmethod
    def load_default(cls, config: Path | None = None) -> "HarnessConfig":
        for candidate in [config, Path(".aegiscode/config.toml"), Path("config/aegiscode.example.toml")]:
            if candidate is not None and candidate.exists():
                return cls.from_file(candidate)
        return cls()
