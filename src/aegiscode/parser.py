from __future__ import annotations
import json
from typing import Any
from .actions import Action

class ActionParseError(ValueError):
    pass

def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = [line for line in stripped.splitlines() if not line.strip().startswith("```")]
        stripped = "\n".join(lines).strip()
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(stripped[start:end + 1])
            except json.JSONDecodeError:
                raise ActionParseError(f"LLM response is not valid JSON: {exc}") from exc
        else:
            raise ActionParseError(f"LLM response is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ActionParseError("LLM response JSON must be an object")
    return obj

def parse_action(text: str) -> Action:
    obj = _extract_json(text)
    raw_action = obj.get("action", obj)
    if not isinstance(raw_action, dict):
        raise ActionParseError("field 'action' must be an object")
    action_type = raw_action.get("type")
    if not isinstance(action_type, str) or not action_type:
        raise ActionParseError("action.type must be a non-empty string")
    return Action(type=action_type, params={k: v for k, v in raw_action.items() if k != "type"})
