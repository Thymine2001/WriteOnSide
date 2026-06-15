from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".ico"}
URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)


def split_drop_data(widget, data: str) -> list[str]:
    """Split TkDND data while preserving paths containing spaces."""
    try:
        values = widget.tk.splitlist(data)
    except Exception:
        values = (data,)
    return [str(value).strip() for value in values if str(value).strip()]


def compact_paths(paths: Iterable[Path]) -> list[Path]:
    """Drop selected paths that live inside another selected folder."""
    resolved = sorted({Path(path).resolve() for path in paths}, key=lambda item: len(item.parts))
    compact: list[Path] = []
    for path in resolved:
        if any(path != other and path.is_relative_to(other) for other in compact):
            continue
        compact.append(path)
    return compact


def format_paths_for_drag(paths: Iterable[Path]) -> tuple[str, ...]:
    return tuple(str(path.resolve()) for path in compact_paths(paths))


def local_path_from_drop(value: str) -> Path | None:
    value = value.strip().strip("{}")
    parsed = urlparse(value)
    if parsed.scheme.lower() == "file":
        path = unquote(parsed.path)
        if parsed.netloc:
            path = f"//{parsed.netloc}{path}"
        if re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        return Path(path)
    if URL_PATTERN.match(value):
        return None
    candidate = Path(value)
    return candidate if candidate.exists() else None


def is_url(value: str) -> bool:
    return bool(URL_PATTERN.match(value.strip()))


def is_image_path(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def is_image_url(value: str) -> bool:
    if not is_url(value):
        return False
    return Path(urlparse(value).path).suffix.lower() in IMAGE_SUFFIXES
