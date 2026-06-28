from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha1
from typing import Callable, Iterable

from .frontmatter import split_front_matter
from .markdown import HTML_COLOR_MD, IMAGE_MD, TASK_LINE, normalize_html_color, task_state_from_marker
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
    "md_live_marker_elide",
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
class MarkerSpan:
    line: int
    start: int
    end: int


@dataclass(frozen=True)
class ReplacementSpan:
    line: int
    start: int
    text: str
    tag: str


@dataclass(frozen=True)
class LiveHighlightPlan:
    frontmatter_end_line: int
    line_range: tuple[int, int]
    line_tags: tuple[LineTag, ...]
    spans: tuple[TagSpan, ...]
    marker_spans: tuple[MarkerSpan, ...]
    replacements: tuple[ReplacementSpan, ...]
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


def _marker_span(line_no: int, start: int, end: int, line_length: int) -> MarkerSpan | None:
    start = max(0, min(start, line_length))
    end = max(0, min(end, line_length))
    if end <= start:
        return None
    return MarkerSpan(line_no, start, end)


def _inline_marker_spans(line_no: int, line: str, match: re.Match[str]) -> list[MarkerSpan]:
    chunk = match.group(0)
    start = match.start()
    end = match.end()
    line_length = len(line)
    spans: list[MarkerSpan] = []

    def add(relative_start: int, relative_end: int) -> None:
        span = _marker_span(line_no, start + relative_start, start + relative_end, line_length)
        if span is not None:
            spans.append(span)

    color_match = HTML_COLOR_MD.fullmatch(chunk)
    if color_match is not None:
        content_group = 2 if color_match.group(2) is not None else 4
        add(0, color_match.start(content_group))
        add(color_match.end(content_group), len(chunk))
        return spans

    if chunk.startswith("**") and len(chunk) >= 4:
        add(0, 2)
        add(len(chunk) - 2, len(chunk))
    elif chunk.startswith(("~~", "==")) and len(chunk) >= 4:
        add(0, 2)
        add(len(chunk) - 2, len(chunk))
    elif chunk.startswith("`") and len(chunk) >= 2:
        add(0, 1)
        add(len(chunk) - 1, len(chunk))
    elif chunk.startswith("*") and len(chunk) >= 2:
        add(0, 1)
        add(len(chunk) - 1, len(chunk))
    elif chunk.lower().startswith("<u>") and chunk.lower().endswith("</u>"):
        add(0, 3)
        add(len(chunk) - 4, len(chunk))
    elif chunk.lower().startswith("<sup>") and chunk.lower().endswith("</sup>"):
        add(0, 5)
        add(len(chunk) - 6, len(chunk))
    elif chunk.lower().startswith("<sub>") and chunk.lower().endswith("</sub>"):
        add(0, 5)
        add(len(chunk) - 6, len(chunk))
    elif chunk.startswith("[") and "](" in chunk:
        close_label = chunk.find("](")
        add(0, 1)
        add(close_label, len(chunk))
    elif chunk.startswith("![") and "](" in chunk:
        close_label = chunk.find("](")
        add(0, 2)
        add(close_label, len(chunk))
    elif chunk.startswith(("[[", "![[")):
        body_start = 3 if chunk.startswith("![[") else 2
        body_end = len(chunk) - 2
        body = chunk[body_start:body_end]
        alias_at = body.rfind("|")
        if alias_at >= 0:
            add(0, body_start + alias_at + 1)
        else:
            add(0, body_start)
        add(body_end, len(chunk))
    return spans


def _line_marker_spans(line_no: int, line: str) -> list[MarkerSpan]:
    line_length = len(line)
    spans: list[MarkerSpan] = []

    def add(start: int, end: int) -> None:
        span = _marker_span(line_no, start, end, line_length)
        if span is not None:
            spans.append(span)

    heading = re.match(r"^(#{1,6})\s+", line)
    if heading:
        add(0, heading.end())
        return spans

    quote = re.match(r"^(\s*>\s?)", line)
    if quote:
        add(0, quote.end())
        return spans

    task = re.match(r"^(\s*(?:-{1,2}|[*+])\s+)(\[[ xX*]\])", line)
    if task:
        suffix_end = task.end(2)
        if suffix_end < line_length and line[suffix_end] == " ":
            suffix_end += 1
        add(0, suffix_end)
        return spans

    bullet = re.match(r"^(\s*[-*+]\s+)", line)
    if bullet:
        add(0, bullet.end())
        return spans

    return spans


def _line_replacement_spans(line_no: int, line: str) -> list[ReplacementSpan]:
    replacements: list[ReplacementSpan] = []
    task = re.match(r"^(\s*)(?:-{1,2}|[*+])\s+\[([ xX*])\](?:\s+|$)", line)
    if task:
        state = task_state_from_marker(task.group(2))
        replacements.append(
            ReplacementSpan(
                line_no,
                len(task.group(1)),
                "☑ " if state == "done" else "☐ ",
                "md_task_done" if state == "done" else "md_task",
            )
        )
        return replacements

    bullet = re.match(r"^(\s*)[-*+]\s+", line)
    if bullet:
        replacements.append(ReplacementSpan(line_no, len(bullet.group(1)), "• ", "md_list"))
    return replacements


def _is_standalone_media_embed_line(line: str) -> bool:
    stripped = line.strip()
    return bool(
        IMAGE_MD.fullmatch(stripped)
        or re.fullmatch(r"!\[\[[^\[\]\n]+?\]\]", stripped)
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
    task_match = TASK_LINE.match(line)
    if task_match:
        return "md_task_done" if task_state_from_marker(task_match.group(1)) == "done" else "md_task"
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
    active_line: int | None = None,
) -> tuple[bool, str, list[LineTag], list[TagSpan], list[MarkerSpan], list[ReplacementSpan], list[ColorSpan]]:
    line_tags: list[LineTag] = []
    spans: list[TagSpan] = []
    marker_spans: list[MarkerSpan] = []
    replacements: list[ReplacementSpan] = []
    colors: list[ColorSpan] = []
    stripped = line.strip()

    if stripped.startswith("```"):
        line_tags.append(LineTag(line_no, "md_code"))
        if in_code_block:
            return False, "", line_tags, spans, marker_spans, replacements, colors
        return True, stripped[3:].strip(), line_tags, spans, marker_spans, replacements, colors
    if in_code_block:
        line_tags.append(LineTag(line_no, "md_code"))
        if not simplified:
            for token_span in code_token_spans(line, code_language, background=theme.CODE_BG, max_chars=8_000):
                colors.append(ColorSpan(line_no, token_span.start, token_span.end, token_span.color))
        return True, code_language, line_tags, spans, marker_spans, replacements, colors
    if stripped in {"---", "***", "___"}:
        line_tags.append(LineTag(line_no, "md_hr"))
        return False, "", line_tags, spans, marker_spans, replacements, colors
    if CALLOUT_LINE.match(line):
        line_tags.append(LineTag(line_no, "md_callout"))
        return False, "", line_tags, spans, marker_spans, replacements, colors
    if "%%" in line:
        line_tags.append(LineTag(line_no, "md_comment"))

    structure_tag = _structure_line_tag(line)
    if structure_tag:
        line_tags.append(LineTag(line_no, structure_tag))

    if simplified:
        return False, "", line_tags, spans, marker_spans, replacements, colors

    skip_live_preview_markers = active_line == line_no or _is_standalone_media_embed_line(line)

    if not skip_live_preview_markers:
        marker_spans.extend(_line_marker_spans(line_no, line))
        replacements.extend(_line_replacement_spans(line_no, line))

    for match in INLINE_MD_EDIT.finditer(line):
        chunk = match.group(0)
        color_match = HTML_COLOR_MD.fullmatch(chunk)
        if color_match is not None:
            color_span = _color_span_for_match(line_no, match.start(), color_match)
            if color_span is not None:
                colors.append(color_span)
            if not skip_live_preview_markers:
                marker_spans.extend(_inline_marker_spans(line_no, line, match))
            continue
        tag = _inline_tag_for_match(chunk)
        if tag:
            spans.append(TagSpan(line_no, match.start(), match.end(), tag))
            if not skip_live_preview_markers:
                marker_spans.extend(_inline_marker_spans(line_no, line, match))

    return False, "", line_tags, spans, marker_spans, replacements, colors


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
    marker_spans: list[MarkerSpan] = []
    replacements: list[ReplacementSpan] = []
    colors: list[ColorSpan] = []
    in_code_block, code_language = code_block_context_before(lines, start_line)

    for line_no in range(start_line, end_line + 1):
        if line_no <= frontmatter_lines:
            continue
        line = lines[line_no - 1] if line_no <= len(lines) else ""
        in_code_block, code_language, planned_line_tags, planned_spans, planned_markers, planned_replacements, planned_colors = _plan_line(
            line_no,
            line,
            in_code_block=in_code_block,
            code_language=code_language,
            simplified=simplified,
            active_line=focus_line,
        )
        line_tags.extend(planned_line_tags)
        spans.extend(planned_spans)
        marker_spans.extend(planned_markers)
        replacements.extend(planned_replacements)
        colors.extend(planned_colors)

    return LiveHighlightPlan(
        frontmatter_end_line=frontmatter_lines,
        line_range=(start_line, end_line),
        line_tags=tuple(line_tags),
        spans=tuple(spans),
        marker_spans=tuple(marker_spans),
        replacements=tuple(replacements),
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
    marker_spans: list[MarkerSpan] = []
    replacements: list[ReplacementSpan] = []
    colors: list[ColorSpan] = []
    in_code_block = initial_code_block
    code_language = initial_code_language

    for offset, line in enumerate(lines):
        line_no = start_line + offset
        in_code_block, code_language, planned_tags, planned_spans, planned_markers, planned_replacements, planned_colors = _plan_line(
            line_no,
            line,
            in_code_block=in_code_block,
            code_language=code_language,
            simplified=simplified,
        )
        line_tags.extend(planned_tags)
        spans.extend(planned_spans)
        marker_spans.extend(planned_markers)
        replacements.extend(planned_replacements)
        colors.extend(planned_colors)

    end_line = start_line + max(0, len(lines) - 1)
    return LiveHighlightPlan(
        frontmatter_end_line=0,
        line_range=(start_line, end_line),
        line_tags=tuple(line_tags),
        spans=tuple(spans),
        marker_spans=tuple(marker_spans),
        replacements=tuple(replacements),
        color_spans=tuple(colors),
        simplified=simplified,
        partial=True,
    )


def color_tag_name(color: str) -> str:
    digest = sha1(color.casefold().encode("utf-8")).hexdigest()[:12]
    return f"md_color_{digest}"


def _clear_live_preview_replacements(text_widget) -> None:
    entries = getattr(text_widget, "_live_preview_replacements", [])
    for entry in entries:
        mark = entry.get("mark") if isinstance(entry, dict) else None
        label = entry.get("label") if isinstance(entry, dict) else None
        if mark:
            try:
                if text_widget.window_cget(mark, "window"):
                    text_widget.delete(mark)
            except Exception:
                pass
            try:
                text_widget.mark_unset(mark)
            except Exception:
                pass
        if label is not None:
            try:
                label.destroy()
            except Exception:
                pass
    try:
        text_widget._live_preview_replacements = []
    except Exception:
        pass


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

    _clear_live_preview_replacements(text_widget)

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

    for marker_span in plan.marker_spans:
        text_widget.tag_add(
            "md_live_marker_elide",
            f"{marker_span.line}.{marker_span.start}",
            f"{marker_span.line}.{marker_span.end}",
        )

    replacements = []
    can_embed = hasattr(text_widget, "window_create")
    if can_embed:
        for index, replacement in enumerate(plan.replacements):
            mark = f"_live_preview_replacement_{index}"
            insert_index = f"{replacement.line}.{replacement.start}"
            try:
                text_widget.mark_set(mark, insert_index)
                text_widget.mark_gravity(mark, tk.LEFT)
                label = tk.Label(
                    text_widget,
                    text=replacement.text,
                    bg=theme.BG,
                    fg=theme.MUTED if replacement.tag == "md_task_done" else theme.TEXT,
                    font=("Segoe UI", 13),
                    padx=0,
                    pady=0,
                    borderwidth=0,
                    highlightthickness=0,
                )
                label.bind(
                    "<Button-1>",
                    lambda _event, idx=insert_index: (
                        text_widget.mark_set(tk.INSERT, idx),
                        text_widget.focus_set(),
                    ),
                )
                text_widget.window_create(mark, window=label)
                replacements.append({"mark": mark, "label": label})
            except tk.TclError:
                try:
                    text_widget.mark_unset(mark)
                except tk.TclError:
                    pass
    try:
        text_widget._live_preview_replacements = replacements
    except Exception:
        pass

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
