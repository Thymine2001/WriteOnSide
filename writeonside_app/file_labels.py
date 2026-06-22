from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping
import re


COLOR_TAG_PALETTE = (
    "#DE2F24",
    "#EBA529",
    "#E8EA45",
    "#70B832",
    "#5175B8",
    "#7BC5D4",
    "#771F77",
    "#070403",
)
MAX_COLOR_TAGS_PER_FILE = 3
TAG_VIEW_MODES = frozenset({"text", "color", "both"})


def normalize_custom_color(value: object) -> str:
    color = str(value or "").strip().upper()
    return color if re.fullmatch(r"#[0-9A-F]{6}", color) else ""


def tag_mode_flags(mode: str) -> tuple[bool, bool]:
    return mode in {"text", "both"}, mode in {"color", "both"}


def toggle_tag_mode(mode: str, layer: str) -> str:
    text_enabled, color_enabled = tag_mode_flags(mode)
    if layer == "text":
        text_enabled = not text_enabled
    elif layer == "color":
        color_enabled = not color_enabled
    else:
        return mode if mode in TAG_VIEW_MODES else "text"
    if not text_enabled and not color_enabled:
        return mode if mode in TAG_VIEW_MODES else "text"
    if text_enabled and color_enabled:
        return "both"
    return "text" if text_enabled else "color"


def path_key(path: Path) -> str:
    return str(path.expanduser().resolve())


def normalize_color_list(values: object) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    normalized: list[str] = []
    for value in values:
        color = normalize_custom_color(value)
        if color and color not in normalized:
            normalized.append(color)
        if len(normalized) == MAX_COLOR_TAGS_PER_FILE:
            break
    return normalized


def normalize_file_color_tags(value: object) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, list[str]] = {}
    for raw_path, raw_colors in value.items():
        key = str(raw_path).strip()
        colors = normalize_color_list(raw_colors)
        if key and colors:
            normalized[key] = colors
    return normalized


def normalize_pinned_notes(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    pins: list[str] = []
    seen: set[str] = set()
    for raw_path in value:
        key = str(raw_path).strip()
        folded = key.casefold()
        if key and folded not in seen:
            pins.append(key)
            seen.add(folded)
    return pins


def colors_for_path(file_color_tags: Mapping[str, list[str]], path: Path) -> tuple[str, ...]:
    target = path_key(path).casefold()
    for raw_path, colors in file_color_tags.items():
        if str(raw_path).casefold() == target:
            return tuple(normalize_color_list(colors))
    return ()


def is_path_pinned(pinned_notes: Iterable[str], path: Path) -> bool:
    target = path_key(path).casefold()
    return any(str(raw_path).casefold() == target for raw_path in pinned_notes)


def relocate_path(path: Path, mapping: Mapping[Path, Path]) -> Path:
    resolved = path.expanduser().resolve()
    candidates = sorted(
        ((old.expanduser().resolve(), new.expanduser().resolve()) for old, new in mapping.items()),
        key=lambda pair: len(pair[0].parts),
        reverse=True,
    )
    for old, new in candidates:
        try:
            relative = resolved.relative_to(old)
        except ValueError:
            continue
        return new / relative
    return resolved


def relocate_file_labels(
    file_color_tags: Mapping[str, list[str]],
    pinned_notes: Iterable[str],
    mapping: Mapping[Path, Path],
) -> tuple[dict[str, list[str]], list[str]]:
    colors: dict[str, list[str]] = {}
    for raw_path, raw_colors in file_color_tags.items():
        relocated = relocate_path(Path(raw_path), mapping)
        values = normalize_color_list(raw_colors)
        if values:
            colors[path_key(relocated)] = values
    pins = normalize_pinned_notes(
        [path_key(relocate_path(Path(raw_path), mapping)) for raw_path in pinned_notes]
    )
    return colors, pins


def remove_file_labels_under(
    file_color_tags: Mapping[str, list[str]],
    pinned_notes: Iterable[str],
    removed_path: Path,
) -> tuple[dict[str, list[str]], list[str]]:
    removed = removed_path.expanduser().resolve()

    def retained(raw_path: str) -> bool:
        try:
            Path(raw_path).expanduser().resolve().relative_to(removed)
        except ValueError:
            return True
        return False

    colors = {
        raw_path: normalize_color_list(raw_colors)
        for raw_path, raw_colors in file_color_tags.items()
        if retained(raw_path) and normalize_color_list(raw_colors)
    }
    pins = normalize_pinned_notes([raw_path for raw_path in pinned_notes if retained(raw_path)])
    return colors, pins
