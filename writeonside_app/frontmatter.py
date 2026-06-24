from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .file_labels import color_tag_storage_name, normalize_color_list


FRONT_MATTER_PATTERN = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)


@dataclass(frozen=True)
class NoteMetadata:
    title: str
    tags: tuple[str, ...]
    created: str
    aliases: tuple[str, ...] = ()
    color_tags: tuple[str, ...] | None = None
    pinned: bool | None = None


def split_front_matter(content: str) -> tuple[str | None, str]:
    match = FRONT_MATTER_PATTERN.match(content)
    if not match:
        return None, content
    return match.group(1), content[match.end():]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
        return str(parsed)
    return value


def _parse_inline_tags(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    tags = []
    for part in re.split(r"\s*,\s*", value):
        tag = _unquote(part).strip()
        if tag:
            tags.append(tag)
    return tags


def parse_front_matter(content: str, fallback_title: str = "") -> NoteMetadata:
    header, _body = split_front_matter(content)
    title = fallback_title
    created = ""
    tags: list[str] = []
    aliases: list[str] = []
    color_tags: list[str] | None = None
    pinned: bool | None = None
    if header is None:
        return NoteMetadata(title=title, tags=(), created=created, aliases=(), color_tags=None, pinned=None)

    collecting_list = ""
    for raw_line in header.splitlines():
        line = raw_line.rstrip()
        if collecting_list:
            item = re.match(r"^\s*-\s+(.+?)\s*$", line)
            if item:
                value = _unquote(item.group(1)).strip()
                if value:
                    if collecting_list == "tags":
                        tags.append(value)
                    elif collecting_list == "aliases":
                        aliases.append(value)
                    elif color_tags is not None:
                        color_tags.append(value)
                continue
            collecting_list = ""
        match = re.match(r"^\s*([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$", line)
        if not match:
            continue
        key = match.group(1).lower()
        value = match.group(2)
        if key == "title":
            title = _unquote(value).strip() or fallback_title
        elif key == "created":
            created = _unquote(value).strip()
        elif key == "tags":
            if value:
                tags.extend(_parse_inline_tags(value))
            else:
                collecting_list = "tags"
        elif key in {"alias", "aliases"}:
            if value:
                aliases.extend(_parse_inline_tags(value))
            else:
                collecting_list = "aliases"
        elif key == "writeonside_colors":
            color_tags = []
            if value:
                color_tags.extend(_parse_inline_tags(value))
            else:
                collecting_list = "writeonside_colors"
        elif key == "writeonside_pinned":
            normalized = _unquote(value).strip().casefold()
            if normalized in {"true", "yes", "on", "1"}:
                pinned = True
            elif normalized in {"false", "no", "off", "0"}:
                pinned = False

    unique_tags = tuple(dict.fromkeys(tag for tag in tags if tag))
    unique_aliases = tuple(dict.fromkeys(alias for alias in aliases if alias))
    normalized_colors = tuple(normalize_color_list(color_tags)) if color_tags is not None else None
    return NoteMetadata(
        title=title,
        tags=unique_tags,
        created=created,
        aliases=unique_aliases,
        color_tags=normalized_colors,
        pinned=pinned,
    )


def set_writeonside_properties(
    content: str,
    *,
    color_tags: list[str] | tuple[str, ...],
    pinned: bool,
) -> str:
    header, body = split_front_matter(content)
    if header is None:
        return content
    keys = {"writeonside_colors", "writeonside_pinned"}
    retained: list[str] = []
    skipping_list = False
    for line in header.splitlines():
        match = re.match(r"^\s*([A-Za-z_][\w-]*)\s*:", line)
        if match:
            skipping_list = match.group(1).casefold() in keys
            if skipping_list:
                continue
        elif skipping_list and re.match(r"^\s+-\s+", line):
            continue
        else:
            skipping_list = False
        retained.append(line)
    colors = normalize_color_list(color_tags)
    color_value = ", ".join(f'"{color_tag_storage_name(color)}"' for color in colors)
    properties = [
        f"writeonside_colors: [{color_value}]",
        f"writeonside_pinned: {'true' if pinned else 'false'}",
    ]
    insert_at = len(retained)
    for index, line in enumerate(retained):
        if re.match(r"^\s*created\s*:", line, re.IGNORECASE):
            insert_at = index + 1
            break
    updated_header = [*retained[:insert_at], *properties, *retained[insert_at:]]
    return "---\n" + "\n".join(updated_header) + "\n---\n" + body


def _yaml_string(value: str) -> str:
    if not value:
        return '""'
    if re.search(r"[:#,\[\]{}&*!|>'\"%@`\n\r\t]", value) or value != value.strip():
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def build_complete_front_matter(title: str, tags: list[str] | tuple[str, ...] = (), created: str | None = None) -> str:
    created = created or date.today().isoformat()
    tag_text = ", ".join(_yaml_string(tag) for tag in tags)
    return (
        "---\n"
        f"title: {_yaml_string(title)}\n"
        f"tags: [{tag_text}]\n"
        f"created: {created}\n"
        "aliases: []\n"
        "writeonside_colors: []\n"
        "writeonside_pinned: false\n"
        "---\n"
    )


def build_front_matter(title: str, tags: list[str] | tuple[str, ...] = (), created: str | None = None) -> str:
    """Build the canonical WriteOnSide YAML header used by all note creation paths."""
    return build_complete_front_matter(title, tags, created)


def ensure_front_matter(content: str, title: str) -> tuple[str, bool]:
    header, _body = split_front_matter(content)
    if header is not None:
        return content, False
    body = content.lstrip("\ufeff")
    separator = "\n" if body and not body.startswith("\n") else ""
    return build_front_matter(title) + separator + body, True


def ensure_complete_front_matter(content: str, title: str) -> tuple[str, bool]:
    header, body = split_front_matter(content)
    if header is None:
        body = content.lstrip("\ufeff")
        separator = "\n" if body and not body.startswith("\n") else ""
        return build_complete_front_matter(title) + separator + body, True

    existing_keys: set[str] = set()
    for line in header.splitlines():
        match = re.match(r"^\s*([A-Za-z_][\w-]*)\s*:", line)
        if match:
            existing_keys.add(match.group(1).casefold())

    additions: list[str] = []
    if "title" not in existing_keys:
        additions.append(f"title: {_yaml_string(title)}")
    if "tags" not in existing_keys:
        additions.append("tags: []")
    if "created" not in existing_keys:
        additions.append(f"created: {date.today().isoformat()}")
    if "alias" not in existing_keys and "aliases" not in existing_keys:
        additions.append("aliases: []")
    if "writeonside_colors" not in existing_keys:
        additions.append("writeonside_colors: []")
    if "writeonside_pinned" not in existing_keys:
        additions.append("writeonside_pinned: false")
    if not additions:
        return content, False
    updated_header = "\n".join([header.rstrip(), *additions])
    return "---\n" + updated_header + "\n---\n" + body, True


def note_template(path: Path, body: str = "") -> str:
    body = body.lstrip("\n")
    return build_front_matter(path.stem) + ("\n" + body if body else "\n")
