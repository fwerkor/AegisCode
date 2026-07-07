from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


@dataclass
class MockLLM:
    responses: list[str]
    calls: list[list[dict[str, str]]] = field(default_factory=list)

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append([dict(m) for m in messages])
        if not self.responses:
            return json.dumps({"action": {"type": "finish", "summary": "mock script exhausted"}})
        return self.responses.pop(0)


@dataclass
class OpenAICompatibleClient:
    """OpenAI-compatible chat-completions provider adapter."""

    model: str
    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 60

    def complete(self, messages: list[dict[str, str]]) -> str:
        token = self.api_key or os.environ.get("AEGISCODE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not token:
            raise RuntimeError("missing API key: set AEGISCODE_OPENAI_API_KEY or use aegiscode auth set openai")
        endpoint = self.base_url or os.environ.get("AEGISCODE_OPENAI_BASE_URL") or "https://api.openai.com/v1/chat/completions"
        payload = json.dumps({"model": self.model, "messages": messages, "temperature": 0}).encode()
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


@dataclass
class GitHubModelsClient:
    """GitHub Models inference provider adapter."""

    model: str = "openai/gpt-4.1"
    token: str | None = None
    base_url: str = "https://models.github.ai/inference/chat/completions"
    api_version: str = "2026-03-10"
    timeout: int = 60

    def complete(self, messages: list[dict[str, str]]) -> str:
        gh_token = self.token or os.environ.get("AEGISCODE_GITHUB_MODELS_KEY") or os.environ.get("GITHUB_MODELS_KEY")
        if not gh_token:
            raise RuntimeError("missing GitHub Models credential: set AEGISCODE_GITHUB_MODELS_KEY or use aegiscode auth set github")
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
        ).encode()
        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {gh_token}",
                "X-GitHub-Api-Version": self.api_version,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
