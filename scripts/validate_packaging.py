from __future__ import annotations

import json
import tomllib
from pathlib import Path

REQUIRED = [
    "pyproject.toml",
    "Dockerfile",
    "packaging/npm-wrapper/package.json",
    "packaging/npm-wrapper/bin/aegiscode.js",
    "packaging/homebrew/aegiscode.rb",
    "packaging/scoop/aegiscode.json",
    "packaging/chocolatey/aegiscode.nuspec",
    "scripts/install.sh",
    "scripts/build_binary.py",
]


def main() -> int:
    missing = [path for path in REQUIRED if not Path(path).exists()]
    if missing:
        raise SystemExit({"missing": missing})
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "aegiscode"
    assert project["scripts"]["aegiscode"] == "aegiscode.cli:main"
    npm = json.loads(Path("packaging/npm-wrapper/package.json").read_text(encoding="utf-8"))
    assert npm["name"] == "@fwerkor/aegiscode"
    assert "aegiscode" in npm.get("bin", {})
    print("packaging ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
