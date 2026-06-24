from __future__ import annotations

import os
import re
import time
from datetime import date, datetime
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageGrab, ImageTk

from ..config import save_config
from ..frontmatter import build_front_matter, parse_front_matter, split_front_matter
from ..image_safety import load_thumbnail_image
from ..i18n import t
from ..storage import read_text_file, safe_note_name, safe_write_text
from ..theme import *  # noqa: F401,F403


PLUGIN_FOLDER = Path("Plugins") / "StickyNotes"
AUTOSAVE_DELAY_MS = 650
IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
PLUGIN_TAGS = ("plugin-sticky-notes", "sticky-notes")


def run(app) -> None:
    open_sticky_notes(app)


def sticky_notes_folder(app) -> Path:
    return app._workspace_dir() / PLUGIN_FOLDER


def sticky_note_paths(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        (path for path in folder.glob("*.md") if path.is_file()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )


def normalize_sticky_tags(value: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(value, str):
        pieces = re.split(r"[,，\n]+", value)
    else:
        pieces = [str(item) for item in value]
    tags: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        tag = piece.strip().lstrip("#")
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def sticky_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        title = re.sub(r"^[#>*\-\s]+", "", line).strip()
        if title:
            return title[:80]
    return fallback


def sticky_note_content(body: str, tags: list[str], *, title: str, created: str | None = None) -> str:
    return build_front_matter(title, tags, created=created or date.today().isoformat()) + body.lstrip("\n")


def next_sticky_path(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = safe_note_name(f"Sticky-{stamp}.md")
    path = folder / base
    counter = 2
    while path.exists():
        path = folder / safe_note_name(f"Sticky-{stamp}-{counter}.md")
        counter += 1
    return path


def unique_sticky_path_for_title(folder: Path, title: str, current: Path | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    base_name = safe_note_name(title)
    candidate = folder / base_name
    try:
        if current is not None and candidate.resolve() == current.resolve():
            return candidate
    except OSError:
        pass
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix or ".md"
    counter = 2
    while True:
        candidate = folder / safe_note_name(f"{stem}-{counter}{suffix}")
        try:
            if current is not None and candidate.resolve() == current.resolve():
                return candidate
        except OSError:
            pass
        if not candidate.exists():
            return candidate
        counter += 1


def safe_attachment_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name).strip().strip(".")
    return cleaned or "attachment"


def open_sticky_notes(app, *, force_new_window: bool = False, create_new_note: bool = False, path: Path | None = None) -> None:
    existing = getattr(app, "_sticky_notes_window", None)
    if existing is not None and not force_new_window and path is None:
        try:
            if existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                existing.focus_force()
                return
        except tk.TclError:
            pass
    StickyNotesWindow(app, create_new_note=create_new_note, initial_path=path).open()


def open_sticky_notes_from_hotkey(app) -> None:
    open_sticky_notes(app, force_new_window=True, create_new_note=True)


def open_path_in_sticky_note(app, path: Path) -> None:
    open_sticky_notes(app, force_new_window=True, path=Path(path))


def keep_sticky_notes_visible(app) -> None:
    live: list[tk.Toplevel] = []
    for window in getattr(app, "_sticky_notes_windows", []) or []:
        try:
            if not window.winfo_exists():
                continue
            window.deiconify()
            window.lift()
            live.append(window)
        except tk.TclError:
            pass
    app._sticky_notes_windows = live
    if live:
        app._sticky_notes_window = live[-1]


def refresh_sticky_notes_theme(app) -> None:
    for controller in getattr(app, "_sticky_notes_controllers", []) or []:
        try:
            controller.refresh_theme()
        except (AttributeError, tk.TclError):
            pass


def sticky_window_geometry(app, width: int, height: int, index: int = 0, previous: tk.Toplevel | None = None) -> str:
    work_height = max(320, app.work_bottom - app.work_top)
    step_x = 22
    step_y = 28
    max_y = app.work_top + max(24, work_height - height - 24)
    max_x = app.work_left + max(24, app.work_right - app.work_left - width - 24)
    if previous is not None:
        try:
            previous.update_idletasks()
            x = previous.winfo_x() + step_x
            y = previous.winfo_y() + step_y
        except tk.TclError:
            previous = None
    if previous is None:
        x = app.work_left + 24 + min(max(0, index), 6) * step_x
        y = app.work_top + min(max_y - app.work_top, 64 + min(max(0, index), 6) * step_y)
    x = min(max_x, max(app.work_left + 8, x))
    y = min(max_y, max(app.work_top + 8, y))
    return f"{width}x{height}+{x}+{y}"


class StickyNotesWindow:
    def __init__(self, app, *, create_new_note: bool = False, initial_path: Path | None = None) -> None:
        self.app = app
        self.create_new_note = create_new_note
        self.initial_path = initial_path
        self.path: Path | None = None
        self.created = date.today().isoformat()
        self.save_after: str | None = None
        self.refresh_after: str | None = None
        self.loading = False

    def open(self) -> None:
        app = self.app
        g = globals()
        parent = app.root

        win = tk.Toplevel(parent)
        win.withdraw()
        win.title(t("sticky.window_title"))
        # Let the window manager own activation/focus. On Windows, overrideredirect
        # windows can display correctly but stop receiving keyboard input after
        # focus moves elsewhere.
        win.configure(bg=g["BORDER"])
        width, height = 380, 360
        open_windows = self._live_windows()
        previous_window = open_windows[-1] if open_windows else None
        win.geometry(sticky_window_geometry(app, width, height, len(open_windows), previous_window))
        win.minsize(300, 240)
        win.resizable(True, True)
        win.attributes("-topmost", bool(app.config.sticky_notes_pinned))

        shell = tk.Frame(win, bg=g["BG"], highlightthickness=1, highlightbackground=g["BORDER"])
        shell.pack(fill="both", expand=True, padx=1, pady=1)

        header = tk.Frame(shell, bg=g["SURFACE"], height=44)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        accent_strip = tk.Frame(header, bg=g["ACCENT"], width=4)
        accent_strip.pack(side="left", fill="y")
        title = tk.Label(
            header,
            text="StickyNote",
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        title.pack(side="left", padx=(10, 8), fill="y")
        drag_state = {"x": 0, "y": 0}

        def activate(widget: tk.Widget | None = None) -> None:
            try:
                win.lift()
                win.focus_force()
                (widget or win).focus_force()
            except tk.TclError:
                pass

        def start_drag(event) -> None:
            drag_state["x"] = event.x_root - win.winfo_x()
            drag_state["y"] = event.y_root - win.winfo_y()

        def drag_window(event) -> None:
            win.geometry(f"+{event.x_root - drag_state['x']}+{event.y_root - drag_state['y']}")

        for drag_target in (header, title):
            drag_target.bind("<ButtonPress-1>", start_drag)
            drag_target.bind("<B1-Motion>", drag_window)

        new_btn = self._header_button(header, f"+ {t('sticky.new')}", self.new_note)
        open_btn = self._header_button(header, f"↗ {t('sticky.open_main')}", self.open_in_main)
        self.pin_btn = self._header_button(header, "📌", self.toggle_pin)
        self.pin_btn.pack(side="right", padx=(2, 8), pady=8)
        open_btn.pack(side="right", padx=2, pady=8)
        new_btn.pack(side="right", padx=2, pady=8)

        self.title_var = tk.StringVar()
        title_row = tk.Frame(shell, bg=g["BG"])
        title_row.pack(fill="x", padx=12, pady=(12, 7))
        tk.Label(
            title_row,
            text=t("sticky.note_title"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 6))
        title_input_shell = tk.Frame(
            title_row,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
        )
        title_input_shell.pack(side="left", fill="x", expand=True)
        self.title_entry = tk.Entry(
            title_input_shell,
            textvariable=self.title_var,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            insertbackground=g["TEXT"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            takefocus=True,
        )
        self.title_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(8, 8))
        self.title_entry.bind("<KeyRelease>", lambda _event: self.schedule_save())
        self.title_entry.bind("<ButtonPress-1>", lambda _event: activate(self.title_entry), add="+")
        self.title_entry.bind("<FocusIn>", lambda _event: self.title_input_shell.configure(highlightbackground=globals()["ACCENT"]))
        self.title_entry.bind("<FocusOut>", lambda _event: self.title_input_shell.configure(highlightbackground=globals()["BORDER"]))
        self.title_input_shell = title_input_shell

        body_outer = tk.Frame(
            shell,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
        )
        body_outer.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        body_frame = tk.Frame(body_outer, bg=g["SURFACE"])
        body_frame.pack(fill="both", expand=True, padx=1, pady=1)
        self.text = tk.Text(
            body_frame,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            insertbackground=g["TEXT"],
            selectbackground=g["ACCENT"],
            selectforeground=app._contrast_text(g["ACCENT"]),
            relief="flat",
            wrap="word",
            padx=10,
            pady=9,
            undo=True,
            font=(app.config.font_family, app.config.font_size),
            takefocus=True,
        )
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure("sticky_image_preview", justify="center")
        self.scrollbar = app._attach_dark_scrollbar(body_frame, self.text)
        self.text.bind("<KeyRelease>", lambda _event: self.schedule_save())
        self.text.bind("<Control-s>", lambda _event: self.save_now() or "break")
        self.text.bind("<Control-v>", self.paste_from_clipboard)
        self.text.bind("<Control-V>", self.paste_from_clipboard)
        self.text.bind("<ButtonPress-1>", lambda _event: activate(self.text), add="+")

        footer = tk.Frame(shell, bg=g["BG"])
        footer.pack(fill="x", padx=12, pady=(0, 9))
        self.status = tk.Label(
            footer,
            text="",
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.status.pack(side="left", fill="x", expand=True)
        resize_grip = tk.Label(
            footer,
            text="◢",
            bg=g["BG"],
            fg=g["MUTED"],
            cursor="size_nw_se",
            font=("Segoe UI", 8),
        )
        resize_grip.pack(side="right")
        resize_state = {"w": 0, "h": 0, "x": 0, "y": 0}

        def start_resize(event) -> None:
            resize_state.update({"w": win.winfo_width(), "h": win.winfo_height(), "x": event.x_root, "y": event.y_root})

        def resize_window(event) -> None:
            next_w = max(300, resize_state["w"] + event.x_root - resize_state["x"])
            next_h = max(240, resize_state["h"] + event.y_root - resize_state["y"])
            win.geometry(f"{next_w}x{next_h}")

        resize_grip.bind("<ButtonPress-1>", start_resize)
        resize_grip.bind("<B1-Motion>", resize_window)

        self.win = win
        self.shell = shell
        self.header = header
        self.accent_strip = accent_strip
        self.title_label = title
        self.title_row = title_row
        self.title_input_shell = title_input_shell
        self.body_outer = body_outer
        self.body_frame = body_frame
        self.footer = footer
        self.resize_grip = resize_grip
        self._tag_dropdown = None
        self._image_previews: list[dict[str, object]] = []
        controllers = [
            controller
            for controller in getattr(app, "_sticky_notes_controllers", [])
            if controller is not None and getattr(controller, "win", None) is not None
        ]
        controllers.append(self)
        app._sticky_notes_controllers = controllers
        app._sticky_notes_windows = [*open_windows, win]
        app._sticky_notes_window = win
        app._sticky_notes_controller = self
        self.load_latest_or_new()
        self.refresh_theme()
        for focus_target in (shell, title_row, title_input_shell, body_outer, body_frame, footer):
            focus_target.bind("<ButtonPress-1>", lambda _event: activate(), add="+")
        win.protocol("WM_DELETE_WINDOW", self.close)
        win.bind("<Escape>", lambda _event: self.close())
        win.update_idletasks()
        win.deiconify()
        try:
            win.lift(parent)
        except tk.TclError:
            win.lift()
        activate(self.text)
        win.after(80, lambda: activate(self.text))

    def _header_button(self, parent: tk.Widget, text: str, command) -> tk.Label:
        button = tk.Label(
            parent,
            text=text,
            bg=globals()["SURFACE_2"],
            fg=globals()["TEXT"],
            font=("Segoe UI Emoji", 9, "bold"),
            cursor="hand2",
            padx=9,
            pady=3,
        )
        button.bind("<Button-1>", lambda _event: command())
        button.bind("<Enter>", lambda _event: self._style_header_button(button, hover=True))
        button.bind("<Leave>", lambda _event: self._style_header_button(button, hover=False))
        return button

    def _style_header_button(self, button: tk.Label, *, hover: bool = False) -> None:
        g = globals()
        if button is getattr(self, "pin_btn", None):
            pinned = bool(self.app.config.sticky_notes_pinned)
            if pinned:
                bg = g["ACCENT_2"] if hover else g["ACCENT"]
                fg = self.app._contrast_text(bg)
            else:
                bg = g["BORDER"] if hover else g["SURFACE_2"]
                fg = g["TEXT"]
            button.configure(bg=bg, fg=fg)
            return
        button.configure(bg=g["BORDER"] if hover else g["SURFACE_2"], fg=g["TEXT"])

    def update_pin_button(self) -> None:
        pinned = bool(self.app.config.sticky_notes_pinned)
        label = t("sticky.pin.pinned") if pinned else t("sticky.pin")
        self.pin_btn.configure(text=f"📌 {label}")
        self._style_header_button(self.pin_btn, hover=False)

    def _live_windows(self) -> list[tk.Toplevel]:
        live: list[tk.Toplevel] = []
        for window in getattr(self.app, "_sticky_notes_windows", []) or []:
            try:
                if window is not None and window.winfo_exists():
                    live.append(window)
            except tk.TclError:
                pass
        self.app._sticky_notes_windows = live
        return live

    def available_tags(self) -> tuple[str, ...]:
        tags = set(getattr(self.app, "_tag_counts", {}) or {})
        default = self.app.config.sticky_notes_default_tag
        if default:
            tags.add(default)
        return tuple(sorted(tags, key=str.casefold))

    def close_tag_dropdown(self) -> None:
        popup = getattr(self, "_tag_dropdown", None)
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
            self._tag_dropdown = None

    def show_tag_dropdown(self) -> None:
        self.close_tag_dropdown()
        values = self.available_tags()
        if not values:
            return
        g = globals()
        popup = tk.Toplevel(self.win)
        popup.overrideredirect(True)
        popup.configure(bg=g["BORDER"])
        popup.transient(self.win)
        shell = tk.Frame(popup, bg=g["SURFACE"], padx=1, pady=1)
        shell.pack(fill="both", expand=True, padx=1, pady=1)
        width = max(180, self.tag_input_shell.winfo_width())
        max_rows = min(8, len(values))

        def choose(value: str) -> None:
            current = normalize_sticky_tags(self.tag_var.get())
            if value not in current:
                current.append(value)
            self.tag_var.set(", ".join(current))
            self.schedule_save()
            self.close_tag_dropdown()
            self.tag_entry.focus_set()

        for value in values[:max_rows]:
            row = tk.Label(
                shell,
                text=f"#{value}",
                bg=g["SURFACE"],
                fg=g["TEXT_SOFT"],
                anchor="w",
                padx=10,
                pady=6,
                font=("Segoe UI", 9),
                cursor="hand2",
            )
            row.pack(fill="x")
            row.bind("<Button-1>", lambda _event, item=value: choose(item))
            row.bind("<Enter>", lambda _event, widget=row: widget.configure(bg=globals()["SURFACE_2"], fg=globals()["TEXT"]))
            row.bind("<Leave>", lambda _event, widget=row: widget.configure(bg=globals()["SURFACE"], fg=globals()["TEXT_SOFT"]))
        x = self.tag_input_shell.winfo_rootx()
        y = self.tag_input_shell.winfo_rooty() + self.tag_input_shell.winfo_height() + 4
        popup.geometry(f"{width}x{max_rows * 32 + 4}+{x}+{y}")
        popup.bind("<Escape>", lambda _event: self.close_tag_dropdown())
        popup.bind("<FocusOut>", lambda _event: popup.after(80, self.close_tag_dropdown))
        self._tag_dropdown = popup
        popup.deiconify()
        popup.lift(self.win)

    def load_latest_or_new(self) -> None:
        if self.initial_path is not None and self.initial_path.exists():
            self.load_path(self.initial_path)
            return
        if self.create_new_note:
            self.new_note()
            return
        paths = sticky_note_paths(sticky_notes_folder(self.app))
        if paths:
            self.load_path(paths[0])
        else:
            self.new_note()

    def load_path(self, path: Path) -> None:
        self.loading = True
        self.path = path
        try:
            content = read_text_file(path)
        except OSError:
            content = ""
        metadata = parse_front_matter(content, path.stem)
        _header, body = split_front_matter(content)
        self.created = metadata.created or date.today().isoformat()
        self.title_var.set(metadata.title or sticky_title(body, path.stem))
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", body)
        self.status.configure(text=t("sticky.saved_to", name=path.name))
        self.loading = False
        self.win.after_idle(self.refresh_image_previews)

    def new_note(self) -> None:
        if hasattr(self, "text") and self.path is not None:
            self.save_now()
        self.loading = True
        folder = sticky_notes_folder(self.app)
        self.path = next_sticky_path(folder)
        self.created = date.today().isoformat()
        self.title_var.set(t("sticky.new_note"))
        if hasattr(self, "text"):
            self.clear_image_previews()
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.status.configure(text=t("sticky.new_note"))
            self.text.focus_set()
        self.loading = False
        self.save_now()

    def tags(self) -> list[str]:
        return normalize_sticky_tags(PLUGIN_TAGS)

    def body(self) -> str:
        self.clear_image_previews()
        return self.text.get("1.0", "end-1c")

    def note_title(self, body: str) -> str:
        explicit = self.title_var.get().strip() if hasattr(self, "title_var") else ""
        return explicit[:80] if explicit else sticky_title(body, self.path.stem if self.path else t("sticky.new_note"))

    def attachment_folder(self) -> Path | None:
        if self.path is None:
            return None
        root = self.app._workspace_dir().resolve()
        attachments_root = (root / self.app.config.attachments_folder).resolve()
        folder = (attachments_root / PLUGIN_FOLDER / self.path.stem).resolve()
        try:
            folder.relative_to(attachments_root)
        except ValueError:
            return None
        return folder

    def unique_attachment_path(self, folder: Path, name: str) -> Path:
        cleaned = safe_attachment_name(name)
        target = folder / cleaned
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix or ".png"
        for index in range(2, 10000):
            candidate = folder / safe_attachment_name(f"{stem}-{index}{suffix}")
            if not candidate.exists():
                return candidate
        return folder / safe_attachment_name(f"{stem}-{int(time.time())}{suffix}")

    def markdown_relative_path(self, target: Path) -> str:
        if self.path is None:
            return target.name
        try:
            return Path(os.path.relpath(target.resolve(), self.path.parent.resolve())).as_posix()
        except (OSError, ValueError):
            return target.as_posix()

    def paste_from_clipboard(self, _event=None):
        if self.save_clipboard_image():
            return "break"
        return None

    def save_clipboard_image(self) -> bool:
        try:
            image = ImageGrab.grabclipboard()
        except Exception as exc:
            self.status.configure(text=t("error.clipboard_unavailable", exc=exc), fg=globals()["DANGER"])
            return False
        if not isinstance(image, Image.Image):
            return False
        self.save_now()
        folder = self.attachment_folder()
        if folder is None:
            self.status.configure(text=t("error.images_need_note"), fg=globals()["DANGER"])
            return True
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = self.unique_attachment_path(folder, time.strftime("sticky-%Y%m%d-%H%M%S.png"))
            image.save(target, "PNG")
        except OSError as exc:
            self.status.configure(text=t("error.image_save_failed", exc=exc), fg=globals()["DANGER"])
            return True
        rel = self.markdown_relative_path(target)
        label = target.stem.replace("_", " ")
        if self.text.compare("insert", "!=", "1.0"):
            before = self.text.get("insert -1c", "insert")
            if before not in {"", "\n"}:
                self.text.insert("insert", "\n")
        self.text.insert("insert", f"![{label}]({rel})\n")
        self.refresh_image_previews()
        self.save_now()
        return True

    def clear_image_previews(self) -> None:
        for preview in getattr(self, "_image_previews", []):
            mark = preview.get("mark")
            try:
                if mark is not None:
                    self.text.delete(str(mark), f"{mark}+2c")
                    self.text.mark_unset(str(mark))
            except tk.TclError:
                pass
        self._image_previews = []

    def resolve_markdown_image_path(self, raw_path: str) -> Path | None:
        if self.path is None:
            return None
        cleaned = raw_path.strip().strip("<>").replace("%20", " ")
        is_windows_drive = bool(re.match(r"^[a-zA-Z]:[\\/]", cleaned))
        if not is_windows_drive and re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", cleaned):
            return None
        path = Path(cleaned)
        if not path.is_absolute():
            path = self.path.parent / path
        return path

    def refresh_image_previews(self) -> None:
        if not hasattr(self, "text"):
            return
        self.clear_image_previews()
        try:
            max_width = max(120, self.text.winfo_width() - 48)
            content = self.text.get("1.0", "end-1c")
        except tk.TclError:
            return
        for line_number, line in enumerate(content.splitlines(), start=1):
            match = IMAGE_MD_RE.search(line.strip())
            if match is None:
                continue
            image_path = self.resolve_markdown_image_path(match.group(1))
            if image_path is None or not image_path.exists():
                continue
            try:
                image = load_thumbnail_image(image_path, (max_width, 160))
                photo = ImageTk.PhotoImage(image)
                insert_at = f"{line_number}.end"
                mark = f"sticky_image_preview_{line_number}_{len(self._image_previews)}"
                self.text.mark_set(mark, insert_at)
                self.text.mark_gravity(mark, tk.LEFT)
                self.text.insert(mark, "\n")
                self.text.image_create(f"{mark}+1c", image=photo, padx=4, pady=6)
                self.text.tag_add("sticky_image_preview", f"{mark}+1c", f"{mark}+2c")
                self._image_previews.append({"mark": mark, "photo": photo})
            except Exception as exc:
                self.status.configure(text=t("error.image_preview_failed", exc=exc), fg=globals()["DANGER"])

    def sync_path_to_title(self, title: str) -> tuple[Path, str]:
        current = self.path
        folder = current.parent if current is not None else sticky_notes_folder(self.app)
        target = unique_sticky_path_for_title(folder, title, current)
        resolved_title = target.stem
        if current is None:
            self.path = target
            return target, resolved_title
        try:
            same_path = current.resolve() == target.resolve()
        except OSError:
            same_path = current == target
        if not same_path:
            try:
                if hasattr(self.app, "_mark_vault_internal_write"):
                    self.app._mark_vault_internal_write(current)
                    self.app._mark_vault_internal_write(target)
                if current.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    current.rename(target)
                self.path = target
            except OSError:
                self.path = current
                return current, current.stem
        return self.path, resolved_title

    def schedule_save(self) -> None:
        if self.loading:
            return
        if self.save_after is not None:
            try:
                self.win.after_cancel(self.save_after)
            except tk.TclError:
                pass
        self.save_after = self.win.after(AUTOSAVE_DELAY_MS, self.save_now)
        self.status.configure(text=t("sticky.saving"))

    def save_now(self) -> None:
        self.save_after = None
        body = self.body() if hasattr(self, "text") else ""
        requested_title = self.note_title(body)
        path, title = self.sync_path_to_title(requested_title)
        if hasattr(self, "title_var") and self.title_var.get().strip() != title:
            self.title_var.set(title)
        content = sticky_note_content(body, self.tags(), title=title, created=self.created)
        try:
            if hasattr(self.app, "_mark_vault_internal_write"):
                self.app._mark_vault_internal_write(path)
            safe_write_text(content=content, path=path, workspace_root=self.app._workspace_dir())
        except OSError as exc:
            self.status.configure(text=t("sticky.error_save", exc=exc), fg=globals()["DANGER"])
            return
        self.status.configure(text=t("sticky.saved_to", name=path.name), fg=globals()["MUTED"])
        self.refresh_image_previews()
        self.schedule_workspace_refresh()

    def schedule_workspace_refresh(self) -> None:
        if self.refresh_after is not None:
            try:
                self.win.after_cancel(self.refresh_after)
            except tk.TclError:
                pass
        self.refresh_after = self.win.after(350, self.refresh_workspace)

    def refresh_workspace(self) -> None:
        self.refresh_after = None
        if hasattr(self.app, "_refresh_explorer"):
            self.app._refresh_explorer()
        if hasattr(self.app, "_schedule_wiki_index_refresh"):
            self.app._schedule_wiki_index_refresh()

    def open_in_main(self) -> None:
        self.save_now()
        if self.path is not None and hasattr(self.app, "_open_file_in_editor"):
            self.app._open_file_in_editor(self.path, reveal_panel=True, prefer_split=False)

    def toggle_pin(self) -> None:
        pinned = not bool(self.app.config.sticky_notes_pinned)
        self.app.config.sticky_notes_pinned = pinned
        save_config(self.app.config)
        self.win.attributes("-topmost", pinned)
        self.status.configure(text=t("sticky.pinned_to_screen") if pinned else t("sticky.unpinned_from_screen"), fg=globals()["MUTED"])
        self.refresh_theme()

    def toggle_double_ctrl(self) -> None:
        self.double_ctrl_var.set(not bool(self.double_ctrl_var.get()))
        self.app.config.sticky_notes_double_ctrl = bool(self.double_ctrl_var.get())
        save_config(self.app.config)
        if hasattr(self.app, "_register_sticky_notes_hotkey"):
            self.app._register_sticky_notes_hotkey()
        self._draw_double_ctrl_toggle()

    def refresh_theme(self) -> None:
        g = globals()
        try:
            self.win.configure(bg=g["BORDER"])
            self.shell.configure(bg=g["BG"], highlightbackground=g["BORDER"])
            self.header.configure(bg=g["SURFACE"])
            self.accent_strip.configure(bg=g["ACCENT"])
            self.title_label.configure(bg=g["SURFACE"], fg=g["TEXT"])
            self.update_pin_button()
            self.title_row.configure(bg=g["BG"])
            self.title_input_shell.configure(bg=g["SURFACE"], highlightbackground=g["BORDER"])
            self.title_entry.configure(bg=g["SURFACE"], fg=g["TEXT"], insertbackground=g["TEXT"])
            self.body_outer.configure(bg=g["SURFACE"], highlightbackground=g["BORDER"])
            self.body_frame.configure(bg=g["SURFACE"])
            self.text.configure(
                bg=g["SURFACE"],
                fg=g["TEXT"],
                insertbackground=g["TEXT"],
                selectbackground=g["ACCENT"],
                selectforeground=self.app._contrast_text(g["ACCENT"]),
                state="normal",
            )
            self.footer.configure(bg=g["BG"])
            self.status.configure(bg=g["BG"], fg=g["MUTED"])
            self.resize_grip.configure(bg=g["BG"], fg=g["MUTED"])
        except tk.TclError:
            pass

    def _draw_double_ctrl_toggle(self) -> None:
        g = globals()
        enabled = bool(self.double_ctrl_var.get())
        canvas = self.double_ctrl_track
        canvas.configure(bg=g["BG"])
        canvas.delete("all")
        track = g["ACCENT"] if enabled else g["BORDER"]
        knob = self.app._contrast_text(track) if enabled else g["MUTED"]
        canvas.create_oval(1, 2, 17, 16, fill=track, outline=track)
        canvas.create_oval(17, 2, 33, 16, fill=track, outline=track)
        canvas.create_rectangle(9, 2, 25, 16, fill=track, outline=track)
        x0 = 18 if enabled else 3
        canvas.create_oval(x0, 3, x0 + 12, 15, fill=knob, outline=knob)

    def close(self) -> None:
        self.close_tag_dropdown()
        if self.save_after is not None:
            try:
                self.win.after_cancel(self.save_after)
            except tk.TclError:
                pass
            self.save_after = None
        self.save_now()
        if self.refresh_after is not None:
            try:
                self.win.after_cancel(self.refresh_after)
            except tk.TclError:
                pass
            self.refresh_after = None
        self.refresh_workspace()
        remaining = [window for window in self._live_windows() if window is not self.win]
        self.app._sticky_notes_windows = remaining
        if getattr(self.app, "_sticky_notes_window", None) is self.win:
            self.app._sticky_notes_window = remaining[-1] if remaining else None
        if getattr(self.app, "_sticky_notes_controller", None) is self:
            self.app._sticky_notes_controller = None
        controllers = [
            controller
            for controller in getattr(self.app, "_sticky_notes_controllers", []) or []
            if controller is not self
        ]
        self.app._sticky_notes_controllers = controllers
        try:
            self.win.destroy()
        except tk.TclError:
            pass
