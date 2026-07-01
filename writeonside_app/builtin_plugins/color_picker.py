from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path

from PIL import Image, ImageGrab, ImageTk

from ..color_picker_store import (
    append_color_pick,
    color_picker_day_file,
    normalize_pick_hex,
    parse_pick_lines,
)
from ..i18n import t
from ..platform import redraw_window, set_window_redraw
from ..storage import read_text_file
from ..theme import *  # noqa: F401,F403


def run(app) -> None:
    # Opening the picker jumps straight into screen selection; the record
    # window only surfaces once a color has been picked (or cancelled).
    ColorPickerPlugin(app).open(pick_first=True)


def _plugin_button(app, parent: tk.Widget, text: str, command, *, primary: bool = False) -> tk.Button:
    g = globals()
    contrast = app._contrast_text(g["ACCENT"]) if hasattr(app, "_contrast_text") else g["TEXT"]
    bg = g["ACCENT"] if primary else g["BORDER"]
    fg = contrast if primary else g["TEXT"]
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=g["ACCENT"],
        activeforeground=contrast,
        relief="flat",
        padx=12,
        pady=6,
        cursor="hand2",
    )


def _rgb_at_screen(x: int, y: int) -> tuple[str, tuple[int, int, int]]:
    image = ImageGrab.grab(bbox=(x, y, x + 1, y + 1))
    red, green, blue = image.getpixel((0, 0))[:3]
    return f"#{red:02X}{green:02X}{blue:02X}", (red, green, blue)


class ScreenColorPickerSession:
    LOUPE_SIZE = 132
    LOUPE_WIDTH = 172
    PREVIEW_HEIGHT = 32
    ZOOM = 8
    POLL_MS = 16
    OFFSET = 20
    CROSSHAIR_OUTLINE = "#FF0000"
    CROSSHAIR_WIDTH = 2
    CROSSHAIR_HALO = "#FFFFFF"
    PREVIEW_BG = "#FFFFFF"
    PREVIEW_BORDER = "#E5E5E5"
    PREVIEW_TEXT = "#1A1A1A"

    def __init__(self, app, on_complete) -> None:
        self.app = app
        self.on_complete = on_complete
        self._active = True
        self._poll_after: str | None = None
        self._last_pos: tuple[int, int] | None = None
        self._last_hex = "#000000"
        self._last_rgb = (0, 0, 0)
        self.overlay = tk.Toplevel(app.root)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", 0.01)
        self.overlay.configure(bg="black", cursor="crosshair")
        self.overlay.overrideredirect(True)

        self.loupe = tk.Toplevel(app.root)
        self.loupe.attributes("-topmost", True)
        self.loupe.overrideredirect(True)
        self.loupe.configure(bg=self.PREVIEW_BG)

        magnifier_wrap = tk.Frame(self.loupe, bg=self.PREVIEW_BG)
        magnifier_wrap.pack(padx=6, pady=(6, 0))
        self.loupe_canvas = tk.Canvas(
            magnifier_wrap,
            width=self.LOUPE_SIZE,
            height=self.LOUPE_SIZE,
            highlightthickness=1,
            highlightbackground=self.PREVIEW_BORDER,
            bd=0,
            bg="#F5F5F5",
        )
        self.loupe_canvas.pack()

        self.preview = tk.Frame(
            self.loupe,
            bg=self.PREVIEW_BG,
            highlightthickness=1,
            highlightbackground=self.PREVIEW_BORDER,
            padx=10,
            pady=8,
        )
        self.preview.pack(fill="x", padx=6, pady=(4, 6))
        self.preview_swatch = tk.Canvas(
            self.preview,
            width=28,
            height=28,
            highlightthickness=0,
            bd=0,
            relief="flat",
            bg=self._last_hex,
        )
        self.preview_swatch.pack(side="left", padx=(0, 10))
        self.preview_swatch.create_rectangle(0, 0, 28, 28, fill=self._last_hex, outline="")
        self.preview_hex = tk.Label(
            self.preview,
            text=self._last_hex,
            bg=self.PREVIEW_BG,
            fg=self.PREVIEW_TEXT,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        self.preview_hex.pack(side="left", fill="both", expand=True)

        self._screen_w = self.overlay.winfo_screenwidth()
        self._screen_h = self.overlay.winfo_screenheight()
        self._loupe_height = self.LOUPE_SIZE + self.PREVIEW_HEIGHT + 24

        self.overlay.bind("<Button-1>", self._on_click)
        self.overlay.bind("<Escape>", lambda _event: self.cancel())
        self.overlay.bind("<Button-3>", lambda _event: self.cancel())
        self.overlay.focus_force()
        # Poll the pointer position on a fixed cadence instead of reacting to a
        # flood of <Motion> events; this keeps the loupe glued to the cursor.
        self._poll()

    def cancel(self) -> None:
        self._teardown()
        self.on_complete(None)

    def _teardown(self) -> None:
        if not self._active:
            return
        self._active = False
        if self._poll_after is not None:
            try:
                self.app.root.after_cancel(self._poll_after)
            except Exception:
                pass
            self._poll_after = None
        for window in (self.overlay, self.loupe):
            try:
                window.destroy()
            except tk.TclError:
                pass

    def _move_loupe(self, x: int, y: int) -> None:
        loupe_x = x + self.OFFSET
        loupe_y = y + self.OFFSET
        if loupe_x + self.LOUPE_WIDTH > self._screen_w:
            loupe_x = max(0, x - self.LOUPE_WIDTH - self.OFFSET)
        if loupe_y + self._loupe_height > self._screen_h:
            loupe_y = max(0, y - self._loupe_height - self.OFFSET)
        self.loupe.geometry(f"{self.LOUPE_WIDTH}x{self._loupe_height}+{loupe_x}+{loupe_y}")

    def _update_loupe_preview(self) -> None:
        self.preview_swatch.configure(bg=self._last_hex)
        self.preview_swatch.delete("all")
        self.preview_swatch.create_rectangle(0, 0, 28, 28, fill=self._last_hex, outline="")
        self.preview_hex.configure(text=self._last_hex)

    def _update_loupe_image(self, x: int, y: int) -> None:
        half = max(1, self.LOUPE_SIZE // (2 * self.ZOOM))
        bbox = (x - half, y - half, x + half, y + half)
        try:
            image = ImageGrab.grab(bbox=bbox).resize(
                (self.LOUPE_SIZE, self.LOUPE_SIZE), Image.Resampling.NEAREST
            )
        except Exception:
            return
        self._loupe_photo = ImageTk.PhotoImage(image=image)
        self.loupe_canvas.delete("all")
        self.loupe_canvas.create_image(0, 0, anchor="nw", image=self._loupe_photo)
        cx = self.LOUPE_SIZE // 2
        half = 4
        # Fixed red crosshair — always visible regardless of the sampled pixel color.
        self.loupe_canvas.create_rectangle(
            cx - half - 1,
            cx - half - 1,
            cx + half + 1,
            cx + half + 1,
            outline=self.CROSSHAIR_HALO,
            width=self.CROSSHAIR_WIDTH + 2,
        )
        self.loupe_canvas.create_rectangle(
            cx - half,
            cx - half,
            cx + half,
            cx + half,
            outline=self.CROSSHAIR_OUTLINE,
            width=self.CROSSHAIR_WIDTH,
        )
        self._update_loupe_preview()

    def _poll(self) -> None:
        if not self._active:
            return
        try:
            x = self.overlay.winfo_pointerx()
            y = self.overlay.winfo_pointery()
        except tk.TclError:
            return
        if (x, y) != self._last_pos:
            self._last_pos = (x, y)
            # Move first (cheap) so the loupe tracks the cursor with no lag,
            # then refresh the magnified sample.
            self._move_loupe(x, y)
            self._last_hex, self._last_rgb = _rgb_at_screen(x, y)
            self._update_loupe_image(x, y)
        try:
            self._poll_after = self.app.root.after(self.POLL_MS, self._poll)
        except tk.TclError:
            self._poll_after = None

    def _on_click(self, event) -> None:
        if not self._active:
            return
        x = self.overlay.winfo_pointerx()
        y = self.overlay.winfo_pointery()
        hex_color, rgb = _rgb_at_screen(x, y)
        self._teardown()
        self.on_complete({"hex": hex_color, "rgb": rgb, "x": x, "y": y})


class ColorPickerPlugin:
    def __init__(self, app) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self._redraw_handle: int | None = None
        self._pick_session: ScreenColorPickerSession | None = None
        self._history_rows: list[tuple[tk.Frame, tk.Label, tk.Label, tk.Label]] = []
        self._display_picks: list[dict[str, str]] = []
        self._body_frame: tk.Frame | None = None
        self._hero_frame: tk.Frame | None = None
        self._history_card: tk.Frame | None = None
        self._action_bar: tk.Frame | None = None

    def open(self, pick_first: bool = False) -> None:
        app = self.app
        if getattr(app, "_color_picker_open", False):
            existing = getattr(app, "_color_picker_window", None)
            try:
                if existing is not None:
                    win = getattr(existing, "win", None)
                    if pick_first:
                        existing._start_screen_pick(reveal_after=True)
                        return
                    if win is not None and win.winfo_exists():
                        existing._show_plugin_window()
                        return
            except tk.TclError:
                pass
            app._color_picker_open = False

        parent = getattr(app, "_plugin_parent_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = app.root
        except tk.TclError:
            parent = app.root

        g = globals()
        win = tk.Toplevel(parent)
        self.win = win
        app._color_picker_open = True
        app._color_picker_window = self
        win.withdraw()
        win.title(t("color_picker.window_title"))

        work_width = max(420, app.work_right - app.work_left)
        work_height = max(360, app.work_bottom - app.work_top)
        width = min(720, max(480, work_width - 64))
        height = min(680, max(480, work_height - 64))
        x = app.work_left + max(0, (work_width - width) // 2)
        y = app.work_top + max(0, (work_height - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.minsize(min(480, width), min(420, height))
        win.configure(bg=g["BG"])
        try:
            win.transient(parent)
        except tk.TclError:
            pass

        redraw_handle = None
        if hasattr(app, "_window_handle"):
            try:
                redraw_handle = app._window_handle(win)
                if redraw_handle is not None:
                    set_window_redraw(redraw_handle, False)
            except (AttributeError, tk.TclError, ValueError):
                redraw_handle = None
        self._redraw_handle = redraw_handle

        footer = tk.Label(
            win,
            text=t("color_picker.footer_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=max(320, width - 44),
        )
        footer.pack(fill="x", side="bottom", padx=22, pady=(0, 12))
        self.status = footer

        action_bar = tk.Frame(win, bg=g["BG"])
        action_bar.pack(fill="x", side="bottom", padx=22, pady=(0, 8))
        self._action_bar = action_bar
        _plugin_button(app, action_bar, t("color_picker.open_log"), self._open_today_log).pack(side="right", padx=(8, 0))
        _plugin_button(app, action_bar, t("color_picker.pick_screen"), self._start_screen_pick, primary=True).pack(side="right")

        body = tk.Frame(win, bg=g["BG"])
        body.pack(fill="both", expand=True, padx=22, pady=(16, 8))
        self._body_frame = body

        hero = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=16,
            pady=14,
        )
        hero.pack(fill="x", pady=(0, 10))
        self._hero_frame = hero
        self._hero_title = tk.Label(hero, text=t("color_picker.title"), bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI", 15, "bold"), anchor="w")
        self._hero_title.pack(fill="x")
        self.subtitle = tk.Label(
            hero,
            text=t("color_picker.subtitle", day=date.today().isoformat()),
            bg=g["SURFACE"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=max(320, width - 80),
        )
        self.subtitle.pack(fill="x", pady=(4, 0))

        history_card = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=12,
            pady=12,
        )
        history_card.pack(fill="both", expand=True)
        self._history_card = history_card
        self._history_heading = tk.Label(
            history_card,
            text=t("color_picker.section.history"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self._history_heading.pack(fill="x", pady=(0, 8))
        self.history_host = tk.Frame(history_card, bg=g["SURFACE"])
        self.history_host.pack(fill="both", expand=True)

        def close() -> None:
            if self._pick_session is not None:
                self._pick_session.cancel()
                self._pick_session = None
            app._color_picker_open = False
            app._color_picker_window = None
            if getattr(app, "_refresh_color_picker_theme", None) is refresh_theme:
                try:
                    delattr(app, "_refresh_color_picker_theme")
                except AttributeError:
                    pass
            try:
                win.destroy()
            except tk.TclError:
                pass

        def refresh_theme() -> None:
            self._apply_plugin_colors()
            self._reload_history()

        app._refresh_color_picker_theme = refresh_theme
        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _event: close())

        refresh_theme()
        win.update_idletasks()
        if pick_first:
            app.root.after(60, lambda: self._start_screen_pick(reveal_after=True))
        else:
            self._show_plugin_window()

    def _workspace(self) -> Path:
        return self.app._workspace_dir().resolve()

    def _today_file(self) -> Path:
        return color_picker_day_file(self._workspace())

    def _apply_plugin_colors(self) -> None:
        g = globals()
        win = self.win
        if win is not None:
            try:
                win.configure(bg=g["BG"])
            except tk.TclError:
                pass
        for frame in (self._body_frame, self._action_bar):
            if frame is not None:
                try:
                    frame.configure(bg=g["BG"])
                except tk.TclError:
                    pass
        if self._hero_frame is not None:
            try:
                self._hero_frame.configure(bg=g["SURFACE"], highlightbackground=g["BORDER"])
            except tk.TclError:
                pass
        if self._history_card is not None:
            try:
                self._history_card.configure(bg=g["SURFACE"], highlightbackground=g["BORDER"])
            except tk.TclError:
                pass
        if self.subtitle is not None:
            try:
                self.subtitle.configure(bg=g["SURFACE"], fg=g["MUTED"])
            except tk.TclError:
                pass
        if getattr(self, "_hero_title", None) is not None:
            try:
                self._hero_title.configure(bg=g["SURFACE"], fg=g["TEXT"])
            except tk.TclError:
                pass
        if getattr(self, "_history_heading", None) is not None:
            try:
                self._history_heading.configure(bg=g["SURFACE"], fg=g["TEXT"])
            except tk.TclError:
                pass
        if self.status is not None:
            try:
                self.status.configure(bg=g["BG"], fg=g["MUTED"])
            except tk.TclError:
                pass
        if self.history_host is not None:
            try:
                self.history_host.configure(bg=g["SURFACE"])
            except tk.TclError:
                pass
        for row, swatch, sample, time_label in self._history_rows:
            for widget in (row, sample, time_label):
                try:
                    widget.configure(bg=g["SURFACE"])
                except tk.TclError:
                    pass
            try:
                time_label.configure(fg=g["TEXT"])
            except tk.TclError:
                pass

    def _show_plugin_window(self, *, status: str | None = None) -> None:
        win = self.win
        if win is None:
            return
        try:
            if not win.winfo_exists():
                return
        except tk.TclError:
            return
        handle = self._redraw_handle
        try:
            win.withdraw()
        except tk.TclError:
            return
        if handle is not None:
            set_window_redraw(handle, False)
        self._apply_plugin_colors()
        if status is not None and self.status is not None:
            try:
                self.status.configure(text=status, bg=globals()["BG"], fg=globals()["MUTED"])
            except tk.TclError:
                pass
        try:
            win.update_idletasks()
            win.deiconify()
            win.lift()
            win.focus_force()
            win.update_idletasks()
            win.update()
        except tk.TclError:
            if handle is not None:
                set_window_redraw(handle, True)
            return
        if handle is not None:
            set_window_redraw(handle, True)
            redraw_window(handle)

    def _start_screen_pick(self, reveal_after: bool = False) -> None:
        if self._pick_session is not None:
            return
        if self.win is not None:
            self.win.withdraw()

        def finished(result: dict | None) -> None:
            self._pick_session = None
            if result is None:
                self._show_plugin_window(status=t("color_picker.pick_cancelled"))
                return
            path = append_color_pick(
                self._workspace(),
                result["hex"],
                result["rgb"],
                result["x"],
                result["y"],
            )
            mark = getattr(self.app, "_mark_vault_internal_write", None)
            if mark is not None:
                mark(path)
            schedule = getattr(self.app, "_schedule_explorer_refresh", None)
            if schedule is not None:
                schedule()
            self._remember_pick(result)
            entry = self._display_picks[0]
            self._prepend_history_row(entry)
            self._show_plugin_window(
                status=t("color_picker.pick_saved", hex=normalize_pick_hex(result["hex"]))
            )
            self.app.root.after_idle(lambda p=path: self._refresh_open_log_note(p))

        self._pick_session = ScreenColorPickerSession(self.app, finished)

    def _remember_pick(self, result: dict) -> None:
        from datetime import datetime

        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "hex": normalize_pick_hex(result["hex"]),
        }
        self._display_picks = [entry] + [
            pick for pick in self._display_picks if pick.get("hex") != entry["hex"] or pick.get("time") != entry["time"]
        ]

    def _refresh_open_log_note(self, path: Path) -> None:
        current = getattr(self.app, "current_note_path", None)
        if current is None:
            return
        try:
            if Path(current).resolve() != path.resolve():
                return
        except OSError:
            return
        if getattr(self.app, "_dirty", False):
            return
        if getattr(self.app, "view_mode", "edit") == "read" and hasattr(self.app, "_render_read_content"):
            self.app._render_read_content()
            return
        if hasattr(self.app, "_reload_main_editor_from_disk"):
            self.app._reload_main_editor_from_disk(path)
        elif hasattr(self.app, "_schedule_live_render"):
            self.app._schedule_live_render()

    def _load_picks_from_file(self) -> list[dict[str, str]]:
        path = self._today_file()
        if not path.exists():
            return []
        try:
            content = read_text_file(path)
        except OSError:
            return []
        return [{"time": str(pick["time"]), "hex": str(pick["hex"])} for pick in parse_pick_lines(content)]

    def _merge_display_picks(self, file_picks: list[dict[str, str]]) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for pick in self._display_picks + file_picks:
            key = (pick.get("time", ""), pick.get("hex", ""))
            if not key[0] or not key[1] or key in seen:
                continue
            seen.add(key)
            merged.append({"time": key[0], "hex": key[1]})
        return merged

    def _open_today_log(self) -> None:
        path = self._today_file()
        if not path.exists():
            if self.status is not None:
                self.status.configure(text=t("color_picker.no_log_today"))
            return
        if hasattr(self.app, "_open_file_in_editor"):
            self.app._open_file_in_editor(path, reveal_panel=True, prefer_split=False)

    def _clear_history_empty_label(self) -> None:
        if self.history_host is None:
            return
        empty_text = t("color_picker.history_empty")
        for child in self.history_host.winfo_children():
            if not isinstance(child, tk.Label):
                continue
            try:
                if child.cget("text") == empty_text:
                    child.destroy()
            except tk.TclError:
                pass

    def _build_history_row(self, pick: dict[str, str]) -> tuple[tk.Frame, tk.Label, tk.Label, tk.Label]:
        g = globals()
        row = tk.Frame(self.history_host, bg=g["SURFACE"])
        swatch = tk.Label(row, text="  ", bg=str(pick["hex"]), width=2, relief="flat")
        swatch.pack(side="left", padx=(0, 8))
        sample = tk.Label(row, text="A", bg=g["SURFACE"], fg=str(pick["hex"]), font=("Segoe UI", 12, "bold"))
        sample.pack(side="left", padx=(0, 8))
        time_label = tk.Label(
            row,
            text=f"{pick['time']}  {pick['hex']}",
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Consolas", 10),
            anchor="w",
        )
        time_label.pack(side="left", fill="x", expand=True)
        return row, swatch, sample, time_label

    def _prepend_history_row(self, pick: dict[str, str]) -> None:
        if self.history_host is None:
            return
        handle = self._redraw_handle
        if handle is not None:
            set_window_redraw(handle, False)
        host = self.history_host
        host.pack_forget()
        try:
            self._clear_history_empty_label()
            row, swatch, sample, time_label = self._build_history_row(pick)
            children = host.winfo_children()
            if children:
                row.pack(fill="x", pady=3, before=children[0])
            else:
                row.pack(fill="x", pady=3)
            self._history_rows.insert(0, (row, swatch, sample, time_label))
            host.update_idletasks()
        finally:
            host.pack(fill="both", expand=True)

    def _reload_history(self) -> None:
        if self.history_host is None:
            return
        handle = self._redraw_handle
        if handle is not None:
            set_window_redraw(handle, False)
        host = self.history_host
        host.pack_forget()
        try:
            for child in host.winfo_children():
                child.destroy()
            self._history_rows.clear()
            file_picks = self._load_picks_from_file()
            self._display_picks = self._merge_display_picks(file_picks)
            picks = self._display_picks
            g = globals()
            if not picks:
                tk.Label(
                    host,
                    text=t("color_picker.history_empty"),
                    bg=g["SURFACE"],
                    fg=g["MUTED"],
                    font=("Segoe UI", 10),
                    anchor="w",
                ).pack(fill="x")
                return
            for pick in picks:
                row, swatch, sample, time_label = self._build_history_row(pick)
                row.pack(fill="x", pady=3)
                self._history_rows.append((row, swatch, sample, time_label))
            host.update_idletasks()
        finally:
            host.pack(fill="both", expand=True)
