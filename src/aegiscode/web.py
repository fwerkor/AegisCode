from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from .agent import AgentLoop
from .config import HarnessConfig
from .llm import MockLLM

INDEX = """<!doctype html><html><head><meta charset='utf-8'><title>AegisCode WebUI</title><style>body{font-family:system-ui;margin:2rem;max-width:980px}textarea{width:100%;height:120px}pre{background:#f6f6f6;padding:1rem;white-space:pre-wrap}.card{border:1px solid #ddd;border-radius:10px;padding:1rem;margin:1rem 0}code{background:#f6f6f6;padding:.15rem .25rem;border-radius:.25rem}</style></head><body><h1>AegisCode WebUI</h1><p>Local WebUI for <code>aegiscode serve</code>. It runs the same governed mock action protocol as the CLI.</p><form method='post'><label>Task</label><textarea name='task'>Create hello.py that prints hello.</textarea><label>Mock responses, one JSON action per line</label><textarea name='responses'>{"action":{"type":"write_file","path":"hello.py","content":"print('hello')\n"}}
{"action":{"type":"finish","summary":"done"}}</textarea><button>Run</button></form>__RESULT__</body></html>"""


class Handler(BaseHTTPRequestHandler):
    workspace = Path(".aegiscode/web-workspace")

    def do_GET(self):
        self._send(INDEX.replace("__RESULT__", ""))

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        data = parse_qs(self.rfile.read(length).decode())
        task = data.get("task", [""])[0]
        responses = [line for line in data.get("responses", [""])[0].splitlines() if line.strip()]
        cfg = HarnessConfig.load_default()
        cfg.feedback.commands = []
        result = AgentLoop(MockLLM(responses), cfg, self.workspace).run(task)
        payload = html.escape(json.dumps({"completed": result.completed, "stopped_reason": result.stopped_reason, "observations": [asdict(o) for o in result.observations]}, ensure_ascii=False, indent=2))
        block = f"<div class='card'><h2>Result</h2><pre>{payload}</pre></div>"
        self._send(INDEX.replace("__RESULT__", block))

    def _send(self, body: str):
        raw = body.encode()
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(prog="aegiscode serve")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ns = ap.parse_args(argv)
    ThreadingHTTPServer((ns.host, ns.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
