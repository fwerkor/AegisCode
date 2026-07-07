# Contributing to AegisCode

AegisCode is a local coding-agent runtime with governed tools, durable subagents, approvals, snapshots, and release-ready packaging. Contributions should preserve that contract: useful automation first, explicit safety boundaries always.

## Ways to contribute

- Fix bugs in the CLI, runtime, tool dispatcher, approval flow, subagents, packaging, or documentation.
- Add tests that lock down governance behavior and command-line semantics.
- Improve provider integrations, release artifacts, installers, and CI coverage.
- Report reproducible issues with logs, platform details, and exact commands.

## Development setup

Use Python 3.11 or newer.

```bash
git clone https://github.com/fwerkor/AegisCode.git
cd AegisCode
python -m pip install -e .[dev]
```

Run the normal validation suite before opening a pull request:

```bash
PYTHONPATH=src python -m pytest -q
python -m compileall -q src tests scripts
python scripts/build_docs.py
python scripts/validate_packaging.py
python scripts/validate_release_version.py v0.2.0
```

For packaging changes, also run:

```bash
python -m build --wheel --sdist
```

## Branch and commit style

Use focused branches and small commits. Prefer these prefixes:

- `feat:` for user-visible features.
- `fix:` for bug fixes.
- `test:` for tests.
- `docs:` for documentation.
- `ci:` for workflow changes.
- `chore:` for maintenance.

Keep each commit reviewable. Avoid mixing code, docs, tests, and release metadata unless the change is inherently coupled.

## Pull request checklist

Before submitting a PR, verify:

- The change has a clear issue, motivation, or reproduction case.
- Tests cover the new behavior or regression.
- Governance-sensitive behavior is explicit, especially shell execution, file access, approvals, snapshots, and release publishing.
- Documentation and examples are updated when user-facing commands change.
- Generated build artifacts, caches, logs, credentials, and local `.aegiscode/` state are not committed.

## Governance and safety expectations

AegisCode intentionally separates allowed, denied, and approval-gated actions. Changes must not bypass guardrails for:

- Shell commands, jobs, and persistent shell sessions.
- File reads/writes outside the workspace.
- Browser file URLs or local filesystem access.
- Git commit, push, restore, delete, or process termination flows.
- Snapshot creation and restoration.

When adding a tool or action, update the registry metadata, guardrails, CLI wiring, tests, and docs together.

## Reporting vulnerabilities

Do not file public issues for vulnerabilities. Follow `SECURITY.md`.
