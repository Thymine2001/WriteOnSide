from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Iterable

try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name
    from pygments.styles import get_style_by_name
    from pygments.util import ClassNotFound
except Exception:  # pragma: no cover - Pygments is optional at import time.
    lex = None  # type: ignore[assignment]
    get_lexer_by_name = None  # type: ignore[assignment]
    get_style_by_name = None  # type: ignore[assignment]

    class ClassNotFound(Exception):
        pass


@dataclass(frozen=True)
class SyntaxSpan:
    start: int
    end: int
    color: str


_LANGUAGE_ALIASES = {
    "shell": "bash",
    "sh": "bash",
    "zsh": "bash",
    "ps": "powershell",
    "pwsh": "powershell",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "yml": "yaml",
    "md": "markdown",
}


def normalize_code_language(language: str | None) -> str:
    value = (language or "").strip()
    if not value:
        return ""
    value = value.split(maxsplit=1)[0].casefold()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1].strip()
    return _LANGUAGE_ALIASES.get(value, value)


def _hex_luminance(color: str) -> float:
    value = color.strip().lstrip("#")
    if len(value) != 6:
        return 0.0
    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return 0.0
    return (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255


def style_for_background(background: str) -> str:
    return "default" if _hex_luminance(background) > 0.55 else "monokai"


def code_token_spans(
    code: str,
    language: str | None,
    *,
    background: str = "#1e1e1e",
    max_chars: int = 60_000,
) -> tuple[SyntaxSpan, ...]:
    if lex is None or get_lexer_by_name is None or get_style_by_name is None:
        return ()
    if not code or len(code) > max_chars:
        return ()
    normalized = normalize_code_language(language)
    if not normalized:
        return ()
    try:
        lexer = get_lexer_by_name(normalized, stripnl=False, ensurenl=False)
        style = get_style_by_name(style_for_background(background))
    except ClassNotFound:
        return ()

    spans: list[SyntaxSpan] = []
    position = 0
    for token_type, value in lex(code, lexer):
        end = position + len(value)
        if value.strip():
            token_style = style.style_for_token(token_type)
            color = token_style.get("color")
            if color:
                spans.append(SyntaxSpan(position, end, f"#{color}"))
        position = end
    return tuple(spans)


def syntax_tag_name(prefix: str, color: str) -> str:
    digest = sha1(color.casefold().encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def configure_syntax_tag(
    widget,
    tag: str,
    color: str,
    *,
    font_family: str = "Consolas",
    font_size: int = 10,
    background: str | None = None,
) -> None:
    options = {
        "foreground": color,
        "font": (font_family, max(8, font_size)),
    }
    if background:
        options["background"] = background
    widget.tag_configure(tag, **options)


def insert_syntax_highlighted_code_block(
    widget,
    code: str,
    language: str | None,
    *,
    base_tags: Iterable[str],
    tag_prefix: str,
    font_size: int,
    background: str,
) -> None:
    spans = code_token_spans(code, language, background=background)
    base = tuple(base_tags)
    if not spans:
        widget.insert("end", code, base)
        return

    position = 0
    for span in spans:
        if span.start > position:
            widget.insert("end", code[position : span.start], base)
        tag = syntax_tag_name(tag_prefix, span.color)
        configure_syntax_tag(widget, tag, span.color, font_size=font_size, background=background)
        widget.insert("end", code[span.start : span.end], (*base, tag))
        position = span.end
    if position < len(code):
        widget.insert("end", code[position:], base)
