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
COLOR_TAG_STORAGE_NAMES = (
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "cyan",
    "purple",
    "black",
)
COLOR_TAG_LABEL_KEYS = {
    color: f"color.{name}"
    for color, name in zip(COLOR_TAG_PALETTE, COLOR_TAG_STORAGE_NAMES)
}
COLOR_TAG_STORAGE_NAME_BY_COLOR = {
    color: name
    for color, name in zip(COLOR_TAG_PALETTE, COLOR_TAG_STORAGE_NAMES)
}
_COLOR_TAG_ALIASES = {
    "red": "#DE2F24",
    "rot": "#DE2F24",
    "rouge": "#DE2F24",
    "rosso": "#DE2F24",
    "rood": "#DE2F24",
    "vermelho": "#DE2F24",
    "червоний": "#DE2F24",
    "красный": "#DE2F24",
    "लाल": "#DE2F24",
    "빨강": "#DE2F24",
    "빨간색": "#DE2F24",
    "红": "#DE2F24",
    "红色": "#DE2F24",
    "紅": "#DE2F24",
    "紅色": "#DE2F24",
    "orange": "#EBA529",
    "laranja": "#EBA529",
    "arancione": "#EBA529",
    "oranje": "#EBA529",
    "помаранчевий": "#EBA529",
    "оранжевый": "#EBA529",
    "नारंगी": "#EBA529",
    "주황": "#EBA529",
    "주황색": "#EBA529",
    "橙": "#EBA529",
    "橙色": "#EBA529",
    "yellow": "#E8EA45",
    "gelb": "#E8EA45",
    "jaune": "#E8EA45",
    "giallo": "#E8EA45",
    "geel": "#E8EA45",
    "amarelo": "#E8EA45",
    "жовтий": "#E8EA45",
    "желтый": "#E8EA45",
    "желтый": "#E8EA45",
    "पीला": "#E8EA45",
    "노랑": "#E8EA45",
    "노란색": "#E8EA45",
    "黄": "#E8EA45",
    "黄色": "#E8EA45",
    "黃": "#E8EA45",
    "黃色": "#E8EA45",
    "green": "#70B832",
    "gruen": "#70B832",
    "grün": "#70B832",
    "vert": "#70B832",
    "verde": "#70B832",
    "groen": "#70B832",
    "зелений": "#70B832",
    "зеленый": "#70B832",
    "हरा": "#70B832",
    "초록": "#70B832",
    "초록색": "#70B832",
    "녹색": "#70B832",
    "绿": "#70B832",
    "绿色": "#70B832",
    "綠": "#70B832",
    "綠色": "#70B832",
    "blue": "#5175B8",
    "blau": "#5175B8",
    "bleu": "#5175B8",
    "blu": "#5175B8",
    "azul": "#5175B8",
    "синій": "#5175B8",
    "синий": "#5175B8",
    "नीला": "#5175B8",
    "파랑": "#5175B8",
    "파란색": "#5175B8",
    "蓝": "#5175B8",
    "蓝色": "#5175B8",
    "藍": "#5175B8",
    "藍色": "#5175B8",
    "cyan": "#7BC5D4",
    "ciano": "#7BC5D4",
    "cyaan": "#7BC5D4",
    "zcyan": "#7BC5D4",
    "бирюзовий": "#7BC5D4",
    "бирюзовый": "#7BC5D4",
    "голубой": "#7BC5D4",
    "सियान": "#7BC5D4",
    "청록": "#7BC5D4",
    "청록색": "#7BC5D4",
    "青": "#7BC5D4",
    "青色": "#7BC5D4",
    "cyanblue": "#7BC5D4",
    "purple": "#771F77",
    "violett": "#771F77",
    "violet": "#771F77",
    "viola": "#771F77",
    "paars": "#771F77",
    "roxo": "#771F77",
    "фіолетовий": "#771F77",
    "фиолетовый": "#771F77",
    "बैंगनी": "#771F77",
    "보라": "#771F77",
    "보라색": "#771F77",
    "紫": "#771F77",
    "紫色": "#771F77",
    "black": "#070403",
    "schwarz": "#070403",
    "noir": "#070403",
    "nero": "#070403",
    "zwart": "#070403",
    "preto": "#070403",
    "чорний": "#070403",
    "черный": "#070403",
    "काला": "#070403",
    "검정": "#070403",
    "검은색": "#070403",
    "黑": "#070403",
    "黑色": "#070403",
}
MAX_COLOR_TAGS_PER_FILE = 3
TAG_VIEW_MODES = frozenset({"text", "color", "both"})


def normalize_color_name(value: object) -> str:
    return re.sub(r"[\s_\-]+", "", str(value or "").strip().casefold())


def normalize_custom_color(value: object) -> str:
    text = str(value or "").strip()
    color = text.upper()
    if re.fullmatch(r"#[0-9A-F]{6}", color):
        return color
    return _COLOR_TAG_ALIASES.get(normalize_color_name(text), "")


def color_tag_storage_name(color: str) -> str:
    normalized = normalize_custom_color(color)
    return COLOR_TAG_STORAGE_NAME_BY_COLOR.get(normalized, normalized)


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
