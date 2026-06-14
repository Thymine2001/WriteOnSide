from __future__ import annotations

import re
from pathlib import Path

from ..storage import safe_note_name


def unique_note_path(base: Path, suggested: str = "Untitled.md") -> Path:
    base = base.expanduser().resolve()
    name = safe_note_name(suggested)
    path = base / name
    if not path.exists():
        return path
    stem = path.stem
    for number in range(1, 10000):
        candidate = base / f"{stem} {number}.md"
        if not candidate.exists():
            return candidate
    raise OSError("Unable to create unique note name.")


def sanitize_non_markdown_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name).strip().strip(".")
    return cleaned or fallback


def rename_target(path: Path, new_name: str, *, markdown: bool) -> Path:
    if markdown:
        cleaned_name = safe_note_name(new_name)
    else:
        cleaned_name = sanitize_non_markdown_name(new_name, path.name)
    return path.with_name(cleaned_name)
