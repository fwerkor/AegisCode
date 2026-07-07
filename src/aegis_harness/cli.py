from __future__ import annotations
import argparse, json
from pathlib import Path
from .agent import AgentLoop
from .config import HarnessConfig
from .credentials import EncryptedCredentialStore, prompt_secret
from .llm import GitHubModelsClient, MockLLM, OpenAICompatibleClient

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aegis")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run"); run.add_argument("task"); run.add_argument("--config", default="config/aegis.example.toml"); run.add_argument("--workspace", default=None); run.add_argument("--mock-response", action="append", default=[]); run.add_argument("--model", default="gpt-4.1-mini")
    run.add_argument("--provider", choices=["openai", "github"], default="openai")
    cred = sub.add_parser("credential"); cs = cred.add_subparsers(dest="cred_cmd", required=True)
    cs.add_parser("status"); sp = cs.add_parser("set"); sp.add_argument("name"); gp = cs.add_parser("get"); gp.add_argument("name"); cp = cs.add_parser("clear"); cp.add_argument("name")
    return p

def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    if ns.cmd == "credential":
        store = EncryptedCredentialStore(Path.home()/".aegis"/"credential-store.json")
        if ns.cred_cmd == "status": print(json.dumps(store.status(), indent=2)); return 0
        if ns.cred_cmd == "set":
            store.set(ns.name, prompt_secret(f"{ns.name}: "), prompt_secret("Master password: "))
            print(f"stored {ns.name}: present")
            return 0
        if ns.cred_cmd == "get":
            print("present" if store.get(ns.name, prompt_secret("Master password: ")) else "missing")
            return 0
        if ns.cred_cmd == "clear": print("cleared" if store.clear(ns.name) else "missing"); return 0
    if ns.cmd == "run":
        cfg = HarnessConfig.from_file(Path(ns.config)); workspace = Path(ns.workspace) if ns.workspace else cfg.agent.workspace
        llm = MockLLM(ns.mock_response) if ns.mock_response else (GitHubModelsClient(model=ns.model) if ns.provider == "github" else OpenAICompatibleClient(model=ns.model))
        result = AgentLoop(llm, cfg, workspace).run(ns.task)
        print(json.dumps({"completed": result.completed, "stopped_reason": result.stopped_reason, "steps": result.steps, "observations": [o.__dict__ for o in result.observations]}, indent=2, ensure_ascii=False))
        return 0 if result.completed else 2
    return 1
if __name__ == "__main__":
    raise SystemExit(main())
