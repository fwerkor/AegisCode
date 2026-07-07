# AGENT_LOG

## 2026-07-07 16:00 Task 1 — brainstorming / writing-plans

Context: course requires SPEC, PLAN, process document, mock-LLM tests, CI, credentials, distribution, and WebUI. Decision: choose Coding Agent Harness A and implement the harness kernel directly in Python.

Human intervention: selected a small but complete harness instead of using an agent framework.

## 2026-07-07 16:10 Task 2 — test-driven-development

Prompt/context: implement parser and guardrail tests before implementation. Key expected red tests: invalid JSON rejection, publish-like command approval requirement, path traversal block.

Subagent output summary: parser and guardrail implementation skeletons.

Human intervention: kept pattern set conservative and documented that it is not an OS sandbox.

## 2026-07-07 16:25 Task 3 — subagent-driven-development

Prompt/context: implement tool dispatcher and feedback sensor with deterministic validator observations. Key test: broken Python file triggers failing `py_compile`, next mock action repairs it.

Human intervention: made feedback observations part of the main loop rather than a separate post-run report, so the next LLM turn can react.

## 2026-07-07 16:40 Task 4 — requesting-code-review

Spec compliance review: main loop, mock LLM, tool dispatch, guardrail, feedback, memory, credentials, config, and WebUI are present. Missing or weak point: no real interactive approval execution. Decision: keep as explicit v0.1 limitation; assignment only requires pause/HITL demonstration.

## 2026-07-07 16:55 Task 5 — finishing-a-development-branch

Validation: `make test`, `make demo`, and import checks. CI includes required `.gitlab-ci.yml` job `unit-test` and GitHub Actions equivalent.

Lessons: the smallest useful harness is still mostly engineering around the LLM; the prompt is not the product.
