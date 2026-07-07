from __future__ import annotations

from pathlib import Path

REQUIRED = ["AegisCode", "aegiscode init", "aegiscode run", "aegiscode serve", "aegiscode subagent", "aegiscode approval"]


def main() -> int:
    docs = Path("docs/index.html")
    readme = Path("README.md")
    text = docs.read_text(encoding="utf-8") + "\n" + readme.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in text]
    if missing:
        raise SystemExit({"missing": missing})
    print("docs ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
