from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .agent import AgentLoop
from .approvals import ApprovalQueue
from .config import HarnessConfig
from .credentials import EncryptedCredentialStore, prompt_secret
from .llm import GitHubModelsClient, MockLLM, OpenAICompatibleClient
from .project import init_project
from .registry import ToolRegistry
from .subagents import SubagentManager, SubagentSpec, SubagentStore


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aegiscode")
    p.add_argument("--config", default=None, help="Path to .aegiscode/config.toml")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="Initialize AGENTS.md and .aegiscode project state")
    init.add_argument("--root", default=".")
    init.add_argument("--force", action="store_true")

    run = sub.add_parser("run", help="Run one AegisCode agent task")
    run.add_argument("task")
    run.add_argument("--workspace", default=None)
    run.add_argument("--mock-response", action="append", default=[])
    run.add_argument("--provider", choices=["mock", "openai-compatible", "github-models"], default=None)
    run.add_argument("--model", default=None)
    run.add_argument("--base-url", default=None)

    serve = sub.add_parser("serve", help="Start the local WebUI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    sg = sub.add_parser("subagent", help="Manage durable subagents")
    sgs = sg.add_subparsers(dest="sub_cmd", required=True)
    sgs.add_parser("list")
    reg = sgs.add_parser("register")
    reg.add_argument("name")
    reg.add_argument("--role", required=True)
    reg.add_argument("--system-hint", default="")
    reg.add_argument("--max-steps", type=int, default=None)
    reg.add_argument("--label", action="append", default=[])
    queue = sgs.add_parser("queue")
    queue.add_argument("--agent")
    queue.add_argument("--task")
    sgs.add_parser("run-next")
    sgs.add_parser("run-all")

    ap = sub.add_parser("approval", help="Inspect and decide persistent approvals")
    aps = ap.add_subparsers(dest="approval_cmd", required=True)
    list_ap = aps.add_parser("list")
    list_ap.add_argument("--status", default=None)
    approve = aps.add_parser("approve")
    approve.add_argument("id")
    approve.add_argument("--note", default="")
    reject = aps.add_parser("reject")
    reject.add_argument("id")
    reject.add_argument("--note", default="")

    sub.add_parser("doctor", help="Print installation, config, provider, and tool-surface diagnostics")

    auth = sub.add_parser("auth", help="Manage encrypted local provider credentials")
    auths = auth.add_subparsers(dest="auth_cmd", required=False)
    auths.add_parser("status")
    aset = auths.add_parser("set")
    aset.add_argument("name", choices=["openai", "github"])
    aget = auths.add_parser("get")
    aget.add_argument("name", choices=["openai", "github"])
    aclr = auths.add_parser("clear")
    aclr.add_argument("name", choices=["openai", "github"])
    return p


def _cfg(path: str | None) -> HarnessConfig:
    return HarnessConfig.load_default(Path(path) if path else None)


def _workspace(cfg: HarnessConfig, override: str | None = None) -> Path:
    return Path(override) if override else cfg.agent.workspace


def _credential_store() -> EncryptedCredentialStore:
    return EncryptedCredentialStore(Path.home() / ".aegiscode" / "credential-store.json")


def _make_llm(cfg: HarnessConfig, provider: str | None, model: str | None, base_url: str | None, mock_responses: list[str]):
    selected = provider or cfg.provider.default
    selected_model = model or cfg.provider.model
    if mock_responses or selected == "mock":
        return MockLLM(list(mock_responses))
    if selected == "github-models":
        return GitHubModelsClient(model=selected_model)
    if selected == "openai-compatible":
        return OpenAICompatibleClient(model=selected_model, base_url=base_url or cfg.provider.base_url)
    raise ValueError(f"unknown provider: {selected}")


def _subagent_manager(cfg: HarnessConfig, workspace: Path, mock_responses: list[str] | None = None) -> SubagentManager:
    store = SubagentStore(workspace / ".aegiscode" / "subagents.json")

    def factory(_spec: SubagentSpec):
        return _make_llm(cfg, cfg.provider.default, cfg.provider.model, cfg.provider.base_url, mock_responses or [])

    return SubagentManager(store, workspace, cfg, factory)


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)

    if ns.cmd == "init":
        written = init_project(Path(ns.root), force=ns.force)
        print(json.dumps({"written": [str(p) for p in written]}, indent=2, ensure_ascii=False))
        return 0

    if ns.cmd == "serve":
        from .web import main as web_main

        return int(web_main(["--host", ns.host, "--port", str(ns.port)]) or 0)

    if ns.cmd == "run":
        cfg = _cfg(ns.config)
        workspace = _workspace(cfg, ns.workspace)
        llm = _make_llm(cfg, ns.provider, ns.model, ns.base_url, ns.mock_response)
        result = AgentLoop(llm, cfg, workspace).run(ns.task)
        print(json.dumps({"completed": result.completed, "stopped_reason": result.stopped_reason, "steps": result.steps, "observations": [asdict(o) for o in result.observations]}, indent=2, ensure_ascii=False))
        return 0 if result.completed else 2

    if ns.cmd == "subagent":
        cfg = _cfg(ns.config)
        workspace = _workspace(cfg)
        manager = _subagent_manager(cfg, workspace)
        if ns.sub_cmd == "list":
            print(json.dumps({name: asdict(spec) for name, spec in manager.store.load_specs().items()}, indent=2, ensure_ascii=False))
            return 0
        if ns.sub_cmd == "register":
            spec = manager.register(SubagentSpec(ns.name, ns.role, ns.system_hint, ns.max_steps, ns.label))
            print(json.dumps(asdict(spec), indent=2, ensure_ascii=False))
            return 0
        if ns.sub_cmd == "queue":
            if ns.agent and ns.task:
                task = manager.submit(ns.agent, ns.task)
                print(json.dumps(asdict(task), indent=2, ensure_ascii=False))
            else:
                print(json.dumps([asdict(task) for task in manager.store.load_tasks()], indent=2, ensure_ascii=False))
            return 0
        if ns.sub_cmd == "run-next":
            task = manager.run_next()
            print(json.dumps(asdict(task) if task else None, indent=2, ensure_ascii=False))
            return 0
        if ns.sub_cmd == "run-all":
            print(json.dumps([asdict(task) for task in manager.run_all_sequential()], indent=2, ensure_ascii=False))
            return 0

    if ns.cmd == "approval":
        cfg = _cfg(ns.config)
        workspace = _workspace(cfg)
        queue = ApprovalQueue(workspace / cfg.governance.approvals_path)
        if ns.approval_cmd == "list":
            print(json.dumps([asdict(rec) for rec in queue.list(ns.status)], indent=2, ensure_ascii=False))
            return 0
        if ns.approval_cmd == "approve":
            print(json.dumps(asdict(queue.decide(ns.id, True, ns.note)), indent=2, ensure_ascii=False))
            return 0
        if ns.approval_cmd == "reject":
            print(json.dumps(asdict(queue.decide(ns.id, False, ns.note)), indent=2, ensure_ascii=False))
            return 0

    if ns.cmd == "doctor":
        cfg = _cfg(ns.config)
        diagnostics = {
            "python": sys.version.split()[0],
            "package": "aegiscode",
            "cli": "aegiscode",
            "config": {
                "workspace": str(cfg.agent.workspace),
                "provider": cfg.provider.default,
                "model": cfg.provider.model,
                "audit_path": str(cfg.governance.audit_path),
                "approvals_path": str(cfg.governance.approvals_path),
                "snapshot_dir": str(cfg.governance.snapshot_dir),
            },
            "tool_count": len(ToolRegistry().describe()),
            "tools": [item["name"] for item in ToolRegistry().describe()],
        }
        print(json.dumps(diagnostics, indent=2, ensure_ascii=False))
        return 0

    if ns.cmd == "auth":
        store = _credential_store()
        auth_cmd = ns.auth_cmd or "status"
        if auth_cmd == "status":
            print(json.dumps(store.status(), indent=2, ensure_ascii=False))
            return 0
        if auth_cmd == "set":
            store.set(ns.name, prompt_secret(f"{ns.name} key: "), prompt_secret("Master password: "))
            print(json.dumps({ns.name: "present"}, indent=2))
            return 0
        if auth_cmd == "get":
            print("present" if store.get(ns.name, prompt_secret("Master password: ")) else "missing")
            return 0
        if auth_cmd == "clear":
            print("cleared" if store.clear(ns.name) else "missing")
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
