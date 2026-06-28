from __future__ import annotations

import mimetypes
import os
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk

from . import theme
from .dragdrop import is_image_path
from .image_safety import ImageTooLargeError, open_image_checked, load_thumbnail_image
from .i18n import t
from .text_files import EDITABLE_TEXT_SUFFIXES


TEXT_SUFFIXES = EDITABLE_TEXT_SUFFIXES | {".bak"}
MAX_TEXT_PREVIEW_BYTES = 1_000_000
PDF_SUFFIX = ".pdf"
PDF_MIN_ZOOM = 0.5
PDF_MAX_ZOOM = 3.0
PDF_ZOOM_STEP = 1.12
PDF_FIT_WIDTH = "width"
PDF_FIT_PAGE = "page"
PDF_CUSTOM_ZOOM = "custom"
PDF_PAGE_FRAGMENT_RE = r"(?:^|[&#])(?:page|p)=(\d+)(?:$|[&#])"


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


def _is_pdf_path(path: Path) -> bool:
    return path.suffix.lower() == PDF_SUFFIX


def pdf_page_index_from_fragment(value: str) -> int:
    import re

    match = re.search(PDF_PAGE_FRAGMENT_RE, value.strip(), re.IGNORECASE)
    if not match:
        return 0
    return max(0, int(match.group(1)) - 1)


def _clamp_pdf_zoom(value: float) -> float:
    return max(PDF_MIN_ZOOM, min(PDF_MAX_ZOOM, float(value)))


def _pdf_preview_zoom(widget: tk.Text) -> float:
    return _clamp_pdf_zoom(getattr(widget, "_pdf_preview_zoom", 1.0) or 1.0)


def set_pdf_preview_zoom(widget: tk.Text, zoom: float) -> float:
    value = _clamp_pdf_zoom(zoom)
    widget._pdf_preview_zoom = value
    widget._pdf_preview_fit = PDF_CUSTOM_ZOOM
    return value


def set_pdf_preview_fit(widget: tk.Text, mode: str) -> str:
    value = mode if mode in {PDF_FIT_WIDTH, PDF_FIT_PAGE} else PDF_CUSTOM_ZOOM
    widget._pdf_preview_fit = value
    if value in {PDF_FIT_WIDTH, PDF_FIT_PAGE}:
        widget._pdf_preview_zoom = 1.0
    return value


def _pdf_preview_fit(widget: tk.Text) -> str:
    return str(getattr(widget, "_pdf_preview_fit", PDF_FIT_WIDTH) or PDF_FIT_WIDTH)


def _pdf_preview_size(widget: tk.Text) -> tuple[int, int]:
    zoom = _pdf_preview_zoom(widget)
    base_width = max(180, text_content_width(widget) - 36)
    base_height = max(220, widget.winfo_height() - 150)
    if _pdf_preview_fit(widget) == PDF_FIT_PAGE:
        return base_width, base_height
    return (
        max(180, int(base_width * zoom)),
        max(1000, int(base_height * 12 * zoom)),
    )


def _render_pdf_page(path: Path, page_index: int, max_size: tuple[int, int]) -> tuple[Image.Image, int]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(path))
    try:
        page_count = len(document)
        if page_count <= 0:
            raise ValueError("PDF has no pages.")
        page_index = max(0, min(int(page_index), page_count - 1))
        page = document[page_index]
        try:
            page_width = max(1.0, float(page.get_width()))
            page_height = max(1.0, float(page.get_height()))
            scale = min(max_size[0] / page_width, max_size[1] / page_height)
            scale = max(0.2, min(3.0, scale))
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().convert("RGB")
        finally:
            close_page = getattr(page, "close", None)
            if callable(close_page):
                close_page()
        return image, page_count
    finally:
        close_document = getattr(document, "close", None)
        if callable(close_document):
            close_document()


def _show_pdf_error(widget: tk.Text, path: Path, size_text: str, exc: Exception) -> str:
    mime, _encoding = mimetypes.guess_type(path.name)
    file_type = mime or "PDF file"
    widget.insert(tk.END, f"{file_type}  |  {size_text}\n\n", "preview_meta")
    widget.insert(tk.END, t("preview.pdf_unavailable", exc=exc), "preview_body")
    widget.configure(state=tk.DISABLED)
    return "info"


def _preview_button(parent: tk.Widget, text: str, command, *, enabled: bool = True, selected: bool = False) -> tk.Label:
    bg = theme.ACCENT if selected and enabled else theme.SURFACE_2 if enabled else theme.SURFACE
    fg = theme.BG if selected and enabled else theme.TEXT if enabled else theme.MUTED
    button = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Segoe UI", 9, "bold"),
        cursor="hand2" if enabled else "arrow",
        padx=8,
        pady=3,
    )
    if enabled:
        button.bind("<Button-1>", lambda _event: command())
        button.bind("<Enter>", lambda _event: button.configure(bg=theme.ACCENT, fg=theme.BG))
        button.bind(
            "<Leave>",
            lambda _event: button.configure(
                bg=theme.ACCENT if selected else theme.SURFACE_2,
                fg=theme.BG if selected else theme.TEXT,
            ),
        )
    return button


def text_content_width(widget: tk.Text) -> int:
    try:
        padx = int(widget.cget("padx") or 0)
    except (AttributeError, tk.TclError, TypeError, ValueError):
        padx = 0
    try:
        width = int(widget.winfo_width())
    except tk.TclError:
        width = 0
    return max(180, width - (padx * 2))


def forward_mousewheel_to_text(widget: tk.Widget, text_widget: tk.Text, *, ctrl_handler=None) -> None:
    def forward(event) -> str:
        if ctrl_handler is not None and getattr(event, "state", 0) & 0x0004:
            ctrl_handler(event)
            return "break"
        try:
            text_widget.event_generate("<MouseWheel>", delta=event.delta, x=0, y=0)
        except tk.TclError:
            pass
        return "break"

    def bind_tree(target: tk.Widget) -> None:
        try:
            if not getattr(target, "_forward_mousewheel_to_text", False):
                target.bind("<MouseWheel>", forward, add="+")
                target._forward_mousewheel_to_text = True
        except tk.TclError:
            return
        try:
            children = target.winfo_children()
        except tk.TclError:
            children = []
        for child in children:
            bind_tree(child)

    bind_tree(widget)


def _insert_pdf_controls(
    widget: tk.Text,
    path: Path,
    page_index: int,
    page_count: int,
    font_family: str,
    font_size: int,
) -> None:
    frame_width = text_content_width(widget)
    frame = tk.Frame(widget, bg=theme.BG, width=frame_width)
    nav_row = tk.Frame(frame, bg=theme.BG, width=frame_width)
    zoom_row = tk.Frame(frame, bg=theme.BG, width=frame_width)
    current_zoom = _pdf_preview_zoom(widget)
    current_fit = _pdf_preview_fit(widget)
    page_var = tk.StringVar(value=str(page_index + 1))
    page_entry = tk.Entry(
        nav_row,
        textvariable=page_var,
        width=4,
        bg=theme.SURFACE,
        fg=theme.TEXT,
        insertbackground=theme.TEXT,
        relief="flat",
        justify="center",
        font=(font_family, max(9, font_size)),
    )
    page_label = tk.Label(
        nav_row,
        text=t("preview.pdf_page_of", total=page_count),
        bg=theme.BG,
        fg=theme.TEXT,
        font=(font_family, max(9, font_size), "bold"),
    )

    def show_page(next_index: int) -> None:
        widget._pdf_preview_page = max(0, min(next_index, page_count - 1))
        render_file_preview(widget, path, font_family=font_family, font_size=font_size)

    def jump_to_page() -> str:
        try:
            page_number = int(page_var.get().strip())
        except ValueError:
            page_var.set(str(page_index + 1))
            return "break"
        show_page(page_number - 1)
        return "break"

    def set_fit(mode: str) -> None:
        set_pdf_preview_fit(widget, mode)
        render_file_preview(widget, path, font_family=font_family, font_size=font_size)

    def zoom_by(factor: float) -> None:
        set_pdf_preview_zoom(widget, current_zoom * factor)
        render_file_preview(widget, path, font_family=font_family, font_size=font_size)

    def open_external() -> None:
        try:
            os.startfile(path)
        except OSError:
            pass

    previous_btn = _preview_button(
        nav_row,
        t("preview.pdf_previous"),
        lambda: show_page(page_index - 1),
        enabled=page_index > 0,
    )
    next_btn = _preview_button(
        nav_row,
        t("preview.pdf_next"),
        lambda: show_page(page_index + 1),
        enabled=page_index + 1 < page_count,
    )
    zoom_out_btn = _preview_button(zoom_row, "−", lambda: zoom_by(1 / PDF_ZOOM_STEP))
    zoom_label = tk.Label(
        zoom_row,
        text=t("preview.pdf_zoom", zoom=round(current_zoom * 100)),
        bg=theme.BG,
        fg=theme.MUTED,
        font=(font_family, max(8, font_size - 1)),
    )
    zoom_in_btn = _preview_button(zoom_row, "+", lambda: zoom_by(PDF_ZOOM_STEP))
    fit_width_btn = _preview_button(
        zoom_row,
        t("preview.pdf_fit_width"),
        lambda: set_fit(PDF_FIT_WIDTH),
        selected=current_fit == PDF_FIT_WIDTH,
    )
    fit_page_btn = _preview_button(
        zoom_row,
        t("preview.pdf_fit_page"),
        lambda: set_fit(PDF_FIT_PAGE),
        selected=current_fit == PDF_FIT_PAGE,
    )
    open_btn = _preview_button(nav_row, t("preview.pdf_open_external"), open_external)
    page_entry.bind("<Return>", lambda _event: jump_to_page())
    page_entry.bind("<FocusOut>", lambda _event: jump_to_page())
    nav_row.pack(anchor="w", pady=(0, 5))
    zoom_row.pack(anchor="w")
    previous_btn.pack(side="left", padx=(0, 4))
    page_entry.pack(side="left", padx=(0, 3), ipady=2)
    page_label.pack(side="left", padx=(0, 5))
    next_btn.pack(side="left", padx=(0, 8))
    open_btn.pack(side="left")
    zoom_out_btn.pack(side="left", padx=(0, 3))
    zoom_label.pack(side="left", padx=(0, 3))
    zoom_in_btn.pack(side="left", padx=(0, 8))
    fit_width_btn.pack(side="left", padx=(0, 4))
    fit_page_btn.pack(in_=zoom_row, side="left")
    forward_mousewheel_to_text(
        frame,
        widget,
        ctrl_handler=lambda event: (
            zoom_by(PDF_ZOOM_STEP if getattr(event, "delta", 0) > 0 else 1 / PDF_ZOOM_STEP)
        ),
    )
    widget._file_preview_windows.append(frame)
    widget.window_create(tk.END, window=frame)
    widget.insert(tk.END, "\n\n")


def insert_pdf_preview_block(
    widget: tk.Text,
    path: Path,
    font_family: str = "Segoe UI",
    font_size: int = 10,
    *,
    edit_command=None,
    insert_at: str = tk.END,
    trailing_newline: bool = True,
    initial_page: int = 0,
):
    if not path.exists() or not path.is_file() or not _is_pdf_path(path):
        return None
    if not hasattr(widget, "_file_preview_windows"):
        widget._file_preview_windows = []
    if not hasattr(widget, "_file_preview_images"):
        widget._file_preview_images = []
    frame_width = text_content_width(widget)
    inner_width = max(180, frame_width - 12)
    frame = tk.Frame(widget, bg=theme.BG, highlightthickness=1, highlightbackground=theme.BORDER, width=frame_width)
    toolbar = tk.Frame(frame, bg=theme.BG, width=inner_width)
    image_holder = tk.Frame(frame, bg=theme.BG, width=inner_width)
    toolbar.pack(fill="x", padx=6, pady=(6, 4))
    image_holder.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    image_label = tk.Label(image_holder, bg=theme.BG)
    image_label.pack(anchor="center")
    state = {
        "page": max(0, int(initial_page)),
        "page_count": 1,
        "zoom": 1.0,
        "fit": PDF_FIT_WIDTH,
        "photo": None,
    }

    def block_size() -> tuple[int, int]:
        base_width = max(180, inner_width - 12)
        base_height = max(220, min(720, widget.winfo_height() - 160))
        zoom = _clamp_pdf_zoom(float(state["zoom"]))
        if state["fit"] == PDF_FIT_PAGE:
            return base_width, base_height
        return max(180, int(base_width * zoom)), max(900, int(base_height * 10 * zoom))

    def rerender() -> None:
        for child in toolbar.winfo_children():
            child.destroy()
        try:
            image, page_count = _render_pdf_page(path, int(state["page"]), block_size())
        except Exception as exc:
            image_label.configure(text=t("preview.pdf_unavailable", exc=exc), image="", fg=theme.MUTED)
            return
        state["page_count"] = page_count
        state["page"] = max(0, min(int(state["page"]), page_count - 1))
        photo = ImageTk.PhotoImage(image)
        state["photo"] = photo
        widget._file_preview_images.append(photo)
        image_label.configure(image=photo, text="")

        def show_page(next_index: int) -> None:
            state["page"] = max(0, min(next_index, int(state["page_count"]) - 1))
            rerender()

        def zoom_by(factor: float) -> None:
            state["zoom"] = _clamp_pdf_zoom(float(state["zoom"]) * factor)
            state["fit"] = PDF_CUSTOM_ZOOM
            rerender()

        def fit(mode: str) -> None:
            state["fit"] = mode
            state["zoom"] = 1.0
            rerender()

        def jump_to_page() -> str:
            try:
                page_number = int(page_var.get().strip())
            except ValueError:
                page_var.set(str(int(state["page"]) + 1))
                return "break"
            show_page(page_number - 1)
            return "break"

        nav_row = tk.Frame(toolbar, bg=theme.BG, width=inner_width)
        zoom_row = tk.Frame(toolbar, bg=theme.BG, width=inner_width)
        page_var = tk.StringVar(value=str(int(state["page"]) + 1))
        page_entry = tk.Entry(
            nav_row,
            textvariable=page_var,
            width=4,
            bg=theme.SURFACE,
            fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief="flat",
            justify="center",
            font=(font_family, max(9, font_size)),
        )
        page_label = tk.Label(
            nav_row,
            text=t("preview.pdf_page_of", total=int(state["page_count"])),
            bg=theme.BG,
            fg=theme.TEXT,
            font=(font_family, max(9, font_size), "bold"),
        )
        page_entry.bind("<Return>", lambda _event: jump_to_page())
        page_entry.bind("<FocusOut>", lambda _event: jump_to_page())
        previous_btn = _preview_button(nav_row, t("preview.pdf_previous"), lambda: show_page(int(state["page"]) - 1), enabled=int(state["page"]) > 0)
        next_btn = _preview_button(
            nav_row,
            t("preview.pdf_next"),
            lambda: show_page(int(state["page"]) + 1),
            enabled=int(state["page"]) + 1 < int(state["page_count"]),
        )
        zoom_out = _preview_button(zoom_row, "−", lambda: zoom_by(1 / PDF_ZOOM_STEP))
        zoom_text = tk.Label(zoom_row, text=t("preview.pdf_zoom", zoom=round(float(state["zoom"]) * 100)), bg=theme.BG, fg=theme.MUTED, font=(font_family, max(8, font_size - 1)))
        zoom_in = _preview_button(zoom_row, "+", lambda: zoom_by(PDF_ZOOM_STEP))
        fit_width = _preview_button(zoom_row, t("preview.pdf_fit_width"), lambda: fit(PDF_FIT_WIDTH), selected=state["fit"] == PDF_FIT_WIDTH)
        fit_page = _preview_button(zoom_row, t("preview.pdf_fit_page"), lambda: fit(PDF_FIT_PAGE), selected=state["fit"] == PDF_FIT_PAGE)
        def open_external() -> None:
            try:
                os.startfile(path)
            except OSError:
                pass

        open_btn = _preview_button(nav_row, t("preview.pdf_open_external"), open_external)
        nav_row.pack(anchor="w", fill="x", pady=(0, 5))
        zoom_row.pack(anchor="w", fill="x")
        previous_btn.pack(side="left", padx=(0, 4))
        page_entry.pack(in_=nav_row, side="left", padx=(0, 3), ipady=2)
        page_label.pack(in_=nav_row, side="left", padx=(0, 5))
        next_btn.pack(side="left", padx=(0, 6))
        open_btn.pack(side="left")
        zoom_out.pack(side="left", padx=(0, 3))
        zoom_text.pack(side="left", padx=(0, 3))
        zoom_in.pack(side="left", padx=(0, 8))
        fit_width.pack(side="left", padx=(0, 4))
        fit_page.pack(side="left", padx=(0, 4))
        if edit_command is not None:
            _preview_button(zoom_row, t("editor.edit_image"), edit_command).pack(side="left")
        forward_mousewheel_to_text(
            frame,
            widget,
            ctrl_handler=lambda event: (
                zoom_by(PDF_ZOOM_STEP if getattr(event, "delta", 0) > 0 else 1 / PDF_ZOOM_STEP)
            ),
        )
        try:
            frame.update_idletasks()
            frame.configure(width=frame_width, height=frame.winfo_reqheight())
            frame.pack_propagate(False)
        except tk.TclError:
            pass

    rerender()
    widget._file_preview_windows.append(frame)
    widget.window_create(insert_at, window=frame)
    if trailing_newline:
        widget.insert(tk.END if insert_at == tk.END else f"{insert_at}+1c", "\n")
    return frame


# Fix #10: font_family and font_size forwarded from caller (notes.py has config access)
def render_file_preview(
    widget: tk.Text,
    path: Path,
    font_family: str = "Segoe UI",
    font_size: int = 10,
) -> str:
    widget.configure(state=tk.NORMAL)
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
            checked = open_image_checked(path)
            dimensions = f"{checked.width} x {checked.height}"
            max_width = max(160, widget.winfo_width() - 44)
            max_height = max(160, widget.winfo_height() - 130)
            image = load_thumbnail_image(path, (max_width, max_height))
            photo = ImageTk.PhotoImage(image)
        except (OSError, ValueError, ImageTooLargeError) as exc:
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

    if _is_pdf_path(path):
        resolved_pdf_path = str(path.resolve())
        if getattr(widget, "_pdf_preview_path", "") != resolved_pdf_path:
            widget._pdf_preview_page = 0
            widget._pdf_preview_zoom = 1.0
            widget._pdf_preview_fit = PDF_FIT_WIDTH
        page_index = max(0, int(getattr(widget, "_pdf_preview_page", 0) or 0))
        zoom = _pdf_preview_zoom(widget)
        try:
            image, page_count = _render_pdf_page(path, page_index, _pdf_preview_size(widget))
            page_index = max(0, min(page_index, page_count - 1))
            photo = ImageTk.PhotoImage(image)
        except Exception as exc:
            return _show_pdf_error(widget, path, size_text, exc)
        widget._file_preview_images.append(photo)
        widget._pdf_preview_path = resolved_pdf_path
        widget._pdf_preview_page = page_index
        widget._pdf_preview_zoom = zoom
        widget._pdf_preview_page_count = page_count
        widget.insert(tk.END, f"PDF  |  {size_text}\n\n", "preview_meta")
        _insert_pdf_controls(widget, path, page_index, page_count, font_family, font_size)
        image_index = widget.index(tk.END)
        widget.image_create(image_index, image=photo)
        widget.tag_add("preview_center", f"{image_index} linestart", f"{image_index} lineend")
        widget.insert(tk.END, "\n")
        widget.configure(state=tk.DISABLED)
        return "pdf"

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
