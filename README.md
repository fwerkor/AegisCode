<div align="center">

# AegisCode

**An opencode-style coding-agent CLI with governed tools, durable subagents, approvals, snapshots, and release-ready packaging.**

[![Docs](https://img.shields.io/badge/docs-fwerkor.github.io%2FAegisCode-7c3aed?logo=readthedocs&logoColor=white)](https://fwerkor.github.io/AegisCode/)
[![CI](https://github.com/fwerkor/AegisCode/actions/workflows/ci.yml/badge.svg)](https://github.com/fwerkor/AegisCode/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/fwerkor/AegisCode?sort=semver)](https://github.com/fwerkor/AegisCode/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?logo=python&logoColor=white)](https://github.com/fwerkor/AegisCode)
[![Docker](https://img.shields.io/badge/docker-ready-2496ed?logo=docker&logoColor=white)](https://github.com/fwerkor/AegisCode/pkgs/container/aegiscode)
[![CLI](https://img.shields.io/badge/cli-aegiscode-111827)](https://fwerkor.github.io/AegisCode/cli.html)

[Documentation](https://fwerkor.github.io/AegisCode/) · [Quickstart](https://fwerkor.github.io/AegisCode/quickstart.html) · [CLI](https://fwerkor.github.io/AegisCode/cli.html) · [Tools](https://fwerkor.github.io/AegisCode/tools.html) · [Subagents](https://fwerkor.github.io/AegisCode/subagents.html) · [Releases](https://github.com/fwerkor/AegisCode/releases)

</div>

---

`AegisCode` is a local coding-agent runtime designed to feel like `opencode`: run a task from the terminal, let the agent use bounded tools, and keep every high-risk action behind persistent approvals.

```text
User task
  -> aegiscode "fix tests"
  -> governed local tools: file, shell, job, git, browser, audit, snapshot, todo
  -> optional subagent pipeline: planner -> implementer -> tester -> reviewer -> release
  -> durable project state under .aegiscode/
```

## Why use it

| Capability | What it enables |
|---|---|
| opencode-style CLI | `aegiscode "fix tests"` works as the short form of `aegiscode run "fix tests"`. |
| Direct local tools | Read, write, patch, grep, run shell commands, manage jobs, inspect Git, capture browser artifacts, and operate snapshots directly. |
| Durable jobs and sessions | Long-running jobs and shell sessions persist metadata and logs across CLI processes. |
| Subagent pipeline | Queue and run planner, implementer, tester, reviewer, and release agents with priorities and dependencies. |
| Human approvals | High-risk actions such as delete, restore, commit, push, and process termination are queued for explicit approval. |
| Release-ready packaging | CI validates pipx, uv tool, npm wrapper, Docker, standalone binaries, package manifests, and release dry-runs. |

## Install

Recommended Python CLI installation:

```bash
pipx install aegiscode
```

Alternative Python tool installation:

```bash
uv tool install aegiscode
```

Node wrapper:

```bash
npm i -g aegiscode
```

Docker:

```bash
docker run --rm -it -p 8080:8080 -v "$PWD:/workspace" ghcr.io/fwerkor/aegiscode:latest
```

Standalone binaries are published on [GitHub Releases](https://github.com/fwerkor/AegisCode/releases) for Linux, macOS, and Windows.

## Quick start

Initialize AegisCode inside a project:

```bash
aegiscode init
```

Run a task:

```bash
aegiscode "fix tests"
```

The shortcut above is equivalent to:

```bash
aegiscode run "fix tests"
```

Inspect the runtime and tool surface:

```bash
aegiscode doctor
```

Start the local WebUI:

```bash
aegiscode serve
# open http://127.0.0.1:8080
```

## Common CLI commands

```bash
# file tools
aegiscode file read README.md
aegiscode file grep "TODO" --glob "*.py"
aegiscode file tree . --depth 3

# shell and jobs
aegiscode shell run python -m pytest -q
aegiscode job start python -m http.server 8000 --name docs-server
aegiscode job list
aegiscode job tail <job-id>

# git
aegiscode git status
aegiscode git diff
aegiscode git commit -m "feat: update parser"

# governance
aegiscode approval list
aegiscode snapshot create --reason "before refactor"
aegiscode audit tail

# project todos
aegiscode todo add "write release notes" --priority high
aegiscode todo list
```

## Subagents

AegisCode initializes a default pipeline:

```text
planner -> implementer -> tester -> reviewer -> release
```

Queue and run the pipeline:

```bash
aegiscode subagent pipeline default --task "prepare the next release"
aegiscode subagent run-all --max-count 5
```

Manage individual tasks:

```bash
aegiscode subagent queue --agent tester --task "run regression tests" --priority 80
aegiscode subagent show <task-id>
aegiscode subagent retry <task-id>
aegiscode subagent cancel <task-id>
```

## Project state

AegisCode writes durable project state under `.aegiscode/`:

| Path | Purpose |
|---|---|
| `.aegiscode/config.toml` | Agent, provider, feedback, governance, and shell policy settings. |
| `.aegiscode/subagents.json` | Subagent specs, queues, dependencies, retries, and pipeline state. |
| `.aegiscode/approvals.json` | Pending, approved, and rejected high-risk actions. |
| `.aegiscode/audit.jsonl` | Append-only audit trail. |
| `.aegiscode/snapshots/` | Workspace snapshot archives and index. |
| `.aegiscode/runtime/` | Durable job and shell-session metadata. |
| `.aegiscode/logs/` | Runtime output logs. |
| `.aegiscode/todos.json` | Project todo list. |

## Security model

AegisCode exposes powerful local tools. Treat the connected model as having control of the configured workspace.

Default protections include:

- Workspace path containment.
- Shell policy allow, deny, and approval patterns.
- Persistent approval queue for high-risk actions.
- JSONL audit logging with basic redaction.
- Pre-mutation snapshots when enabled.
- Optional Playwright browser artifacts instead of mandatory browser dependencies.

Do not run it against repositories or machines where the agent should not be allowed to modify files.

## Documentation

The README is only the entry point. Detailed references are in the documentation site:

- [Quickstart](https://fwerkor.github.io/AegisCode/quickstart.html)
- [Install](https://fwerkor.github.io/AegisCode/install.html)
- [CLI](https://fwerkor.github.io/AegisCode/cli.html)
- [Tools](https://fwerkor.github.io/AegisCode/tools.html)
- [Subagents](https://fwerkor.github.io/AegisCode/subagents.html)
- [Approvals](https://fwerkor.github.io/AegisCode/approvals.html)
- [Snapshots](https://fwerkor.github.io/AegisCode/snapshots.html)
- [CI](https://fwerkor.github.io/AegisCode/ci.html)
- [Security](https://fwerkor.github.io/AegisCode/security.html)
- [Configuration](https://fwerkor.github.io/AegisCode/configuration.html)

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python -m pytest -q
python scripts/build_docs.py
python scripts/validate_packaging.py
```

Release validation:

```bash
python scripts/release_dry_run.py
```
