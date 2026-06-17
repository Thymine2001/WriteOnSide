"""Prepare README/ folder: move translated readmes and fix relative paths."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_DIR = ROOT / "README"

LANG_NAV_SUB = """<p align="center">
  <strong>Languages:</strong>
  <a href="../README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.pt.md">Português</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.nl.md">Nederlands</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.hi.md">हिन्दी</a> |
  <a href="README.uk.md">Українська</a>
</p>"""

LANG_NAV_PATTERN = re.compile(
    r"<p align=\"center\">\s*<strong>(?:Languages|语言|Idiomas|Sprachen|Langues|Talen|언어|Lingue|भाषाएँ|Мови):</strong>.*?</p>",
    re.DOTALL,
)


def fix_paths(text: str) -> str:
    text = text.replace('src="assets/', 'src="../assets/')
    text = text.replace('](assets/', '](../assets/')
    for name in (
        "requirements.txt",
        "BUILDING.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
    ):
        text = text.replace(f"]({name})", f"](../{name})")
    return text


def main() -> None:
    README_DIR.mkdir(exist_ok=True)
    for name in ("README.zh-CN.md", "README.pt.md"):
        src = ROOT / name
        if not src.exists():
            continue
        body = fix_paths(src.read_text(encoding="utf-8"))
        body = LANG_NAV_PATTERN.sub(LANG_NAV_SUB, body, count=1)
        (README_DIR / name).write_text(body, encoding="utf-8")
        src.unlink()


if __name__ == "__main__":
    main()
