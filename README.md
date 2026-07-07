# AegisCode

AegisCode is an opencode-style coding-agent CLI. It provides project initialization, governed file and shell tools, durable subagents, persistent approvals, JSONL audit logs, snapshots, provider adapters, a local WebUI, and portable release artifacts.

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

Standalone binaries are published on GitHub Releases for Linux, macOS, and Windows. Download the matching artifact and put it on your `PATH`.

Optional install script:

```bash
curl -fsSL https://raw.githubusercontent.com/fwerkor/AegisCode/main/scripts/install.sh | sh
```

## Initialize a project

Run this inside the repository you want AegisCode to operate on:

```bash
aegiscode init
```

This creates:

```text
AGENTS.md
.aegiscode/config.toml
.aegiscode/subagents.json
```

`AGENTS.md` stores project-level agent rules. `.aegiscode/config.toml` stores runtime, provider, governance, feedback, and shell-policy settings. `.aegiscode/subagents.json` stores durable subagent roles and queued work.

## Run tasks

Offline mock run:

```bash
aegiscode run "create hello.py" \
  --provider mock \
  --mock-response '{"action":{"type":"write_file","path":"hello.py","content":"print(42)\n"}}' \
  --mock-response '{"action":{"type":"finish","summary":"created hello.py"}}'
```

OpenAI-compatible provider:

```bash
export AEGISCODE_OPENAI_API_KEY=...
aegiscode run "add a pytest for the parser" --provider openai-compatible --model gpt-4.1-mini
```

GitHub Models provider:

```bash
export AEGISCODE_GITHUB_MODELS_KEY=...
aegiscode run "review the current diff" --provider github-models --model openai/gpt-4.1
```

## Local WebUI

Online docs: <https://fwerkor.github.io/AegisCode/>

Local WebUI:

```bash
aegiscode serve
# open http://127.0.0.1:8080
```

## Subagents

Default project initialization includes `planner`, `implementer`, `reviewer`, `tester`, and `release` roles.

```bash
aegiscode subagent list

aegiscode subagent register docs --role documentation --system-hint "Improve user docs and examples."

aegiscode subagent queue --agent planner --task "Plan the release checklist"
aegiscode subagent queue

aegiscode subagent run-next
aegiscode subagent run-all
```

## Approvals

High-risk actions are persisted in `.aegiscode/approvals.json` and can be reviewed later.

```bash
aegiscode approval list
aegiscode approval approve <approval-id> --note "reviewed"
aegiscode approval reject <approval-id> --note "not safe"
```

## Credentials

Use environment variables for CI and non-interactive runs:

```bash
export AEGISCODE_OPENAI_API_KEY=...
export AEGISCODE_GITHUB_MODELS_KEY=...
```

Use the encrypted local credential store for interactive machines:

```bash
aegiscode auth status
aegiscode auth set openai
aegiscode auth set github
aegiscode auth clear openai
```

`auth status` only reports whether a credential exists. It does not print secret values.

## Tool surface

AegisCode exposes a governed local tool surface:

```text
file: read_file, write_file, edit_file, patch, delete_file, glob, grep, tree
shell: shell, shell_session_start, shell_session_read, shell_session_send, shell_session_kill, job_start, job_list, job_tail, job_kill
git: git_status, git_diff, git_add, git_commit, git_push, git_branch, git_log
browser/web: browser_text, browser_screenshot, browser_pdf
governance: audit_tail, create_snapshot, restore_snapshot, list_tools
```

All actions are written to `.aegiscode/audit.jsonl`. Mutating actions can create pre-change snapshots under `.aegiscode/snapshots` so changes can be restored.

## Configuration

Example `.aegiscode/config.toml`:

```toml
[agent]
max_steps = 12
workspace = "."
stop_on_approval_required = true

[provider]
default = "mock"
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1/chat/completions"

[governance]
audit_path = ".aegiscode/audit.jsonl"
approvals_path = ".aegiscode/approvals.json"
snapshot_dir = ".aegiscode/snapshots"
snapshot_before_mutation = true
```

## Diagnostics

```bash
aegiscode doctor
```

`doctor` prints the active package name, CLI name, workspace, provider, governance paths, and registered tools.

## Releases

GitHub Releases publish:

- Python source distribution and wheel
- standalone Linux, macOS, and Windows binaries
- Docker image metadata
- npm wrapper package files
- Homebrew formula
- Scoop manifest
- Chocolatey nuspec

Primary install paths are `pipx install aegiscode`, `uv tool install aegiscode`, and release binaries.
