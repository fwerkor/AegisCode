# SPEC: AegisCode

## 1. Goal

AegisCode is an opencode-style coding-agent runtime for normal developer repositories. It provides a single CLI, `aegiscode`, with project initialization, governed local tools, durable subagents, persistent approvals, snapshots, audit logs, provider adapters, a local WebUI, and portable release artifacts.

The core behavior is implemented in this repository and remains testable with `MockLLM`. The model supplies one JSON action per turn; AegisCode owns parsing, validation, tool dispatch, governance, feedback, and stop conditions.

## 2. User-facing commands

```text
aegiscode init
aegiscode run
aegiscode serve
aegiscode subagent list/register/queue/run-next/run-all
aegiscode approval list/approve/reject
aegiscode doctor
aegiscode auth
```

`aegiscode init` creates project-level state:

```text
AGENTS.md
.aegiscode/config.toml
.aegiscode/subagents.json
```

## 3. Provider surface

Supported providers:

- `mock`: deterministic offline scripted responses.
- `openai-compatible`: any chat-completions endpoint compatible with the OpenAI request/response shape.
- `github-models`: GitHub Models inference endpoint.

Provider settings live in `.aegiscode/config.toml` and can be overridden from the CLI. CI and non-interactive runs should use environment variables. Interactive machines may use `aegiscode auth` for encrypted local credentials.

External dependencies: Python standard library, `cryptography` for encrypted credentials, optional OpenAI-compatible chat completion endpoint, optional GitHub Models REST inference endpoint, and Docker for container distribution.

## 4. Tool surface

AegisCode exposes the following governed action families:

```text
file: read_file, write_file, edit_file, patch, delete_file, glob, grep, tree
shell: shell, shell_session_start, shell_session_read, shell_session_send, shell_session_kill, job_start, job_list, job_tail, job_kill
git: git_status, git_diff, git_add, git_commit, git_push, git_branch, git_log
browser/web: browser_text, browser_screenshot, browser_pdf
governance: audit_tail, create_snapshot, restore_snapshot, list_tools
runtime: test, remember, finish
```

All paths are resolved under the configured workspace. Path traversal is blocked before dispatch. High-risk actions can require persistent human approval.

## 5. Governance

The guardrail layer checks the action registry, workspace boundaries, shell policy, explicit approval requirements, and command patterns. If an action needs approval, AegisCode writes a durable record to `.aegiscode/approvals.json` and stops the run with `approval_required`.

Every action start, finish, and failure is appended to `.aegiscode/audit.jsonl`. Sensitive fields are redacted before writing. Mutating actions can create pre-change snapshots under `.aegiscode/snapshots` so the workspace can be restored.

## 6. Subagents

Subagents are named, durable role specifications stored in `.aegiscode/subagents.json`. Default roles are:

- planner
- implementer
- reviewer
- tester
- release

Tasks can be queued and executed sequentially through `aegiscode subagent run-next` or `aegiscode subagent run-all`.

## 7. Feedback and memory

Feedback commands run after selected actions and emit observations back into the next model turn. Typical commands are unit tests, syntax checks, linters, or type checks.

Memory is a local JSON store. Records contain text, tags, id, and timestamp. Retrieval is deterministic lexical/tag matching so tests do not require network or embeddings.

## 8. Release and installation targets

AegisCode release workflows build and upload:

- Python wheel and source distribution
- Linux, macOS, and Windows standalone binaries
- Docker image
- npm wrapper files
- Homebrew formula
- Scoop manifest
- Chocolatey package metadata

Primary install paths are:

```bash
pipx install aegiscode
uv tool install aegiscode
npm i -g aegiscode
```

Standalone binaries are published on GitHub Releases. The optional shell installer is documented as an alternate path, not the primary recommendation.

## 9. CI requirements

CI covers:

- unit tests
- integration tests
- CLI smoke tests
- docs build
- Docker build
- Python package build
- Linux/macOS/Windows binary build matrix
- release artifact workflow
- weekly regression
- Pages docs deploy

## 10. Acceptance criteria

- `python -m pytest -q` passes offline.
- `aegiscode init` creates `AGENTS.md`, `.aegiscode/config.toml`, and `.aegiscode/subagents.json`.
- `aegiscode run` can complete a mock provider run.
- `aegiscode doctor` reports the canonical package and CLI name as `aegiscode`.
- The tool registry includes file, shell, job, git, browser, audit, snapshot, and runtime actions.
- High-risk actions produce durable approval records.
- Docs and workflow names use AegisCode consistently.
