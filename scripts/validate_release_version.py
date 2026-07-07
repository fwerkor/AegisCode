from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    ns = parser.parse_args(argv)
    expected = ns.version.removeprefix("v")
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    init = re.search(r'__version__ = "([^"]+)"', Path("src/aegiscode/__init__.py").read_text(encoding="utf-8"))
    npm = json.loads(Path("packaging/npm-wrapper/package.json").read_text(encoding="utf-8"))["version"]
    values = {"pyproject": pyproject, "__init__": init.group(1) if init else None, "npm-wrapper": npm}
    mismatched = {name: value for name, value in values.items() if value != expected}
    if mismatched:
        raise SystemExit({"expected": expected, "mismatched": mismatched})
    print(f"version ok: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
