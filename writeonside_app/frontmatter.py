from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


FRONT_MATTER_PATTERN = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)


@dataclass(frozen=True)
class NoteMetadata:
    title: str
    tags: tuple[str, ...]
    created: str
    aliases: tuple[str, ...] = ()


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
    if header is None:
        return NoteMetadata(title=title, tags=(), created=created, aliases=())

    collecting_list = ""
    for raw_line in header.splitlines():
        line = raw_line.rstrip()
        if collecting_list:
            item = re.match(r"^\s*-\s+(.+?)\s*$", line)
            if item:
                value = _unquote(item.group(1)).strip()
                if value:
                    (tags if collecting_list == "tags" else aliases).append(value)
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

    unique_tags = tuple(dict.fromkeys(tag for tag in tags if tag))
    unique_aliases = tuple(dict.fromkeys(alias for alias in aliases if alias))
    return NoteMetadata(title=title, tags=unique_tags, created=created, aliases=unique_aliases)


def _yaml_string(value: str) -> str:
    if not value:
        return '""'
    if re.search(r"[:#,\[\]{}&*!|>'\"%@`\n\r\t]", value) or value != value.strip():
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def build_front_matter(title: str, tags: list[str] | tuple[str, ...] = (), created: str | None = None) -> str:
    created = created or date.today().isoformat()
    tag_text = ", ".join(_yaml_string(tag) for tag in tags)
    return (
        "---\n"
        f"title: {_yaml_string(title)}\n"
        f"tags: [{tag_text}]\n"
        f"created: {created}\n"
        "---\n"
    )


def ensure_front_matter(content: str, title: str) -> tuple[str, bool]:
    header, _body = split_front_matter(content)
    if header is not None:
        return content, False
    body = content.lstrip("\ufeff")
    separator = "\n" if body and not body.startswith("\n") else ""
    return build_front_matter(title) + separator + body, True


def note_template(path: Path, body: str = "") -> str:
    body = body.lstrip("\n")
    return build_front_matter(path.stem) + ("\n" + body if body else "\n")
