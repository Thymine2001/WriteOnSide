from __future__ import annotations

import mimetypes
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageOps, ImageTk

from . import theme
from .dragdrop import is_image_path
from .i18n import t
from .text_files import EDITABLE_TEXT_SUFFIXES


TEXT_SUFFIXES = EDITABLE_TEXT_SUFFIXES | {".bak"}
MAX_TEXT_PREVIEW_BYTES = 1_000_000


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


# Fix #10: accept font_family and font_size so the preview respects user typography settings
def _configure_tags(
    widget: tk.Text,
    font_family: str = "Segoe UI",
    font_size: int = 10,
) -> None:
    delta = font_size - 10
    widget.tag_configure(
        "preview_title",
        font=(font_family, 15 + delta, "bold"),
        foreground=theme.TEXT,
        spacing3=4,
    )
    widget.tag_configure(
        "preview_meta",
        font=(font_family, max(8, 9 + delta)),
        foreground=theme.MUTED,
        spacing3=12,
    )
    widget.tag_configure(
        "preview_body",
        font=("Consolas", max(8, 10 + delta)),
        foreground=theme.TEXT_SOFT,
    )
    widget.tag_configure(
        "preview_center",
        justify="center",
        foreground=theme.TEXT,
    )


def _decode_text(path: Path) -> tuple[str, bool] | None:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            data = handle.read(MAX_TEXT_PREVIEW_BYTES + 1)
    except OSError:
        return None
    truncated = size > MAX_TEXT_PREVIEW_BYTES
    data = data[:MAX_TEXT_PREVIEW_BYTES]
    if b"\x00" in data[:4096] and path.suffix.lower() not in {".txt", ".log"}:
        return None
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return data.decode(encoding), truncated
        except UnicodeError:
            continue
    return data.decode("utf-8", errors="replace"), truncated


def _looks_like_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    mime, _encoding = mimetypes.guess_type(path.name)
    return bool(mime and mime.startswith("text/"))


# Fix #10: font_family and font_size forwarded from caller (notes.py has config access)
def render_file_preview(
    widget: tk.Text,
    path: Path,
    font_family: str = "Segoe UI",
    font_size: int = 10,
) -> str:
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget._markdown_images = []
    widget._file_preview_images = []
    widget._clickable_images = {}
    _configure_tags(widget, font_family, font_size)

    try:
        stat = path.stat()
        size_text = _format_size(stat.st_size)
    except OSError:
        stat = None
        size_text = t("preview.unavailable")

    widget.insert(tk.END, path.name + "\n", "preview_title")

    if is_image_path(path):
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).copy()
                dimensions = f"{image.width} x {image.height}"
                max_width = max(160, widget.winfo_width() - 44)
                max_height = max(160, widget.winfo_height() - 130)
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
        except Exception as exc:
            widget.insert(tk.END, t("preview.image_unavailable", exc=exc) + "\n", "preview_meta")
            widget.configure(state=tk.DISABLED)
            return "info"
        widget.insert(tk.END, f"{dimensions}  |  {size_text}\n\n", "preview_meta")
        widget._file_preview_images.append(photo)
        image_index = widget.index(tk.END)
        image_name = widget.image_create(image_index, image=photo)
        widget._clickable_images[str(image_name)] = str(path.resolve())
        widget.tag_add("preview_center", f"{image_index} linestart", f"{image_index} lineend")
        widget.insert(tk.END, "\n")
        widget.configure(state=tk.DISABLED)
        return "image"

    if _looks_like_text(path):
        decoded = _decode_text(path)
        if decoded is not None:
            content, truncated = decoded
            suffix = "  |  Preview limited to 1 MB" if truncated else ""
            widget.insert(tk.END, f"{size_text}{suffix}\n\n", "preview_meta")
            widget.insert(tk.END, content, "preview_body")
            widget.configure(state=tk.DISABLED)
            return "text"

    mime, _encoding = mimetypes.guess_type(path.name)
    file_type = mime or (path.suffix.upper().lstrip(".") + " file" if path.suffix else "File")
    widget.insert(tk.END, f"{file_type}  |  {size_text}\n\n", "preview_meta")
    widget.insert(
        tk.END,
        t("preview.cannot_render"),
        "preview_body",
    )
    widget.configure(state=tk.DISABLED)
    return "info"
