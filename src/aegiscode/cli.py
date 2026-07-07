from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .actions import Action
from .agent import AgentLoop
from .approvals import ApprovalQueue
from .audit import AuditLog
from .config import HarnessConfig
from .credentials import EncryptedCredentialStore, prompt_secret
from .guardrails import GuardrailEngine
from .llm import GitHubModelsClient, MockLLM, OpenAICompatibleClient
from .policy import ShellPolicy
from .project import init_project
from .registry import ToolRegistry
from .snapshots import SnapshotStore
from .subagents import DEFAULT_PIPELINE, SubagentManager, SubagentSpec, SubagentStore
from .tools import ToolDispatcher

KNOWN_COMMANDS = {
    "init", "run", "serve", "subagent", "approval", "doctor", "auth", "file", "shell", "job", "git", "browser", "audit", "snapshot", "todo",
}


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
    reg.add_argument("--description", default="")
    reg.add_argument("--system-hint", default="")
    reg.add_argument("--max-steps", type=int, default=None)
    reg.add_argument("--label", action="append", default=[])
    reg.add_argument("--capability", action="append", default=[])
    reg.add_argument("--workspace", default="")
    reg.add_argument("--provider", default="")
    reg.add_argument("--model", default="")
    reg.add_argument("--priority", type=int, default=0)
    reg.add_argument("--concurrency", type=int, default=1)
    reg.add_argument("--handoff", default="")
    reg.add_argument("--default-next", default="")
    queue = sgs.add_parser("queue")
    queue.add_argument("--agent")
    queue.add_argument("--task")
    queue.add_argument("--priority", type=int, default=None)
    queue.add_argument("--depends-on", action="append", default=[])
    queue.add_argument("--parent-id", default=None)
    queue.add_argument("--max-attempts", type=int, default=1)
    run_next = sgs.add_parser("run-next")
    run_next.add_argument("--agent", default=None)
    run_all = sgs.add_parser("run-all")
    run_all.add_argument("--max-count", type=int, default=None)
    run_all.add_argument("--agent", default=None)
    show = sgs.add_parser("show")
    show.add_argument("id")
    cancel = sgs.add_parser("cancel")
    cancel.add_argument("id")
    retry = sgs.add_parser("retry")
    retry.add_argument("id")
    pipe = sgs.add_parser("pipeline")
    pipe.add_argument("name", choices=["default"])
    pipe.add_argument("--task", default="Run the default AegisCode pipeline")

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

    sub.add_parser("doctor", help="Print installation, config, provider, and tool capability matrix")

    _add_tool_groups(sub)

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


def _add_tool_groups(sub: argparse._SubParsersAction) -> None:
    file_p = sub.add_parser("file", help="Direct workspace file tools")
    fs = file_p.add_subparsers(dest="file_cmd", required=True)
    r = fs.add_parser("read"); r.add_argument("path")
    w = fs.add_parser("write"); w.add_argument("path"); w.add_argument("content", nargs="?"); w.add_argument("--stdin", action="store_true")
    e = fs.add_parser("edit"); e.add_argument("path"); e.add_argument("old"); e.add_argument("new"); e.add_argument("--replace-all", action="store_true")
    pa = fs.add_parser("patch"); pa.add_argument("patch_file", nargs="?", default="-")
    d = fs.add_parser("delete"); d.add_argument("path")
    g = fs.add_parser("glob"); g.add_argument("pattern")
    gr = fs.add_parser("grep"); gr.add_argument("query"); gr.add_argument("--glob", default="*"); gr.add_argument("--literal", action="store_true")
    t = fs.add_parser("tree"); t.add_argument("path", nargs="?", default="."); t.add_argument("--depth", type=int, default=3)

    shell_p = sub.add_parser("shell", help="Direct shell session tools")
    ss = shell_p.add_subparsers(dest="shell_cmd", required=True)
    sr = ss.add_parser("run"); sr.add_argument("command", nargs=argparse.REMAINDER); sr.add_argument("--timeout", type=int, default=20)
    st = ss.add_parser("start"); st.add_argument("command", nargs=argparse.REMAINDER); st.add_argument("--name", default="")
    ss.add_parser("list")
    sread = ss.add_parser("read"); sread.add_argument("id"); sread.add_argument("--lines", type=int, default=200)
    snd = ss.add_parser("send"); snd.add_argument("id"); snd.add_argument("input"); snd.add_argument("--no-enter", action="store_true")
    sk = ss.add_parser("kill"); sk.add_argument("id")

    job_p = sub.add_parser("job", help="Direct long-running job tools")
    js = job_p.add_subparsers(dest="job_cmd", required=True)
    jst = js.add_parser("start"); jst.add_argument("command", nargs=argparse.REMAINDER); jst.add_argument("--name", default="")
    js.add_parser("list")
    jt = js.add_parser("tail"); jt.add_argument("id"); jt.add_argument("--lines", type=int, default=200)
    jk = js.add_parser("kill"); jk.add_argument("id")

    git_p = sub.add_parser("git", help="Direct git tools")
    gs = git_p.add_subparsers(dest="git_cmd", required=True)
    gs.add_parser("status")
    gd = gs.add_parser("diff"); gd.add_argument("--staged", action="store_true")
    ga = gs.add_parser("add"); ga.add_argument("paths", nargs="*")
    gc = gs.add_parser("commit"); gc.add_argument("-m", "--message", required=True)
    gp = gs.add_parser("push"); gp.add_argument("remote", nargs="?", default="origin"); gp.add_argument("branch", nargs="?", default="HEAD")
    gs.add_parser("branch")
    gl = gs.add_parser("log"); gl.add_argument("--limit", type=int, default=20)

    br = sub.add_parser("browser", help="Browser text/screenshot/pdf tools")
    bs = br.add_subparsers(dest="browser_cmd", required=True)
    bt = bs.add_parser("text"); bt.add_argument("url")
    bi = bs.add_parser("screenshot"); bi.add_argument("url"); bi.add_argument("--output", default="screenshot.png")
    bp = bs.add_parser("pdf"); bp.add_argument("url"); bp.add_argument("--output", default="page.pdf")

    audit = sub.add_parser("audit", help="Audit log tools")
    au = audit.add_subparsers(dest="audit_cmd", required=True)
    at = au.add_parser("tail"); at.add_argument("--lines", type=int, default=50)

    snap = sub.add_parser("snapshot", help="Workspace snapshot tools")
    sn = snap.add_subparsers(dest="snapshot_cmd", required=True)
    sc = sn.add_parser("create"); sc.add_argument("--reason", default="manual")
    sn.add_parser("list")
    sres = sn.add_parser("restore"); sres.add_argument("id")

    todo = sub.add_parser("todo", help="Durable project todo tools")
    ts = todo.add_subparsers(dest="todo_cmd", required=True)
    tl = ts.add_parser("list"); tl.add_argument("--status", default=None)
    ta = ts.add_parser("add"); ta.add_argument("content"); ta.add_argument("--priority", default="normal")
    tu = ts.add_parser("update"); tu.add_argument("id"); tu.add_argument("--status", default=None); tu.add_argument("--content", default=None); tu.add_argument("--priority", default=None)
    tr = ts.add_parser("remove"); tr.add_argument("id")


def _cfg(path: str | None) -> HarnessConfig:
    return HarnessConfig.load_default(Path(path) if path else None)


def _workspace(cfg: HarnessConfig, override: str | None = None) -> Path:
    return Path(override) if override else cfg.agent.workspace


def _state_path(workspace: Path, path: Path) -> Path:
    return path if path.is_absolute() else workspace / path


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

    def factory(spec: SubagentSpec):
        return _make_llm(cfg, spec.provider or cfg.provider.default, spec.model or cfg.provider.model, cfg.provider.base_url, mock_responses or [])

    return SubagentManager(store, workspace, cfg, factory)


def _print_json(value: Any) -> int:
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return 0


def _obs_payload(obs) -> dict[str, Any]:
    return {"success": obs.success, "source": obs.source, "message": obs.message, "data": obs.data}


def _direct_action(ns: argparse.Namespace, action: Action) -> int:
    cfg = _cfg(ns.config)
    workspace = _workspace(cfg).resolve()
    audit = AuditLog(_state_path(workspace, cfg.governance.audit_path))
    approvals = ApprovalQueue(_state_path(workspace, cfg.governance.approvals_path))
    registry = ToolRegistry()
    policy = ShellPolicy(
        allow_prefixes=cfg.shell_policy.allow_prefixes,
        approval_patterns=cfg.shell_policy.approval_patterns,
        deny_patterns=cfg.shell_policy.deny_patterns,
        max_command_chars=cfg.shell_policy.max_command_chars,
    )
    guardrails = GuardrailEngine(workspace, cfg.guardrails.require_approval, shell_policy=policy, registry=registry)
    decision = guardrails.check(action)
    if not decision.allowed:
        payload: dict[str, Any] = {"allowed": False, "needs_approval": decision.needs_approval, "action": action.type, "reasons": decision.reasons}
        if decision.needs_approval:
            rec = approvals.submit(action, decision.reasons)
            audit.append("approval.pending", "queued direct tool approval", {"approval": asdict(rec)})
            payload["approval"] = asdict(rec)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 3
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2
    snapshots = SnapshotStore(workspace, cfg.governance.snapshot_dir)
    tools = ToolDispatcher(workspace, audit=audit, snapshots=snapshots, snapshot_before_mutation=cfg.governance.snapshot_before_mutation)
    obs = tools.dispatch(action)
    print(json.dumps(_obs_payload(obs), indent=2, ensure_ascii=False))
    return 0 if obs.success else 1


def _join_remainder(parts: list[str]) -> str:
    return " ".join(parts).strip()


def _tool_action_from_ns(ns: argparse.Namespace) -> Action | None:
    if ns.cmd == "file":
        if ns.file_cmd == "read": return Action("read_file", {"path": ns.path})
        if ns.file_cmd == "write":
            content = sys.stdin.read() if ns.stdin or ns.content is None else ns.content
            return Action("write_file", {"path": ns.path, "content": content})
        if ns.file_cmd == "edit": return Action("edit_file", {"path": ns.path, "old": ns.old, "new": ns.new, "replace_all": ns.replace_all})
        if ns.file_cmd == "patch":
            diff = sys.stdin.read() if ns.patch_file == "-" else Path(ns.patch_file).read_text(encoding="utf-8")
            return Action("patch", {"diff": diff})
        if ns.file_cmd == "delete": return Action("delete_file", {"path": ns.path})
        if ns.file_cmd == "glob": return Action("glob", {"pattern": ns.pattern})
        if ns.file_cmd == "grep": return Action("grep", {"query": ns.query, "glob": ns.glob, "regex": not ns.literal})
        if ns.file_cmd == "tree": return Action("tree", {"path": ns.path, "depth": ns.depth})
    if ns.cmd == "shell":
        if ns.shell_cmd == "run": return Action("shell", {"command": _join_remainder(ns.command), "timeout": ns.timeout})
        if ns.shell_cmd == "start": return Action("shell_session_start", {"command": _join_remainder(ns.command), "name": ns.name})
        if ns.shell_cmd == "list": return Action("shell_session_list", {})
        if ns.shell_cmd == "read": return Action("shell_session_read", {"id": ns.id, "lines": ns.lines})
        if ns.shell_cmd == "send": return Action("shell_session_send", {"id": ns.id, "input": ns.input, "enter": not ns.no_enter})
        if ns.shell_cmd == "kill": return Action("shell_session_kill", {"id": ns.id})
    if ns.cmd == "job":
        if ns.job_cmd == "start": return Action("job_start", {"command": _join_remainder(ns.command), "name": ns.name})
        if ns.job_cmd == "list": return Action("job_list", {})
        if ns.job_cmd == "tail": return Action("job_tail", {"id": ns.id, "lines": ns.lines})
        if ns.job_cmd == "kill": return Action("job_kill", {"id": ns.id})
    if ns.cmd == "git":
        if ns.git_cmd == "status": return Action("git_status", {})
        if ns.git_cmd == "diff": return Action("git_diff", {"staged": ns.staged})
        if ns.git_cmd == "add": return Action("git_add", {"paths": ns.paths or ["."]})
        if ns.git_cmd == "commit": return Action("git_commit", {"message": ns.message})
        if ns.git_cmd == "push": return Action("git_push", {"remote": ns.remote, "branch": ns.branch})
        if ns.git_cmd == "branch": return Action("git_branch", {})
        if ns.git_cmd == "log": return Action("git_log", {"limit": ns.limit})
    if ns.cmd == "browser":
        if ns.browser_cmd == "text": return Action("browser_text", {"url": ns.url})
        if ns.browser_cmd == "screenshot": return Action("browser_screenshot", {"url": ns.url, "output": ns.output})
        if ns.browser_cmd == "pdf": return Action("browser_pdf", {"url": ns.url, "output": ns.output})
    if ns.cmd == "audit" and ns.audit_cmd == "tail": return Action("audit_tail", {"limit": ns.lines})
    if ns.cmd == "snapshot":
        if ns.snapshot_cmd == "create": return Action("create_snapshot", {"reason": ns.reason})
        if ns.snapshot_cmd == "list": return Action("list_snapshots", {})
        if ns.snapshot_cmd == "restore": return Action("restore_snapshot", {"id": ns.id})
    if ns.cmd == "todo":
        if ns.todo_cmd == "list": return Action("todo_list", {"status": ns.status})
        if ns.todo_cmd == "add": return Action("todo_add", {"content": ns.content, "priority": ns.priority})
        if ns.todo_cmd == "update": return Action("todo_update", {"id": ns.id, "status": ns.status, "content": ns.content, "priority": ns.priority})
        if ns.todo_cmd == "remove": return Action("todo_remove", {"id": ns.id})
    return None


def _doctor(ns: argparse.Namespace) -> int:
    cfg = _cfg(ns.config)
    registry = ToolRegistry()
    groups = registry.by_group()
    matrix = {}
    for group, tools in groups.items():
        matrix[group] = [
            {
                "name": item["name"],
                "mutates_workspace": item["mutates_workspace"],
                "requires_approval": item["requires_approval"],
                "params": item["params"],
            }
            for item in tools
        ]
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
        "capabilities": {
            "git": shutil.which("git") is not None,
            "tmux": shutil.which("tmux") is not None,
            "playwright": _module_available("playwright"),
            "docker": shutil.which("docker") is not None,
        },
        "tool_count": len(registry.describe()),
        "tool_matrix": matrix,
        "tools": [item["name"] for item in registry.describe()],
    }
    return _print_json(diagnostics)


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and not args[0].startswith("-") and args[0] not in KNOWN_COMMANDS:
        args = ["run", *args]
    ns = build_parser().parse_args(args)

    action = _tool_action_from_ns(ns)
    if action is not None:
        return _direct_action(ns, action)

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
            return _print_json({name: asdict(spec) for name, spec in manager.store.load_specs().items()})
        if ns.sub_cmd == "register":
            spec = manager.register(SubagentSpec(
                ns.name,
                ns.role,
                ns.system_hint,
                ns.max_steps,
                ns.label,
                ns.description,
                ns.capability,
                ns.workspace,
                ns.provider,
                ns.model,
                ns.priority,
                ns.concurrency,
                ns.handoff,
                ns.default_next,
            ))
            return _print_json(asdict(spec))
        if ns.sub_cmd == "queue":
            if ns.agent and ns.task:
                task = manager.submit(ns.agent, ns.task, priority=ns.priority, depends_on=ns.depends_on, parent_id=ns.parent_id, max_attempts=ns.max_attempts)
                return _print_json(asdict(task))
            return _print_json([asdict(task) for task in manager.store.load_tasks()])
        if ns.sub_cmd == "run-next":
            task = manager.run_next(agent_name=ns.agent)
            return _print_json(asdict(task) if task else None)
        if ns.sub_cmd == "run-all":
            return _print_json([asdict(task) for task in manager.run_all_sequential(max_count=ns.max_count, agent_name=ns.agent)])
        if ns.sub_cmd == "show":
            return _print_json(asdict(manager.show(ns.id)))
        if ns.sub_cmd == "cancel":
            return _print_json(asdict(manager.cancel(ns.id)))
        if ns.sub_cmd == "retry":
            return _print_json(asdict(manager.retry(ns.id)))
        if ns.sub_cmd == "pipeline" and ns.name == "default":
            created = manager.queue_default_pipeline(ns.task)
            return _print_json({"pipeline": DEFAULT_PIPELINE, "tasks": [asdict(task) for task in created]})

    if ns.cmd == "approval":
        cfg = _cfg(ns.config)
        workspace = _workspace(cfg)
        queue = ApprovalQueue(workspace / cfg.governance.approvals_path)
        if ns.approval_cmd == "list":
            return _print_json([asdict(rec) for rec in queue.list(ns.status)])
        if ns.approval_cmd == "approve":
            return _print_json(asdict(queue.decide(ns.id, True, ns.note)))
        if ns.approval_cmd == "reject":
            return _print_json(asdict(queue.decide(ns.id, False, ns.note)))

    if ns.cmd == "doctor":
        return _doctor(ns)

    if ns.cmd == "auth":
        store = _credential_store()
        auth_cmd = ns.auth_cmd or "status"
        if auth_cmd == "status":
            return _print_json(store.status())
        if auth_cmd == "set":
            store.set(ns.name, prompt_secret(f"{ns.name} key: "), prompt_secret("Master password: "))
            return _print_json({ns.name: "present"})
        if auth_cmd == "get":
            print("present" if store.get(ns.name, prompt_secret("Master password: ")) else "missing")
            return 0
        if auth_cmd == "clear":
            print("cleared" if store.clear(ns.name) else "missing")
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
