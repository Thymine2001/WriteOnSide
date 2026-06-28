import re
import unicodedata
from pathlib import Path
from typing import Callable
from urllib.parse import unquote
import tkinter as tk
import tkinter.font as tkfont
from PIL import ImageTk

from . import theme
from .frontmatter import split_front_matter
from .obsidian_md import (
    CALLOUT_LINE,
    FOOTNOTE_DEF,
    FOOTNOTE_REF,
    TAG_PATTERN,
    callout_label,
    collect_footnote_definitions,
    is_footnote_definition_line,
    strip_obsidian_comments,
)
from .image_safety import ImageTooLargeError, load_thumbnail_image
from .preview import _is_pdf_path, insert_pdf_preview_block, pdf_page_index_from_fragment
from .syntax_highlight import insert_syntax_highlighted_code_block
from .wikilinks import WIKI_LINK_PATTERN, WikiLink, parse_wiki_links


def _markdown_body_size(widget: tk.Text, font_size: int) -> int:
    width = widget.winfo_width()
    compact = width and width < 360
    return (11 if compact else 12) + (font_size - 10)


def configure_markdown_tags(widget: tk.Text, font_family: str = "Segoe UI", font_size: int = 10) -> None:
    width = widget.winfo_width()
    compact = width and width < 360
    delta = font_size - 10
    h1_size = (15 if compact else 18) + delta
    h2_size = (14 if compact else 16) + delta
    h3_size = (13 if compact else 14) + delta
    body_size = _markdown_body_size(widget, font_size)
    margin = 10 if compact else 18
    list_margin = 16 if compact else 22
    widget.tag_configure("h1", font=(font_family, h1_size, "bold"), foreground=theme.TEXT, spacing3=8)
    widget.tag_configure("h2", font=(font_family, h2_size, "bold"), foreground=theme.TEXT, spacing3=6)
    widget.tag_configure("h3", font=(font_family, h3_size, "bold"), foreground=theme.TEXT, spacing3=5)
    widget.tag_configure("h4", font=(font_family, body_size + 1, "bold"), foreground=theme.TEXT, spacing3=4)
    widget.tag_configure("h5", font=(font_family, body_size, "bold"), foreground=theme.TEXT_SOFT, spacing3=3)
    widget.tag_configure("h6", font=(font_family, body_size, "bold"), foreground=theme.MUTED, spacing3=3)
    widget.tag_configure("bold", font=(font_family, body_size, "bold"), foreground=theme.TEXT)
    widget.tag_configure("italic", font=(font_family, body_size, "italic"), foreground=theme.TEXT)
    widget.tag_configure("underline", underline=True, foreground=theme.TEXT)
    widget.tag_configure("strike", overstrike=True, foreground=theme.TEXT_SOFT)
    widget.tag_configure("highlight", background=theme.HIGHLIGHT_BG, foreground=theme.HIGHLIGHT_FG)
    widget.tag_configure("sup", font=(font_family, max(8, body_size - 2)), offset=4, foreground=theme.TEXT)
    widget.tag_configure("sub", font=(font_family, max(8, body_size - 2)), offset=-3, foreground=theme.TEXT)
    widget.tag_configure("code", font=("Consolas", max(10, body_size)), background=theme.CODE_BG, foreground=theme.CODE_TEXT)
    # Fix #4: code_lang tag for fenced code block language labels
    widget.tag_configure(
        "code_lang",
        font=("Consolas", max(8, body_size - 2)),
        foreground=theme.MUTED,
        background=theme.CODE_BG,
        lmargin1=4,
        lmargin2=4,
    )
    widget.tag_configure("link", foreground=theme.LINK, underline=True)
    widget.tag_configure("quote", foreground=theme.QUOTE, lmargin1=margin, lmargin2=margin)
    widget.tag_configure("list", lmargin1=list_margin, lmargin2=list_margin, foreground=theme.TEXT_SOFT)
    widget.tag_configure("task_done", lmargin1=list_margin, lmargin2=list_margin, foreground=theme.MUTED, overstrike=True)
    widget.tag_configure("table_header", font=("Consolas", max(9, body_size - 1), "bold"), foreground=theme.TEXT)
    widget.tag_configure("table", font=("Consolas", max(9, body_size - 1)), foreground=theme.TEXT_SOFT)
    widget.tag_configure("table_border", font=("Consolas", max(9, body_size - 1)), foreground=theme.MUTED)
    widget.tag_configure("body", font=(font_family, body_size), foreground=theme.TEXT)
    widget.tag_configure("hr", foreground=theme.MUTED)
    widget.tag_configure("obsidian_tag", foreground=theme.ACCENT_2)
    widget.tag_configure("footnote", foreground=theme.MUTED, font=(font_family, max(8, body_size - 1)))
    widget.tag_configure(
        "callout_title",
        font=(font_family, body_size, "bold"),
        background=theme.SURFACE_2,
        foreground=theme.TEXT,
        lmargin1=10,
        lmargin2=10,
        spacing1=4,
    )
    widget.tag_configure(
        "callout_body",
        background=theme.SURFACE_2,
        foreground=theme.TEXT_SOFT,
        lmargin1=18,
        lmargin2=18,
        spacing3=4,
    )
    widget.tag_configure(
        "callout_warning",
        background=theme.HIGHLIGHT_BG,
        foreground=theme.HIGHLIGHT_FG,
    )
    widget.tag_configure(
        "embed_title",
        font=(font_family, body_size, "bold"),
        foreground=theme.ACCENT,
        lmargin1=10,
        lmargin2=10,
        spacing1=4,
    )
    widget.tag_configure(
        "embed_body",
        background=theme.SURFACE,
        foreground=theme.TEXT_SOFT,
        lmargin1=14,
        lmargin2=14,
        spacing3=2,
    )

INLINE_MD = re.compile(
    r"("
    r"<span\b[^>]*style=[\"'][^\"']*\bcolor\s*:\s*[^;\"']+[^\"']*[\"'][^>]*>.*?</span>|"
    r"<font\b[^>]*color\s*=\s*[\"']?[^\"'\s>]+[\"']?[^>]*>.*?</font>|"
    r"!?\[\[[^\[\]\n]+?\]\]|"
    r"!\[[^\]]*\]\([^)]+\)|"
    r"\[[^\]]+\]\([^)]+\)|"
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
    r"\*[^*]+\*"
    r")",
    re.IGNORECASE,
)
IMAGE_MD = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
TASK_LINE = re.compile(r"^\s*[-*+] \[([ xX*])\](?:\s+(.*))?$")
EXTERNAL_URL_MD = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
HTML_COLOR_MD = re.compile(
    r"<span\b[^>]*style=[\"'][^\"']*\bcolor\s*:\s*([^;\"']+)[^\"']*[\"'][^>]*>(.*?)</span>"
    r"|<font\b[^>]*color\s*=\s*[\"']?([^\"'\s>]+)[\"']?[^>]*>(.*?)</font>",
    re.IGNORECASE,
)


def normalize_html_color(color: str) -> str:
    value = color.strip()
    rgb_match = re.fullmatch(
        r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)",
        value,
        re.IGNORECASE,
    )
    if rgb_match:
        channels = [max(0, min(255, int(channel))) for channel in rgb_match.groups()]
        return "#" + "".join(f"{channel:02x}" for channel in channels)
    if re.fullmatch(r"#[0-9a-fA-F]{8}", value):
        return value[:7]
    if re.fullmatch(r"#[0-9a-fA-F]{4}", value):
        return "#" + "".join(character * 2 for character in value[1:4])
    return value


def html_color_parts(chunk: str) -> tuple[str, str] | None:
    match = HTML_COLOR_MD.fullmatch(chunk)
    if not match:
        return None
    color = normalize_html_color(match.group(1) or match.group(3) or "")
    text = match.group(2) if match.group(2) is not None else match.group(4)
    return color, text or ""


def configure_html_color_tag(widget: tk.Text, color: str) -> str | None:
    try:
        widget.winfo_rgb(color)
    except tk.TclError:
        return None
    counter = getattr(widget, "_html_color_tag_counter", 0) + 1
    widget._html_color_tag_counter = counter
    tag = f"html_color_{counter}"
    widget.tag_configure(tag, foreground=color)
    return tag


def _insert_wiki_link(widget: tk.Text, link: WikiLink, base_tag: str) -> None:
    counter = getattr(widget, "_wiki_link_counter", 0) + 1
    widget._wiki_link_counter = counter
    tag = f"wiki_link_{counter}"
    widget.tag_configure(tag, foreground=theme.LINK, underline=True)
    widget._wiki_links[tag] = link
    label = link.label
    if link.embed and not link.block_id:
        label = f"\u21aa {label}"
    widget.insert(tk.END, label, (base_tag, tag))


def _insert_external_link(widget: tk.Text, label: str, url: str, base_tag: str) -> None:
    counter = getattr(widget, "_external_link_counter", 0) + 1
    widget._external_link_counter = counter
    tag = f"external_link_{counter}"
    widget.tag_configure(tag, foreground=theme.LINK, underline=True)
    widget._external_links[tag] = url
    widget.insert(tk.END, label, (base_tag, tag))


def _insert_attachment_link(
    widget: tk.Text,
    label: str,
    raw_path: str,
    base_tag: str,
    base_path: Path | None,
) -> bool:
    path = resolve_markdown_path(raw_path, base_path)
    if path is None or not path.exists() or not path.is_file():
        return False
    counter = getattr(widget, "_attachment_link_counter", 0) + 1
    widget._attachment_link_counter = counter
    tag = f"attachment_link_{counter}"
    widget.tag_configure(tag, foreground=theme.LINK, underline=True)
    widget._attachment_links[tag] = str(path.resolve())
    widget.insert(tk.END, label, (base_tag, tag))
    return True


# Fix #5: added base_path parameter so inline images within paragraphs can be rendered
def insert_inline_md(
    widget: tk.Text,
    text: str,
    base_tag: str = "body",
    base_path: Path | None = None,
) -> None:
    pos = 0
    for match in INLINE_MD.finditer(text):
        if match.start() > pos:
            widget.insert(tk.END, text[pos : match.start()], base_tag)
        chunk = match.group(0)
        if chunk.startswith("`"):
            widget.insert(tk.END, chunk[1:-1], "code")
        elif chunk.startswith("**"):
            widget.insert(tk.END, chunk[2:-2], "bold")
        elif chunk.startswith("~~"):
            widget.insert(tk.END, chunk[2:-2], "strike")
        elif chunk.startswith("=="):
            widget.insert(tk.END, chunk[2:-2], "highlight")
        elif chunk.lower().startswith("<u>"):
            widget.insert(tk.END, chunk[3:-4], "underline")
        elif chunk.lower().startswith("<sup>"):
            widget.insert(tk.END, chunk[5:-6], "sup")
        elif chunk.lower().startswith("<sub>"):
            widget.insert(tk.END, chunk[5:-6], "sub")
        elif chunk.startswith("*"):
            widget.insert(tk.END, chunk[1:-1], "italic")
        elif WIKI_LINK_PATTERN.fullmatch(chunk):
            links = parse_wiki_links(chunk)
            if links:
                _insert_wiki_link(widget, links[0], base_tag)
            else:
                widget.insert(tk.END, chunk, base_tag)
        elif EXTERNAL_URL_MD.match(chunk):
            _insert_external_link(widget, chunk, chunk, base_tag)
        elif chunk.startswith("!["):
            # Fix #5: attempt to render inline images; fall back to raw text
            img_match = IMAGE_MD.fullmatch(chunk)
            if img_match and base_path is not None:
                if not insert_markdown_image(widget, img_match.group(1), img_match.group(2), base_path):
                    widget.insert(tk.END, chunk, base_tag)
            else:
                widget.insert(tk.END, chunk, base_tag)
        elif chunk.startswith("[") and not chunk.startswith("[^"):
            link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", chunk)
            if link and EXTERNAL_URL_MD.match(link.group(2).strip()):
                _insert_external_link(widget, link.group(1), link.group(2).strip(), base_tag)
            elif link and _insert_attachment_link(
                widget,
                link.group(1),
                link.group(2).strip(),
                base_tag,
                base_path,
            ):
                pass
            else:
                widget.insert(tk.END, link.group(1) if link else chunk, "link" if link else base_tag)
        elif chunk.startswith("[^"):
            widget.insert(tk.END, chunk, ("footnote", "sup"))
        elif TAG_PATTERN.fullmatch(chunk):
            widget.insert(tk.END, chunk, ("obsidian_tag", base_tag))
        elif chunk.lower().startswith(("<span", "<font")):
            parts = html_color_parts(chunk)
            if parts:
                color, inner = parts
                color_tag = configure_html_color_tag(widget, color)
                tags: str | tuple[str, ...] = (base_tag, color_tag) if color_tag else base_tag
                widget.insert(tk.END, inner, tags)
            else:
                widget.insert(tk.END, chunk, base_tag)
        pos = match.end()
    if pos < len(text):
        widget.insert(tk.END, text[pos:], base_tag)


def parse_table_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith(r"\|"):
        value = value[:-1]
    cells: list[str] = []
    current: list[str] = []
    in_code = False
    index = 0
    while index < len(value):
        character = value[index]
        if character == "\\" and index + 1 < len(value) and value[index + 1] in {"|", "\\"}:
            current.append(value[index + 1])
            index += 2
            continue
        if character == "`":
            in_code = not in_code
            current.append(character)
            index += 1
            continue
        if character == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(character)
        index += 1
    cells.append("".join(current).strip())
    return cells


def is_table_separator(line: str) -> bool:
    cells = parse_table_row(line)
    return len(cells) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


# Fix #3: extract column alignments from the separator row
def parse_table_alignment(line: str) -> list[str]:
    alignments = []
    for cell in parse_table_row(line):
        stripped = cell.strip()
        if stripped.startswith(":") and stripped.endswith(":"):
            alignments.append("center")
        elif stripped.endswith(":"):
            alignments.append("right")
        else:
            alignments.append("left")
    return alignments


def _plain_table_cell(value: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!?\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]", lambda match: match.group(2) or match.group(1), text)
    text = re.sub(r"</?(?:u|sup|sub|span|font)\b[^>]*>", "", text, flags=re.IGNORECASE)
    for marker in ("**", "__", "~~", "==", "`"):
        text = text.replace(marker, "")
    return text.strip()


def _display_width(value: str) -> int:
    width = 0
    for character in value:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
    return width


def _truncate_display(value: str, width: int) -> str:
    if _display_width(value) <= width:
        return value
    if width <= 3:
        return "." * width
    target = width - 3
    result: list[str] = []
    used = 0
    for character in value:
        char_width = 0 if unicodedata.combining(character) else 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
        if used + char_width > target:
            break
        result.append(character)
        used += char_width
    return "".join(result) + "..."


def _pad_table_cell(value: str, width: int, alignment: str) -> str:
    value = _truncate_display(value, width)
    padding = max(0, width - _display_width(value))
    if alignment == "right":
        return " " * padding + value
    if alignment == "center":
        left = padding // 2
        return " " * left + value + " " * (padding - left)
    return value + " " * padding


def format_table_lines(
    rows: list[list[str]],
    alignments: list[str] | None = None,
    *,
    max_width: int = 80,
) -> list[tuple[str, str]]:
    if not rows:
        return []
    column_count = max(len(row) for row in rows)
    normalized = [
        [_plain_table_cell(row[index]) if index < len(row) else "" for index in range(column_count)]
        for row in rows
    ]
    alignments = list(alignments or []) + ["left"] * column_count
    widths = [max(3, max(_display_width(row[index]) for row in normalized)) for index in range(column_count)]
    available_cells = max(column_count * 3, max_width - (3 * column_count + 1))
    while sum(widths) > available_cells:
        widest = max(range(column_count), key=lambda index: widths[index])
        if widths[widest] <= 3:
            break
        widths[widest] -= 1

    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    result: list[tuple[str, str]] = [(border, "table_border")]
    for row_index, row in enumerate(normalized):
        cells = [
            _pad_table_cell(row[index], widths[index], alignments[index])
            for index in range(column_count)
        ]
        result.append(("| " + " | ".join(cells) + " |", "table_header" if row_index == 0 else "table"))
        if row_index == 0:
            result.append((border, "table_border"))
    if len(normalized) > 1:
        result.append((border, "table_border"))
    return result


def insert_table(
    widget: tk.Text,
    rows: list[list[str]],
    alignments: list[str] | None = None,
    font_size: int = 10,
) -> None:
    if not rows:
        return
    width = widget.winfo_width()
    if width > 100:
        font = tkfont.Font(widget, font=("Consolas", max(9, font_size)))
        max_width = max(24, (width - 28) // max(1, font.measure("0")))
    else:
        max_width = 80
    for line, tag in format_table_lines(rows, alignments, max_width=max_width):
        widget.insert(tk.END, line + "\n", tag)
    widget.insert(tk.END, "\n")


def resolve_markdown_path(raw: str, base_path: Path | None) -> Path | None:
    target = unquote(raw.strip().strip("<>"))
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
        return None
    target = re.split(r"(?<!^)[#?]", target, maxsplit=1)[0]
    path = Path(target)
    if not path.is_absolute() and base_path:
        path = base_path.parent / path
    return path


def insert_markdown_image(widget: tk.Text, alt: str, raw_path: str, base_path: Path | None) -> bool:
    path = resolve_markdown_path(raw_path, base_path)
    if not path or not path.exists() or not path.is_file():
        return False
    if _is_pdf_path(path):
        return insert_pdf_preview_block(widget, path, initial_page=pdf_page_index_from_fragment(raw_path))
    try:
        max_w = max(180, widget.winfo_width() - 48)
        img = load_thumbnail_image(path, (max_w, max_w * 4))
        photo = ImageTk.PhotoImage(img)
    except (OSError, ImageTooLargeError):
        return False
    if not hasattr(widget, "_markdown_images"):
        widget._markdown_images = []
    if not hasattr(widget, "_clickable_images"):
        widget._clickable_images = {}
    widget._markdown_images.append(photo)
    image_name = widget.image_create(tk.END, image=photo)
    widget._clickable_images[str(image_name)] = str(path.resolve())
    widget.insert(tk.END, f"\n{alt}\n" if alt else "\n")
    return True


def task_state_from_marker(marker: str) -> str:
    return "open" if marker == " " else "done"


def task_prefix_for_state(state: str) -> str:
    if state == "done":
        return "☑ "
    return "☐ "


def insert_note_embed(
    widget: tk.Text,
    title: str,
    body: str,
    base_path: Path | None,
    font_family: str,
    font_size: int,
) -> None:
    widget.insert(tk.END, f"▎ {title}\n", "embed_title")
    for body_line in body.splitlines():
        cleaned = strip_obsidian_comments(body_line)
        if not cleaned.strip():
            widget.insert(tk.END, "\n")
            continue
        insert_inline_md(widget, cleaned + "\n", "embed_body", base_path)
    widget.insert(tk.END, "\n")


def insert_callout(
    widget: tk.Text,
    kind: str,
    title: str,
    body_lines: list[str],
    base_path: Path | None,
) -> None:
    label = callout_label(kind)
    heading = f"{label}: {title}".strip(": ") if title else label
    title_tags = ("callout_title", "callout_warning") if kind.casefold() in {"warning", "caution", "danger", "error"} else ("callout_title",)
    widget.insert(tk.END, heading + "\n", title_tags)
    for body_line in body_lines:
        cleaned = strip_obsidian_comments(body_line)
        if not cleaned.strip():
            widget.insert(tk.END, "\n", "callout_body")
            continue
        insert_inline_md(widget, cleaned + "\n", "callout_body", base_path)
    widget.insert(tk.END, "\n")


def render_markdown(
    widget: tk.Text,
    content: str,
    base_path: Path | None = None,
    font_family: str = "Segoe UI",
    font_size: int = 10,
    wiki_asset_resolver: Callable[[str, Path | None], Path | None] | None = None,
    wiki_note_resolver: Callable[[str, Path | None], tuple[str, str] | None] | None = None,
) -> None:
    widget.config(state=tk.NORMAL)
    for child in getattr(widget, "_file_preview_windows", []):
        try:
            child.destroy()
        except tk.TclError:
            pass
    widget.delete("1.0", tk.END)
    widget._markdown_images = []
    widget._file_preview_images = []
    widget._file_preview_windows = []
    widget._clickable_images = {}
    widget._wiki_links = {}
    widget._wiki_link_counter = 0
    widget._external_links = {}
    widget._external_link_counter = 0
    widget._attachment_links = {}
    widget._attachment_link_counter = 0
    widget._html_color_tag_counter = 0
    configure_markdown_tags(widget, font_family, font_size)
    body_size = _markdown_body_size(widget, font_size)
    # Newly created content tags outrank the built-in selection tag; without
    # this, selecting text over code blocks (CODE_BG) shows no highlight
    widget.tag_raise("sel")

    widget._code_blocks = []
    _header, body = split_front_matter(content)
    lines = body.splitlines()
    footnote_defs = collect_footnote_definitions(lines)
    line_index = 0

    # Fix #2: compute HR width from the widget's actual pixel width
    char_width = max(20, widget.winfo_width() // 8)
    hr_line = "─" * min(char_width, 60) + "\n"

    while line_index < len(lines):
        line = lines[line_index]
        stripped = line.strip()

        if stripped.startswith("%%"):
            if stripped.endswith("%%") and len(stripped) > 4:
                line_index += 1
                continue
            line_index += 1
            while line_index < len(lines) and "%%" not in lines[line_index]:
                line_index += 1
            line_index += 1
            continue

        if is_footnote_definition_line(line):
            line_index += 1
            continue

        line = strip_obsidian_comments(line)
        stripped = line.strip()
        if not stripped and not line:
            line_index += 1
            continue

        callout_match = CALLOUT_LINE.match(line)
        if callout_match:
            kind = callout_match.group(1)
            title = callout_match.group(2).strip()
            body_lines: list[str] = []
            line_index += 1
            while line_index < len(lines) and lines[line_index].lstrip().startswith(">"):
                body_lines.append(re.sub(r"^>\s?", "", lines[line_index].lstrip()))
                line_index += 1
            insert_callout(widget, kind, title, body_lines, base_path)
            continue

        # Fix #4: capture fenced code block language and display a label
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            line_index += 1
            code_lines: list[str] = []
            while line_index < len(lines):
                candidate = lines[line_index]
                if candidate.strip().startswith("```"):
                    line_index += 1
                    break
                code_lines.append(candidate)
                line_index += 1
            if lang:
                widget.insert(tk.END, lang + "\n", "code_lang")
            code_text = "\n".join(code_lines)
            if code_lines:
                code_text += "\n"
            insert_syntax_highlighted_code_block(
                widget,
                code_text,
                lang,
                base_tags=("code", "code_block"),
                tag_prefix="code_syntax",
                font_size=max(10, body_size),
                background=theme.CODE_BG,
            )
            continue
        if (
            "|" in line
            and line_index + 1 < len(lines)
            and is_table_separator(lines[line_index + 1])
        ):
            rows = [parse_table_row(line)]
            # Fix #3: capture alignment from separator row before advancing
            alignments = parse_table_alignment(lines[line_index + 1])
            line_index += 2
            while line_index < len(lines) and "|" in lines[line_index] and lines[line_index].strip():
                rows.append(parse_table_row(lines[line_index]))
                line_index += 1
            insert_table(widget, rows, alignments, font_size=max(9, body_size - 1))
            continue
        image_match = IMAGE_MD.fullmatch(stripped)
        if image_match:
            if not insert_markdown_image(widget, image_match.group(1), image_match.group(2), base_path):
                widget.insert(tk.END, line + "\n", "body")
            line_index += 1
            continue
        file_link_match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", stripped)
        if file_link_match:
            raw_target = file_link_match.group(2)
            linked_path = resolve_markdown_path(raw_target, base_path)
            if linked_path and linked_path.exists() and linked_path.is_file() and _is_pdf_path(linked_path):
                if insert_pdf_preview_block(widget, linked_path, font_family, font_size, initial_page=pdf_page_index_from_fragment(raw_target)):
                    line_index += 1
                    continue
        wiki_links = parse_wiki_links(stripped)
        if len(wiki_links) == 1 and wiki_links[0].raw == stripped and wiki_links[0].embed:
            wiki_link = wiki_links[0]
            if wiki_note_resolver is not None:
                embed = wiki_note_resolver(wiki_link.target, base_path)
                if embed:
                    insert_note_embed(widget, embed[0], embed[1], base_path, font_family, font_size)
                    line_index += 1
                    continue
            asset_path = (
                wiki_asset_resolver(wiki_link.target, base_path)
                if wiki_asset_resolver is not None
                else resolve_markdown_path(wiki_link.target, base_path)
            )
            if asset_path and _is_pdf_path(asset_path) and insert_pdf_preview_block(
                widget,
                asset_path,
                font_family,
                font_size,
                initial_page=pdf_page_index_from_fragment(wiki_link.heading),
            ):
                line_index += 1
                continue
            if asset_path and asset_path.suffix.casefold() in {
                ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".ico"
            } and insert_markdown_image(widget, wiki_link.alias, str(asset_path), None):
                line_index += 1
                continue
        # Fix #2: use dynamic hr_line instead of hardcoded 36 chars
        if stripped in {"---", "***", "___"}:
            widget.insert(tk.END, hr_line, "hr")
        elif line.startswith("###### "):
            insert_inline_md(widget, line[7:] + "\n", "h6", base_path)
        elif line.startswith("##### "):
            insert_inline_md(widget, line[6:] + "\n", "h5", base_path)
        elif line.startswith("#### "):
            insert_inline_md(widget, line[5:] + "\n", "h4", base_path)
        elif line.startswith("### "):
            insert_inline_md(widget, line[4:] + "\n", "h3", base_path)
        elif line.startswith("## "):
            insert_inline_md(widget, line[3:] + "\n", "h2", base_path)
        elif line.startswith("# "):
            insert_inline_md(widget, line[2:] + "\n", "h1", base_path)
        elif line.startswith("> "):
            insert_inline_md(widget, line[2:] + "\n", "quote", base_path)
        elif match := TASK_LINE.match(line):
            task_state = task_state_from_marker(match.group(1))
            tag = "task_done" if task_state == "done" else "list"
            widget.insert(tk.END, task_prefix_for_state(task_state), tag)
            insert_inline_md(widget, (match.group(2) or "") + "\n", tag, base_path)
        elif re.match(r"^[-*+] ", line):
            widget.insert(tk.END, "• ", "list")
            insert_inline_md(widget, line[2:] + "\n", "list", base_path)
        elif re.match(r"^\d+\. ", line):
            match = re.match(r"^(\d+\. )(.*)$", line)
            widget.insert(tk.END, match.group(1), "list")
            insert_inline_md(widget, match.group(2) + "\n", "list", base_path)
        elif not stripped:
            widget.insert(tk.END, "\n")
        else:
            insert_inline_md(widget, line + "\n", "body", base_path)
        line_index += 1

    if footnote_defs:
        widget.insert(tk.END, "\n")
        widget.insert(tk.END, "Footnotes\n", "h6")
        for key, text in sorted(footnote_defs.items(), key=lambda item: item[0].casefold()):
            widget.insert(tk.END, f"[^{key}] ", "footnote")
            insert_inline_md(widget, text + "\n", "footnote", base_path)

    # Collect fenced code block positions for hover-copy feature
    code_ranges = widget.tag_ranges("code_block")
    for i in range(0, len(code_ranges), 2):
        start = str(code_ranges[i])
        end = str(code_ranges[i + 1])
        # Fix #1: renamed from 'content' to 'block_text' to avoid shadowing the parameter
        block_text = widget.get(start, end).strip()
        widget._code_blocks.append({"start": start, "end": end, "text": block_text})
    widget.tag_raise("sel")
    # Keep widget NORMAL so text can be selected and copied
    widget.config(state=tk.NORMAL)
