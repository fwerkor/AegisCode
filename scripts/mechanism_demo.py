from __future__ import annotations
import argparse, json, tempfile
from pathlib import Path
from aegiscode.agent import AgentLoop
from aegiscode.config import HarnessConfig
from aegiscode.llm import MockLLM

def run_case(case: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        cfg = HarnessConfig(); cfg.agent.max_steps = 4; cfg.agent.workspace = Path(td)
        if case == "guardrail":
            llm = MockLLM([json.dumps({"action":{"type":"shell","command":"external-deploy production"}})])
            result = AgentLoop(llm, cfg, Path(td)).run("try a publish-like command")
        elif case == "feedback":
            cfg.feedback.commands = ["python -m py_compile hello.py"]
            llm = MockLLM([
                json.dumps({"action":{"type":"write_file","path":"hello.py","content":"print('broken'\n"}}),
                json.dumps({"action":{"type":"write_file","path":"hello.py","content":"print('fixed')\n"}}),
                json.dumps({"action":{"type":"finish","summary":"feedback repaired syntax"}}),
            ])
            result = AgentLoop(llm, cfg, Path(td)).run("write a valid hello.py")
        elif case == "approval":
            llm = MockLLM([json.dumps({"action":{"type":"delete_file","path":"old.py"}})])
            Path(td, "old.py").write_text("x=1\n")
            result = AgentLoop(llm, cfg, Path(td)).run("delete old file")
        else:
            raise ValueError(case)
        return {"case": case, "completed": result.completed, "stopped_reason": result.stopped_reason, "observations": [o.__dict__ for o in result.observations]}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--case", choices=["all","guardrail","feedback","approval"], default="all")
    ns = ap.parse_args(); cases = ["guardrail","feedback","approval"] if ns.case == "all" else [ns.case]
    print(json.dumps([run_case(c) for c in cases], ensure_ascii=False, indent=2))
if __name__ == "__main__": main()
