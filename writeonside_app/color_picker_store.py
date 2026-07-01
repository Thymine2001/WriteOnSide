from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

PLUGIN_FOLDER = Path("Plugins") / "ColorPicker"
PICK_LINE_RE = re.compile(
    r"^\-\s+`(\d{2}:\d{2}:\d{2})`\s+—\s+<span style=\"color:\s*([^\"]+)\">A</span>\s+`([^`]+)`",
    re.IGNORECASE,
)


def color_picker_day_folder(workspace: Path, day: date | None = None) -> Path:
    day = day or date.today()
    return workspace.resolve() / PLUGIN_FOLDER / day.isoformat()


def color_picker_day_file(workspace: Path, day: date | None = None) -> Path:
    day = day or date.today()
    return color_picker_day_folder(workspace, day) / f"{day.isoformat()}.md"


def normalize_pick_hex(value: str) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", text):
        return text.upper()
    if re.fullmatch(r"#[0-9A-Fa-f]{3}", text):
        return ("#" + "".join(ch * 2 for ch in text[1:])).upper()
    return text.upper()


def format_pick_line(hex_color: str, rgb: tuple[int, int, int], x: int, y: int, *, when: datetime | None = None) -> str:
    when = when or datetime.now()
    hex_color = normalize_pick_hex(hex_color)
    r, g, b = rgb
    return (
        f'- `{when.strftime("%H:%M:%S")}` — '
        f'<span style="color: {hex_color.lower()}">A</span> '
        f"`{hex_color}` · rgb({r}, {g}, {b}) · ({int(x)}, {int(y)})"
    )


def ensure_day_note_header(path: Path, day: date | None = None) -> None:
    day = day or date.today()
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Color Picker {day.isoformat()}\n\n", encoding="utf-8")


def append_color_pick(
    workspace: Path,
    hex_color: str,
    rgb: tuple[int, int, int],
    x: int,
    y: int,
    *,
    when: datetime | None = None,
) -> Path:
    path = color_picker_day_file(workspace)
    ensure_day_note_header(path)
    line = format_pick_line(hex_color, rgb, x, y, when=when)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
    return path


def parse_pick_lines(content: str) -> list[dict[str, str | int]]:
    picks: list[dict[str, str | int]] = []
    for line in content.splitlines():
        match = PICK_LINE_RE.match(line.strip())
        if not match:
            continue
        picks.append(
            {
                "time": match.group(1),
                "hex": normalize_pick_hex(match.group(2)),
                "label_hex": normalize_pick_hex(match.group(3)),
            }
        )
    return list(reversed(picks))
