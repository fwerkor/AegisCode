# SPEC_PROCESS

## Brainstorming key nodes

The initial idea was to build a coding harness rather than a generic application because the course document marks Coding Agent Harness as the preferred option and gives the clearest mechanism requirements. The useful design questions were:

1. Which mechanisms remain testable after removing the real LLM?
2. Which dimension should be deep enough to count as the main contribution?
3. How should credentials be handled without requiring a platform-specific keychain in CI?
4. How can a WebUI exist without turning the project into a front-end-heavy application?
5. What should be treated as deterministic code rather than prompt policy?

## Iteration 1 — From generic agent to coding-specific harness

Original direction: a general task automation agent. Revision: constrain to coding actions: file I/O, shell, tests, memory, finish. This made feedback objective and dangerous actions concrete. The SPEC was changed to list action schemas and validator behavior.

## Iteration 2 — From prompt safety to code safety

Original direction: include a system prompt telling the agent not to run dangerous commands. Revision: add `GuardrailEngine.check(action)` with pattern and path-boundary checks. This changed safety from model compliance to deterministic enforcement.

## Iteration 3 — From real API demo to mock-first demo

Original direction: demo with a real LLM provider. Revision: use `MockLLM` scripts for the mechanism demo. This avoids network and credentials during grading while still allowing a real provider adapter.

## Cold-start validation with a different agent

A cold-start reviewer was simulated by reading only SPEC and PLAN and implementing from the listed files. The main ambiguity exposed was whether human approval should be a complete interactive state machine or a stop condition. The revision made the first version explicit: the harness returns `approval_required`, and future work may add an approval server.

Revision diff summary:

```diff
- Dangerous actions pause for human approval.
+ Dangerous actions return RunResult(stopped_reason="approval_required") in v0.1; approval execution is deliberately outside the mock deterministic demo.
```

Another ambiguity was whether WebUI should call a real LLM. The revision says the WebUI is an offline mock-LLM interface for deterministic demos, while CLI can use a real OpenAI-compatible provider.

## Adopted AI suggestions

- Use a small JSON action protocol rather than free-form tool calls.
- Keep memory lexical so it can be tested deterministically.
- Implement credential storage as a portable encrypted file fallback and document OS keyring as a production alternative.

## Rejected or narrowed suggestions

- Full vector database memory was rejected because it would add dependencies and weaken deterministic grading.
- A full approval server was deferred because a stop condition is enough to demonstrate governance and keep the project scope focused.
- A large React UI was rejected because the course requires an accessible WebUI, not front-end complexity.

## Reflection on brainstorming

Brainstorming was most useful when it forced each mechanism to answer the mock-test question: if the LLM is removed, does the mechanism still exist? It was less useful for process-heavy evidence such as real subagent transcript capture; those artifacts require actual tool-session history and should be maintained during development rather than reconstructed after implementation.
