from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def replace_all(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def render(version: str, artifacts: Path, out: Path) -> list[Path]:
    plain_version = version.removeprefix("v")
    out.mkdir(parents=True, exist_ok=True)
    linux = artifacts / "aegiscode-linux-x86_64"
    macos = artifacts / "aegiscode-macos-x86_64"
    windows = artifacts / "aegiscode-windows-x86_64.exe"
    required = [linux, macos, windows]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError({"missing_artifacts": missing})

    checksums = {
        "linux": sha256(linux),
        "macos": sha256(macos),
        "windows": sha256(windows),
    }

    written: list[Path] = []
    checksum_file = out / "SHA256SUMS"
    checksum_file.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(required)) + "\n",
        encoding="utf-8",
    )
    written.append(checksum_file)

    homebrew = Path("packaging/homebrew/aegiscode.rb").read_text(encoding="utf-8")
    homebrew = replace_all(
        homebrew,
        {
            "v0.1.0": version,
            "version \"0.1.0\"": f"version \"{plain_version}\"",
            "PLACEHOLDER": checksums["macos"],
        },
    )
    target = out / "aegiscode.rb"
    target.write_text(homebrew, encoding="utf-8")
    written.append(target)

    scoop = Path("packaging/scoop/aegiscode.json").read_text(encoding="utf-8")
    scoop = replace_all(
        scoop,
        {
            "0.1.0": plain_version,
            "v$version": "v$version",
            "PLACEHOLDER": checksums["windows"],
        },
    )
    target = out / "aegiscode-scoop.json"
    target.write_text(scoop, encoding="utf-8")
    written.append(target)

    choco_dir = out / "chocolatey"
    choco_tools = choco_dir / "tools"
    choco_tools.mkdir(parents=True, exist_ok=True)
    nuspec = Path("packaging/chocolatey/aegiscode.nuspec").read_text(encoding="utf-8")
    nuspec = nuspec.replace("<version>0.1.0</version>", f"<version>{plain_version}</version>")
    (choco_dir / "aegiscode.nuspec").write_text(nuspec, encoding="utf-8")
    written.append(choco_dir / "aegiscode.nuspec")
    ps1 = Path("packaging/chocolatey/tools/chocolateyinstall.ps1").read_text(encoding="utf-8")
    ps1 = replace_all(ps1, {"v0.1.0": version, "PLACEHOLDER": checksums["windows"]})
    (choco_tools / "chocolateyinstall.ps1").write_text(ps1, encoding="utf-8")
    written.append(choco_tools / "chocolateyinstall.ps1")

    shutil.make_archive(str(out / "aegiscode-chocolatey"), "zip", choco_dir)
    written.append(out / "aegiscode-chocolatey.zip")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifacts", default="release-artifacts")
    parser.add_argument("--out", default="release-artifacts")
    ns = parser.parse_args(argv)
    for path in render(ns.version, Path(ns.artifacts), Path(ns.out)):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
