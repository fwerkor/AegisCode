from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> int:
    run([sys.executable, "scripts/validate_packaging.py"])
    run([sys.executable, "scripts/build_docs.py"])
    run([sys.executable, "-m", "build", "--sdist", "--wheel"])
    artifacts = sorted(str(path) for path in Path("dist").glob("aegiscode-*"))
    if not artifacts:
        raise SystemExit("no release artifacts created")
    print(json.dumps({"release_dry_run": artifacts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
