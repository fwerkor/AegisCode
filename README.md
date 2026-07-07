# AegisCode

AegisCode is an opencode-style coding-agent CLI with governed local tools, durable subagents, approvals, snapshots, audit logs, provider adapters, and portable releases.

## Install

```bash
pipx install aegiscode
# or
uv tool install aegiscode
# or
npm i -g aegiscode
```

Docker:

```bash
docker run --rm -it -p 8080:8080 -v "$PWD:/workspace" ghcr.io/fwerkor/aegiscode:latest
```

Standalone binaries are published on GitHub Releases for Linux, macOS, and Windows.

## Start

```bash
aegiscode init
aegiscode "fix tests"
aegiscode doctor
```

The shortcut form `aegiscode "fix tests"` is equivalent to `aegiscode run "fix tests"`.

## Common commands

```bash
aegiscode file read README.md
aegiscode shell run python -m pytest -q
aegiscode job start python -m http.server 8000
aegiscode git status
aegiscode subagent pipeline default --task "prepare release"
aegiscode approval list
aegiscode snapshot create --reason "before refactor"
aegiscode todo add "write release notes"
```

## Documentation

Detailed documentation is in `docs/` and on the hosted documentation site:

<https://fwerkor.github.io/AegisCode/>
