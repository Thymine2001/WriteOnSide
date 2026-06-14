from __future__ import annotations

import re

CALLOUT_LINE = re.compile(r"^>\s*\[!([\w+-]+)\]\s*(.*)$", re.IGNORECASE)
TAG_PATTERN = re.compile(r"(?<![\w#])#([a-zA-Z][\w/-]*)")
COMMENT_INLINE = re.compile(r"%%.*?%%", re.DOTALL)
FOOTNOTE_REF = re.compile(r"\[\^([^\]]+)\]")
FOOTNOTE_DEF = re.compile(r"^\[\^([^\]]+)\]:\s*(.+)$")
BLOCK_ID_PATTERN = re.compile(r"(?:^|\s)\^([\w-]+)\s*$")

CALLOUT_LABELS = {
    "note": "Note",
    "abstract": "Abstract",
    "summary": "Summary",
    "tldr": "Summary",
    "info": "Info",
    "todo": "Todo",
    "tip": "Tip",
    "hint": "Tip",
    "important": "Important",
    "success": "Success",
    "check": "Success",
    "done": "Success",
    "question": "Question",
    "help": "Question",
    "faq": "Question",
    "warning": "Warning",
    "caution": "Warning",
    "attention": "Warning",
    "failure": "Failure",
    "fail": "Failure",
    "missing": "Failure",
    "danger": "Danger",
    "error": "Danger",
    "bug": "Bug",
    "example": "Example",
    "quote": "Quote",
    "cite": "Quote",
}


def callout_label(kind: str) -> str:
    return CALLOUT_LABELS.get(kind.casefold(), kind.title())


def strip_obsidian_comments(text: str) -> str:
    return COMMENT_INLINE.sub("", text)


def find_block_line(content: str, block_id: str) -> int | None:
    normalized = block_id.strip().casefold()
    if not normalized:
        return None
    for line_no, line in enumerate(content.splitlines(), start=1):
        match = BLOCK_ID_PATTERN.search(line.rstrip())
        if match and match.group(1).casefold() == normalized:
            return line_no
    return None


def collect_footnote_definitions(lines: list[str]) -> dict[str, str]:
    definitions: dict[str, str] = {}
    for line in lines:
        match = FOOTNOTE_DEF.match(line.strip())
        if match:
            definitions[match.group(1).casefold()] = match.group(2).strip()
    return definitions


def is_footnote_definition_line(line: str) -> bool:
    return bool(FOOTNOTE_DEF.match(line.strip()))
