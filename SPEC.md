# SPEC: Aegis Code Harness

## 1. Problem statement

Modern LLMs can propose coding steps, but a usable coding agent needs a harness around the model. Aegis Code Harness targets individual developers and students who need a small, auditable coding agent kernel that can read and write files, execute commands, run objective validators, stop for human approval on dangerous actions, and remember project conventions across sessions.

The value is that the core mechanisms are code, not instructions hidden in prompts. The project can still run with a mock LLM, which makes its safety and feedback behavior testable.

## 2. User stories

1. As a developer, I can ask the harness to complete a coding task in a workspace so generated changes do not escape the project directory.
2. As a reviewer, I can run mock-LLM tests so the harness mechanisms can be verified without network access.
3. As a cautious user, I can require approval for destructive or publishing actions so the agent cannot mutate external state silently.
4. As a developer, I can configure deterministic validators so syntax errors, test failures, or lint failures are fed back into the next model turn.
5. As a returning user, I can store project conventions in memory so future tasks receive only relevant recalled facts.
6. As a deployer, I can run the project from source or Docker and configure provider credentials without hardcoding keys.
7. As a course evaluator, I can inspect SPEC, PLAN, AGENT_LOG, tests, CI, and mechanism demos as evidence of process and implementation discipline.

## 3. Functional specification

### 3.1 Decision loop

Input: task text, configuration, memory store, LLM client. Behavior: assemble system prompt, task, memory context, and observations; call one LLM completion per turn; parse one JSON action; dispatch the action; collect feedback; append observations; stop on finish, approval requirement, parser exhaustion, or max steps. Output: `RunResult` with completion status, stop reason, step count, observations, and final summary. Errors: invalid JSON becomes a parser observation and is fed back rather than crashing.

### 3.2 Action and tool dispatch

Supported actions: `read_file`, `write_file`, `delete_file`, `shell`, `test`, `remember`, `finish`. Tool paths are resolved under the workspace. Shell and test commands run with captured stdout, stderr, return code, and timeout. Unknown tools return a failed observation.

### 3.3 Feedback

The feedback sensor runs configured commands after selected actions. Each validator returns success, output, command, and return code. Failures are fed back into the message history. This is objective because it comes from process exit status and captured output, not from LLM self-critique.

### 3.4 Governance

The guardrail engine checks path boundaries, publishing operations, infrastructure mutation, device formatting patterns, and explicit file deletion. Some actions are blocked outright; others return `approval_required`. This is deterministic code and tested with constructed actions.

### 3.5 Memory

The memory store persists JSON records with text, tags, id, and timestamp. Retrieval is lexical token/tag overlap. This is intentionally simple, deterministic, and framework-free.

### 3.6 Configuration

TOML configuration controls max steps, workspace, feedback commands, memory path, and guardrail approval behavior.

### 3.7 Credentials

The CLI provides an encrypted local credential store using a master password. Status never reveals secret values. Environment variables are allowed as a fallback for provider adapters but documented as weaker.

### 3.8 WebUI

A minimal WebUI accepts a task and newline-separated mock responses, runs the harness offline, and displays observations. It exists to satisfy the accessible WebUI requirement and demonstrate mechanisms without real API keys.

## 4. Non-functional requirements

Performance: mock runs should complete in seconds; feedback commands are bounded by timeout. Security: keys are never committed, printed, or logged by credential commands. Workspace access is bounded. Dangerous actions require approval. Usability: source, Makefile, Docker, and WebUI entry points are documented. Observability: every step returns structured observations.

## 5. System architecture

```text
Task + Config + Memory
        |
        v
   AgentLoop -----> LLMClient(single completion)
        |                 |
        |           JSON action text
        v
   ActionParser
        |
        v
   GuardrailEngine -- approval/block --> RunResult
        |
        v
   ToolDispatcher ----> Workspace / Shell / Tests
        |
        v
   FeedbackSensor ----> observations back to loop
```

External dependencies: Python standard library, `cryptography` for encrypted credentials, optional OpenAI-compatible chat completion endpoint, Docker for container distribution.

## 6. Data model

`Action`: type plus params. `Observation`: source, success, message, data. `RunResult`: completion state, stop reason, steps, observations, summary. `MemoryRecord`: id, text, tags, created_at. Credential record: name, salt, encrypted token.

## 7. Credential and distribution design

The encrypted credential store is the primary local secret mechanism. It uses PBKDF2-HMAC-SHA256 and Fernet encryption. Users can set, check, and clear keys. Docker distribution runs a non-root user and stores data under `/data`. Source distribution uses `pip install -e .[dev]`.

## 8. Technology choices

Python was chosen because it is fast for a course-scale CLI/WebUI, has mature testing, and can run in GitLab/GitHub CI without heavy setup. TOML is used for configuration because it is in the Python 3.11+ standard library through `tomllib`. The WebUI uses `http.server` to avoid front-end framework overhead.

## 9. Domain and mechanism design

The domain is coding. Tools are file I/O, shell, test execution, memory writing, and finish. Feedback signals are validator commands such as `py_compile`, unit tests, lint, or type checks. Dangerous actions include path escape, deletion, publishing, external deployment, infrastructure mutation, and device formatting. Memory needs include project conventions, historical decisions, and recurring validation commands.

The main contribution is governance plus feedback. Both are code mechanisms. `GuardrailEngine.check(action)` can be tested directly with a constructed action. `FeedbackSensor.collect()` can be tested against a known broken file. `AgentLoop.run()` can be tested with `MockLLM` scripts. Removing the real LLM still leaves deterministic behavior.

## 10. Acceptance criteria

- `make test` passes with no network and no real LLM.
- A mock run can write a file, receive validator feedback, repair the file, and finish.
- A publish-like command produces `approval_required`.
- A path traversal write is blocked.
- Memory records persist and retrieve deterministically.
- Credential status does not reveal secret material.
- Docker image builds and starts WebUI.
- CI includes `unit-test` and container build jobs.

## 11. Risks and open issues

Shell command filtering is never a complete sandbox. Real untrusted code should run in a container or VM with OS-level restrictions. The current memory retrieval is lexical; future work could add embeddings, but that would require careful deterministic fallbacks for tests. Human approval state is represented as a stop condition rather than a full interactive approval server.
