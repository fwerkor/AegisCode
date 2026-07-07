# Security Policy

AegisCode controls local files, shell commands, Git operations, browser artifacts, snapshots, approvals, and long-running jobs. Security reports are treated as high priority when they affect those boundaries.

## Supported versions

Security fixes are applied to the `main` branch first. Pre-release builds may receive fixes through a new pre-release tag when needed.

## What to report

Please report suspected vulnerabilities involving:

- Workspace escape in file, browser, snapshot, or patch tools.
- Shell policy bypasses for direct tools, jobs, persistent sessions, tests, or subagents.
- Approval bypasses for delete, restore, commit, push, process termination, or other high-risk actions.
- Credential disclosure or improper storage of provider credentials.
- Release, installer, Docker, or package-manager supply-chain risks.
- WebUI behavior that exposes local data or runs unintended actions.

## How to report

Do not open a public issue for security problems. Send a private report to the maintainer with:

- Affected commit, release, or branch.
- Operating system and Python version.
- Exact reproduction steps.
- Expected and actual behavior.
- Logs or screenshots with secrets removed.
- Suggested fix, if known.

## Handling expectations

Maintainers should acknowledge valid reports when possible, reproduce the issue, prepare a fix, add regression tests, and publish release notes that describe the impact without exposing unnecessary exploit detail.

## Safe research rules

Do not use a report as authorization to access data, systems, accounts, tokens, repositories, or machines that you do not own or have explicit permission to test.
