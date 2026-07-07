from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class ToolSpec:
    name: str
    mutates_workspace: bool
    requires_approval: bool
    description: str
    params: list[str]

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self.register(ToolSpec("read_file", False, False, "Read a UTF-8 file inside the workspace", ["path"]))
        self.register(ToolSpec("write_file", True, False, "Write a UTF-8 file inside the workspace", ["path", "content"]))
        self.register(ToolSpec("delete_file", True, True, "Remove a file after HITL approval", ["path"]))
        self.register(ToolSpec("shell", True, False, "Run a bounded shell command in the workspace", ["command", "timeout"]))
        self.register(ToolSpec("test", False, False, "Run a validator command and capture output", ["command", "timeout"]))
        self.register(ToolSpec("remember", False, False, "Persist a project memory record", ["text", "tags"]))
        self.register(ToolSpec("create_snapshot", False, False, "Create a workspace snapshot", ["reason"]))
        self.register(ToolSpec("restore_snapshot", True, True, "Restore a workspace snapshot after HITL approval", ["id"]))
        self.register(ToolSpec("list_tools", False, False, "List available tool capabilities", []))
        self.register(ToolSpec("finish", False, False, "Stop the run with a summary", ["summary"]))

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def describe(self) -> list[dict]:
        return [asdict(spec) for spec in sorted(self._tools.values(), key=lambda item: item.name)]

    def prompt_block(self) -> str:
        return "\n".join(f"- {spec.name}: {spec.description}; params={','.join(spec.params) or 'none'}" for spec in sorted(self._tools.values(), key=lambda item: item.name))
