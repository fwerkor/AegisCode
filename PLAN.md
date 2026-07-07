# PLAN: Aegis Code Harness

## Task 1 — Project skeleton and failing tests

Files: `pyproject.toml`, `Makefile`, `tests/test_parser.py`, `tests/test_guardrails.py`. Add package skeleton and tests for JSON action parsing and dangerous action blocking. Verification: run `python -m pytest tests/test_parser.py tests/test_guardrails.py` and first observe failures before implementation.

Status: completed. Commit: to be filled after Git operations.

## Task 2 — Action parser and data model

Files: `src/aegis_harness/actions.py`, `src/aegis_harness/parser.py`. Implement `Action`, `Observation`, `RunResult`, parse JSON and fenced JSON. Verification: parser tests pass.

Status: completed.

## Task 3 — Governance guardrails

Files: `src/aegis_harness/guardrails.py`, `tests/test_guardrails.py`. Implement workspace path checks, dangerous shell patterns, approval requirement, and outright blocks. Verification: guardrail unit tests pass with no LLM.

Status: completed.

## Task 4 — Tool dispatch and feedback sensor

Files: `src/aegis_harness/tools.py`, `src/aegis_harness/feedback.py`, `tests/test_agent_loop.py`. Implement file, shell, test, remember, finish tools and validator observations. Verification: mock LLM creates broken file, feedback fails, next action repairs file, final feedback passes.

Status: completed.

## Task 5 — Agent main loop

Files: `src/aegis_harness/agent.py`, `src/aegis_harness/llm.py`, `tests/test_agent_loop.py`. Implement context assembly, LLM call, parse, guardrail, tool dispatch, feedback, observation回灌, stop conditions. Verification: mock-LLM loop tests pass.

Status: completed.

## Task 6 — Memory and configuration

Files: `src/aegis_harness/memory.py`, `src/aegis_harness/config.py`, `config/aegis.example.toml`, `tests/test_memory.py`. Implement TOML config and JSON memory retrieval. Verification: memory retrieval test passes.

Status: completed.

## Task 7 — Credential safety

Files: `src/aegis_harness/credentials.py`, `src/aegis_harness/cli.py`, `tests/test_credentials.py`. Implement encrypted credential store and CLI status/set/clear/get. Verification: secret is retrievable with password but not visible in status or raw plaintext.

Status: completed.

## Task 8 — WebUI and mechanism demo

Files: `src/aegis_harness/web.py`, `scripts/mechanism_demo.py`. Implement minimal WebUI and deterministic guardrail/feedback/approval demos. Verification: `make demo` and `make web` work.

Status: completed.

## Task 9 — Distribution and CI

Files: `Dockerfile`, `.gitlab-ci.yml`, `.github/workflows/ci.yml`, `README.md`. Add Docker distribution and CI jobs. Verification: `docker build` and CI pass.

Status: completed locally except remote CI pending after push.

## Parallelism and worktree mapping

- Parser/data model and guardrail tests can be developed independently.
- Feedback/tool dispatch depends on action model.
- Agent loop depends on parser, guardrails, tools, feedback, and memory.
- Docs/CI can run in parallel after API stabilizes.

For the final repository, each logical task should map to a small PR or commit. This implementation separates commit history by deliverable groups to preserve reviewability.
