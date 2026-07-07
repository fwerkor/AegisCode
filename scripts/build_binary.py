from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    dist = Path("dist")
    dist.mkdir(exist_ok=True)
    name = "aegiscode.exe" if sys.platform.startswith("win") else "aegiscode"
    if shutil.which("pyinstaller"):
        entry_dir = Path("build")
        entry_dir.mkdir(exist_ok=True)
        entry = entry_dir / "aegiscode_entry.py"
        entry.write_text("from aegiscode.cli import main\nraise SystemExit(main())\n", encoding="utf-8")
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "--onefile", "--name", "aegiscode", "--collect-all", "aegiscode", str(entry)])
        return 0
    launcher = dist / name
    script = "#!/usr/bin/env sh\nexec python -m aegiscode.cli \"$@\"\n"
    if sys.platform.startswith("win"):
        launcher.write_text("@echo off\r\npython -m aegiscode.cli %*\r\n", encoding="utf-8")
    else:
        launcher.write_text(script, encoding="utf-8")
        launcher.chmod(0o755)
    print(f"created fallback launcher at {launcher}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
