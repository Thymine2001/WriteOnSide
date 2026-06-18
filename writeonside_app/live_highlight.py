from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha1
from typing import Callable, Iterable

from .frontmatter import split_front_matter
from .markdown import HTML_COLOR_MD, normalize_html_color
from .obsidian_md import CALLOUT_LINE, TAG_PATTERN
from .syntax_highlight import code_token_spans
from . import theme

MD_EDITOR_TAGS: tuple[str, ...] = (
    "md_h1",
    "md_h2",
    "md_h3",
    "md_h4",
    "md_h5",
    "md_h6",
    "md_bold",
    "md_italic",
    "md_underline",
    "md_strike",
    "md_highlight",
    "md_sup",
    "md_sub",
    "md_code",
    "md_link",
    "md_image",
    "md_quote",
    "md_list",
    "md_task",
    "md_task_done",
    "md_table",
    "md_hr",
    "md_frontmatter",
    "md_obsidian_tag",
    "md_callout",
    "md_comment",
)

LARGE_FILE_LINE_LIMIT = 2000
PARTIAL_HIGHLIGHT_THRESHOLD = 500
PARTIAL_HIGHLIGHT_MARGIN = 60

INLINE_MD_EDIT = re.compile(
    r"("
    r"<span\b[^>]*style=[\"'][^\"']*\bcolor\s*:\s*[^;\"']+[^\"']*[\"'][^>]*>.*?</span>|"
    r"<font\b[^>]*color\s*=\s*[\"']?[^\"'\s>]+[\"']?[^>]*>.*?</font>|"
    r"!?\[\[[^\[\]\n]+?\]\]|"
    r"!\[[^\]]*\]\([^)]+\)|"
    r"(?<!!)\[[^\]]+\]\([^)]+\)|"
    r"https?://[^\s<>)]+|"
    r"\[\^[^\]]+\]|"
    r"(?<![\w#])#[a-zA-Z][\w/-]*|"
    r"`[^`]+`|"
    r"\*\*[^*]+\*\*|"
    r"~~.+?~~|"
    r"==.+?==|"
    r"<u>.+?</u>|"
    r"<sup>.+?</sup>|"
    r"<sub>.+?</sub>|"
    r"(?<!\*)\*[^*\n]+\*(?!\*)"
    r")",
    re.IGNORECASE,
)

_TASK_LINE = re.compile(r"^\s*[-*+] \[[ xX]\] ")
_TASK_CHECKED = re.compile(r"^\s*[-*+] \[[xX]\] ")
_LIST_LINE = re.compile(r"^(\s*[-*+] |\s*\d+\. )")


@dataclass(frozen=True)
class ColorSpan:
    line: int
    start: int
    end: int
    color: str


@dataclass(frozen=True)
class TagSpan:
    line: int
    start: int
    end: int
    tag: str


@dataclass(frozen=True)
class LineTag:
    line: int
    tag: str


@dataclass(frozen=True)
class LiveHighlightPlan:
    frontmatter_end_line: int
    line_range: tuple[int, int]
    line_tags: tuple[LineTag, ...]
    spans: tuple[TagSpan, ...]
    color_spans: tuple[ColorSpan, ...]
    simplified: bool
    partial: bool


def code_block_active_before(lines: list[str], line_no: int) -> bool:
    active = False
    for index in range(1, line_no):
        if index > len(lines):
            break
        if lines[index - 1].strip().startswith("```"):
            active = not active
    return active


def code_block_context_before(lines: list[str], line_no: int) -> tuple[bool, str]:
    active = False
    language = ""
    for index in range(1, line_no):
        if index > len(lines):
            break
        stripped = lines[index - 1].strip()
        if not stripped.startswith("```"):
            continue
        if active:
            active = False
            language = ""
        else:
            active = True
            language = stripped[3:].strip()
    return active, language


def _inline_tag_for_match(match_text: str) -> str | None:
    if match_text.startswith("![") and "](" in match_text and not match_text.startswith("![["):
        return "md_image"
    if match_text.startswith("[[") or match_text.startswith("![["):
        return "md_link"
    if match_text.startswith("[") and "](" in match_text:
        return "md_link"
    if re.match(r"^https?://", match_text, re.IGNORECASE):
        return "md_link"
    if match_text.startswith("[^"):
        return "md_code"
    if TAG_PATTERN.fullmatch(match_text):
        return "md_obsidian_tag"
    if match_text.startswith("`"):
        return "md_code"
    if match_text.startswith("**"):
        return "md_bold"
    if match_text.startswith("~~"):
        return "md_strike"
    if match_text.startswith("=="):
        return "md_highlight"
    if match_text.lower().startswith("<u>"):
        return "md_underline"
    if match_text.lower().startswith("<sup>"):
        return "md_sup"
    if match_text.lower().startswith("<sub>"):
        return "md_sub"
    if match_text.startswith("*"):
        return "md_italic"
    return None


def _color_span_for_match(line_no: int, line_offset: int, match: re.Match[str]) -> ColorSpan | None:
    color = normalize_html_color(match.group(1) or match.group(3) or "")
    content_group = 2 if match.group(2) is not None else 4
    return ColorSpan(
        line_no,
        line_offset + match.start(content_group),
        line_offset + match.end(content_group),
        color,
    )


def _structure_line_tag(line: str) -> str | None:
    if line.startswith("###### "):
        return "md_h6"
    if line.startswith("##### "):
        return "md_h5"
    if line.startswith("#### "):
        return "md_h4"
    if line.startswith("### "):
        return "md_h3"
    if line.startswith("## "):
        return "md_h2"
    if line.startswith("# "):
        return "md_h1"
    if line.startswith("> "):
        return "md_quote"
    if _TASK_LINE.match(line):
        return "md_task_done" if _TASK_CHECKED.match(line) else "md_task"
    if _LIST_LINE.match(line):
        return "md_list"
    if "|" in line:
        return "md_table"
    return None


def _plan_line(
    line_no: int,
    line: str,
    *,
    in_code_block: bool,
    code_language: str,
    simplified: bool,
) -> tuple[bool, str, list[LineTag], list[TagSpan], list[ColorSpan]]:
    line_tags: list[LineTag] = []
    spans: list[TagSpan] = []
    colors: list[ColorSpan] = []
    stripped = line.strip()

    if stripped.startswith("```"):
        line_tags.append(LineTag(line_no, "md_code"))
        if in_code_block:
            return False, "", line_tags, spans, colors
        return True, stripped[3:].strip(), line_tags, spans, colors
    if in_code_block:
        line_tags.append(LineTag(line_no, "md_code"))
        if not simplified:
            for token_span in code_token_spans(line, code_language, background=theme.CODE_BG, max_chars=8_000):
                colors.append(ColorSpan(line_no, token_span.start, token_span.end, token_span.color))
        return True, code_language, line_tags, spans, colors
    if stripped in {"---", "***", "___"}:
        line_tags.append(LineTag(line_no, "md_hr"))
        return False, "", line_tags, spans, colors
    if CALLOUT_LINE.match(line):
        line_tags.append(LineTag(line_no, "md_callout"))
        return False, "", line_tags, spans, colors
    if "%%" in line:
        line_tags.append(LineTag(line_no, "md_comment"))

    structure_tag = _structure_line_tag(line)
    if structure_tag:
        line_tags.append(LineTag(line_no, structure_tag))

    if simplified:
        return False, "", line_tags, spans, colors

    for match in INLINE_MD_EDIT.finditer(line):
        chunk = match.group(0)
        color_match = HTML_COLOR_MD.fullmatch(chunk)
        if color_match is not None:
            color_span = _color_span_for_match(line_no, match.start(), color_match)
            if color_span is not None:
                colors.append(color_span)
            continue
        tag = _inline_tag_for_match(chunk)
        if tag:
            spans.append(TagSpan(line_no, match.start(), match.end(), tag))

    return False, "", line_tags, spans, colors


def plan_live_highlight(
    content: str,
    *,
    focus_line: int | None = None,
    margin: int = PARTIAL_HIGHLIGHT_MARGIN,
) -> LiveHighlightPlan:
    lines = content.splitlines()
    total_lines = len(lines) or 1
    header, _body = split_front_matter(content)
    frontmatter_lines = content[: len(content) - len(_body)].count("\n") if header is not None else 0
    simplified = total_lines > LARGE_FILE_LINE_LIMIT
    partial = (
        not simplified
        and focus_line is not None
        and total_lines > PARTIAL_HIGHLIGHT_THRESHOLD
    )

    if partial and focus_line is not None:
        start_line = max(frontmatter_lines + 1, focus_line - margin)
        end_line = min(total_lines, focus_line + margin)
    else:
        start_line = 1
        end_line = total_lines

    line_tags: list[LineTag] = []
    spans: list[TagSpan] = []
    colors: list[ColorSpan] = []
    in_code_block, code_language = code_block_context_before(lines, start_line)

    for line_no in range(start_line, end_line + 1):
        if line_no <= frontmatter_lines:
            continue
        line = lines[line_no - 1] if line_no <= len(lines) else ""
        in_code_block, code_language, planned_line_tags, planned_spans, planned_colors = _plan_line(
            line_no,
            line,
            in_code_block=in_code_block,
            code_language=code_language,
            simplified=simplified,
        )
        line_tags.extend(planned_line_tags)
        spans.extend(planned_spans)
        colors.extend(planned_colors)

    return LiveHighlightPlan(
        frontmatter_end_line=frontmatter_lines,
        line_range=(start_line, end_line),
        line_tags=tuple(line_tags),
        spans=tuple(spans),
        color_spans=tuple(colors),
        simplified=simplified,
        partial=partial,
    )


def plan_live_highlight_fragment(
    content: str,
    *,
    start_line: int,
    initial_code_block: bool = False,
    initial_code_language: str = "",
    simplified: bool = True,
) -> LiveHighlightPlan:
    """Plan tags for a bounded editor fragment using absolute line numbers."""
    lines = content.splitlines()
    line_tags: list[LineTag] = []
    spans: list[TagSpan] = []
    colors: list[ColorSpan] = []
    in_code_block = initial_code_block
    code_language = initial_code_language

    for offset, line in enumerate(lines):
        line_no = start_line + offset
        in_code_block, code_language, planned_tags, planned_spans, planned_colors = _plan_line(
            line_no,
            line,
            in_code_block=in_code_block,
            code_language=code_language,
            simplified=simplified,
        )
        line_tags.extend(planned_tags)
        spans.extend(planned_spans)
        colors.extend(planned_colors)

    end_line = start_line + max(0, len(lines) - 1)
    return LiveHighlightPlan(
        frontmatter_end_line=0,
        line_range=(start_line, end_line),
        line_tags=tuple(line_tags),
        spans=tuple(spans),
        color_spans=tuple(colors),
        simplified=simplified,
        partial=True,
    )


def color_tag_name(color: str) -> str:
    digest = sha1(color.casefold().encode("utf-8")).hexdigest()[:12]
    return f"md_color_{digest}"


def apply_live_highlight_plan(
    text_widget,
    plan: LiveHighlightPlan,
    *,
    clear_tags: Iterable[str],
    clear_line_range: tuple[int, int] | None,
    validate_color: Callable[[str], bool],
    configure_color_tag: Callable[[str, str], None],
    editor_color_tags: set[str],
) -> None:
    import tkinter as tk

    if clear_line_range is None:
        for tag in clear_tags:
            text_widget.tag_remove(tag, "1.0", tk.END)
        for tag in list(editor_color_tags):
            text_widget.tag_remove(tag, "1.0", tk.END)
        editor_color_tags.clear()
    else:
        start_line, end_line = clear_line_range
        line_start = f"{start_line}.0"
        line_end = f"{end_line}.end"
        for tag in clear_tags:
            text_widget.tag_remove(tag, line_start, line_end)
        for tag in list(editor_color_tags):
            text_widget.tag_remove(tag, line_start, line_end)

    if plan.frontmatter_end_line:
        text_widget.tag_add("md_frontmatter", "1.0", f"{plan.frontmatter_end_line + 1}.0")

    for line_tag in plan.line_tags:
        text_widget.tag_add(line_tag.tag, f"{line_tag.line}.0", f"{line_tag.line}.end")

    for span in plan.spans:
        text_widget.tag_add(
            span.tag,
            f"{span.line}.{span.start}",
            f"{span.line}.{span.end}",
        )

    for color_span in plan.color_spans:
        if not validate_color(color_span.color):
            continue
        tag = color_tag_name(color_span.color)
        configure_color_tag(tag, color_span.color)
        editor_color_tags.add(tag)
        text_widget.tag_add(
            tag,
            f"{color_span.line}.{color_span.start}",
            f"{color_span.line}.{color_span.end}",
        )
        text_widget.tag_raise(tag)
