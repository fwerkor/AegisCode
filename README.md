# Aegis Code Harness

Aegis Code Harness is a small, self-contained Coding Agent Harness. It demonstrates that the reliable part of a coding agent is not a prompt, but an explicit loop around an LLM: context assembly, action parsing, tool dispatch, deterministic governance, feedback sensors, cross-session memory, configuration, credentials, and distribution.

The project deliberately avoids high-level agent orchestration frameworks. The LLM adapter only performs a single chat completion. The agent loop, guardrails, validators, memory retrieval, and stop conditions are implemented in this repository and tested with a mock LLM.

## Installation

```bash
python -m pip install -e .[dev]
make test
```

## Running

Mechanism demos:

```bash
make demo
```

Offline mock run:

```bash
aegis run "create hello.py"   --mock-response '{"action":{"type":"write_file","path":"hello.py","content":"print(42)\n"}}'   --mock-response '{"action":{"type":"finish","summary":"created hello.py"}}'
```

WebUI:

```bash
make web
# open http://127.0.0.1:8080
```

GitHub Models provider run:

```bash
AEGIS_GITHUB_MODELS_KEY=... aegis run "create hello.py" --provider github --model openai/gpt-4.1
```

Mock tests remain the required grading path; the GitHub Models adapter is for real-provider smoke testing and experimentation.

## Distribution

Container build:

```bash
docker build -t aegis-code-harness:local .
docker run --rm -p 8080:8080 -v "$PWD/.aegis-data:/data" aegis-code-harness:local
```

The Docker image runs the WebUI on port 8080 and stores runtime state under `/data`.

## Key security configuration

Real provider calls can use `AEGIS_OPENAI_API_KEY` or `AEGIS_GITHUB_MODELS_KEY`, but the safer local path is the encrypted credential store:

```bash
aegis credential set openai
aegis credential status
aegis credential clear openai
```

`credential status` reports only whether a secret exists. It never prints the key. `.env` files are supported only as an operational fallback through environment variables; they are plaintext and must not be committed.

## Directory structure

```text
src/aegis_harness/     harness kernel
  agent.py            main loop
  parser.py           JSON action parser
  tools.py            file/shell/test tool dispatcher
  guardrails.py       deterministic dangerous-action governance
  feedback.py         validator/sensor execution
  memory.py           framework-free JSON memory store
  credentials.py      encrypted credential storage fallback
  web.py              minimal WebUI
scripts/              deterministic mechanism demonstrations
tests/                mock-LLM unit tests
config/               example TOML configuration
.github/workflows/    GitHub Actions CI
.gitlab-ci.yml        required GitLab unit-test job
```

## Safety boundaries

Aegis confines file tools to the configured workspace. Potentially irreversible actions such as deletion, package publishing, external deployment, and infrastructure mutation require human approval. Path traversal is blocked. Validators and guardrails are deterministic code, so they can be tested without a real LLM.

## Known limits

This is a course-scale harness. It does not implement process isolation stronger than workspace boundaries and command filtering. For untrusted code, run it in a locked-down container or VM. Real LLM use depends on a provider-compatible API key.
