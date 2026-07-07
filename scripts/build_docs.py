from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

DOCS = Path("docs")
REQUIRED_PAGES = [
    "index.html",
    "quickstart.html",
    "install.html",
    "cli.html",
    "tools.html",
    "subagents.html",
    "providers.html",
    "approvals.html",
    "snapshots.html",
    "release.html",
    "ci.html",
    "security.html",
    "configuration.html",
]
REQUIRED_TEXT = [
    "AegisCode",
    "aegiscode init",
    "aegiscode run",
    "aegiscode serve",
    "aegiscode subagent",
    "aegiscode approval",
    "aegiscode file",
    "aegiscode shell",
    "aegiscode job",
    "aegiscode git",
    "aegiscode snapshot",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag == "a":
            for key, value in attrs:
                if key == "href" and value:
                    self.links.append(value)


def main() -> int:
    missing_pages = [page for page in REQUIRED_PAGES if not (DOCS / page).exists()]
    if missing_pages:
        raise SystemExit({"missing_pages": missing_pages})
    combined = "\n".join((DOCS / page).read_text(encoding="utf-8") for page in REQUIRED_PAGES) + "\n" + Path("README.md").read_text(encoding="utf-8")
    missing_text = [item for item in REQUIRED_TEXT if item not in combined]
    if missing_text:
        raise SystemExit({"missing_text": missing_text})
    broken: list[str] = []
    for page in REQUIRED_PAGES:
        parser = LinkParser()
        parser.feed((DOCS / page).read_text(encoding="utf-8"))
        for href in parser.links:
            if href.startswith(("http://", "https://", "mailto:")) or href.startswith("#"):
                continue
            target = href.split("#", 1)[0]
            if target and not (DOCS / target).exists():
                broken.append(f"{page}: {href}")
    if broken:
        raise SystemExit({"broken_links": broken})
    print("docs ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
