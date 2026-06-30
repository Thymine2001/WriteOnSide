from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable
from tkinter import filedialog
import tkinter as tk
import tkinter.font as tkfont
from PIL import Image, ImageDraw, ImageTk

from .. import theme as theme_module
from ..config import APP_NAME, AppConfig, normalize_plugin_shortcuts, normalize_relative_folder, save_config
from ..i18n import SUPPORTED_LANGUAGES, command_label, normalize_language, set_language, t
from ..hotkeys import format_hotkey_display, is_modifier_only_hotkey, normalize_hotkey, read_hotkey_clean, validate_hotkey
from ..layout_metrics import explorer_width_limits, panel_width_limits
from ..platform import is_startup_enabled, redraw_window, set_startup_enabled, set_window_redraw
from ..plugins import BUILTIN_PLUGINS, disable_plugin, enable_plugin, plugin_status, remove_plugin, restore_plugin
from ..shortcuts import (
    COMMAND_SHORTCUTS,
    DEFAULT_COMMAND_SHORTCUTS,
    normalize_command_shortcuts,
    shortcut_conflicts,
)
from ..storage import BACKUP_DIR
from ..theme import *  # noqa: F401,F403
from .typography import (
    FONT_CARD_TITLE_STRONG,
    FONT_CONTROL,
    FONT_PLUGIN_ICON_SMALL,
    FONT_PREVIEW_LABEL,
    FONT_PREVIEW_TITLE,
    FONT_UI,
    FONT_UI_SMALL,
    FONT_WINDOW_TITLE,
)


class SettingsMixin:
    def _open_settings(self) -> None:
        if self._settings_open:
            return
        self._settings_open = True
        g = globals()
        original = {
            "notes_directory": self.config.notes_directory,
            "hotkey": self.config.hotkey,
            "width": self.config.width,
            "explorer_width": self.config.explorer_width,
            "nav_width": self.config.nav_width,
            "nav_bar_anchor": self.config.nav_bar_anchor,
            "alpha": self.config.alpha,
            "auto_save": self.config.auto_save,
            "remember_last_note": self.config.remember_last_note,
            "explorer_open": self.config.explorer_open,
            "app_position": self.config.app_position,
            "theme": self.config.theme,
            "start_on_boot": self.config.start_on_boot,
            "font_family": self.config.font_family,
            "font_size": self.config.font_size,
            "attachments_folder": self.config.attachments_folder,
            "language": self.config.language,
            "command_shortcuts": dict(self.config.command_shortcuts),
            "plugin_shortcuts": dict(getattr(self.config, "plugin_shortcuts", {})),
            "sticky_notes_double_ctrl": bool(getattr(self.config, "sticky_notes_double_ctrl", True)),
            "enabled_plugins": list(self.config.enabled_plugins),
            "disabled_plugins": list(self.config.disabled_plugins),
            "removed_plugins": list(self.config.removed_plugins),
        }

        win = tk.Toplevel(self.root)
        # Keep the native window hidden until all controls have been laid out.
        # Mapping a half-built Toplevel exposes several intermediate frames on
        # Windows and looks like a delayed/dragging title area.
        win.withdraw()
        win.title(t("settings.window_title", app=APP_NAME))
        work_width = max(320, self.work_right - self.work_left)
        work_height = max(320, self.work_bottom - self.work_top)
        settings_w = min(760, max(320, work_width - 48))
        settings_h = min(680, max(320, work_height - 72))
        settings_x = self.work_left + max(0, (work_width - settings_w) // 2)
        settings_y = self.work_top + max(0, (work_height - settings_h) // 2)
        win.geometry(f"{settings_w}x{settings_h}+{settings_x}+{settings_y}")
        win.minsize(min(420, settings_w), min(320, settings_h))
        win.configure(bg=g["BG"])
        win.transient(self.root)
        win.resizable(True, True)

        content_shell = tk.Frame(win, bg=g["BG"])
        content_shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(content_shell, bg=g["BG"], highlightthickness=0, borderwidth=0)
        scroll_track = tk.Frame(content_shell, bg=g["BG"], width=12, cursor="sb_v_double_arrow")
        scroll_thumb = tk.Frame(scroll_track, bg=g["BORDER"], width=5, cursor="sb_v_double_arrow")
        h_scroll_track = tk.Frame(content_shell, bg=g["BG"], height=12, cursor="sb_h_double_arrow")
        h_scroll_thumb = tk.Frame(h_scroll_track, bg=g["BORDER"], height=5, cursor="sb_h_double_arrow")
        content = tk.Frame(canvas, bg=g["BG"])
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        content_shell.grid_rowconfigure(0, weight=1)
        content_shell.grid_columnconfigure(0, weight=1)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll_track.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=10)
        h_scroll_track.grid(row=1, column=0, sticky="ew", padx=(10, 0), pady=(0, 5))
        scroll_track.pack_propagate(False)
        h_scroll_track.pack_propagate(False)

        def update_scroll_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                scroll_thumb.place_forget()
                return
            scroll_thumb.place(relx=0.5, rely=start, relheight=max(0.08, end - start), width=5, anchor="n")

        def update_h_scroll_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                h_scroll_thumb.place_forget()
                return
            h_scroll_thumb.place(relx=start, rely=0.5, relwidth=max(0.08, end - start), height=5, anchor="w")

        def scroll_to_pointer(event) -> None:
            height = max(1, scroll_track.winfo_height())
            canvas.yview_moveto(max(0.0, min(1.0, event.y / height)))

        def h_scroll_to_pointer(event) -> None:
            width = max(1, h_scroll_track.winfo_width())
            canvas.xview_moveto(max(0.0, min(1.0, event.x / width)))

        drag_state = {"y": 0, "first": 0.0}
        h_drag_state = {"x": 0, "first": 0.0}

        def start_thumb_drag(event) -> None:
            first, _last = canvas.yview()
            drag_state["y"] = event.y_root
            drag_state["first"] = first
            scroll_thumb.config(bg=globals()["ACCENT"])

        def start_h_thumb_drag(event) -> None:
            first, _last = canvas.xview()
            h_drag_state["x"] = event.x_root
            h_drag_state["first"] = first
            h_scroll_thumb.config(bg=globals()["ACCENT"])

        def drag_thumb(event) -> None:
            height = max(1, scroll_track.winfo_height())
            delta = (event.y_root - drag_state["y"]) / height
            canvas.yview_moveto(max(0.0, min(1.0, drag_state["first"] + delta)))

        def drag_h_thumb(event) -> None:
            width = max(1, h_scroll_track.winfo_width())
            delta = (event.x_root - h_drag_state["x"]) / width
            canvas.xview_moveto(max(0.0, min(1.0, h_drag_state["first"] + delta)))

        def end_thumb_drag(_event) -> None:
            scroll_thumb.config(bg=globals()["BORDER"])

        def end_h_thumb_drag(_event) -> None:
            h_scroll_thumb.config(bg=globals()["BORDER"])

        canvas.configure(yscrollcommand=update_scroll_thumb, xscrollcommand=update_h_scroll_thumb)
        scroll_track.bind("<Button-1>", scroll_to_pointer)
        scroll_thumb.bind("<ButtonPress-1>", start_thumb_drag)
        scroll_thumb.bind("<B1-Motion>", drag_thumb)
        scroll_thumb.bind("<ButtonRelease-1>", end_thumb_drag)
        scroll_thumb.bind("<Enter>", lambda _e: scroll_thumb.config(bg=globals()["ACCENT_2"]))
        scroll_thumb.bind("<Leave>", lambda _e: scroll_thumb.config(bg=globals()["BORDER"]))
        h_scroll_track.bind("<Button-1>", h_scroll_to_pointer)
        h_scroll_thumb.bind("<ButtonPress-1>", start_h_thumb_drag)
        h_scroll_thumb.bind("<B1-Motion>", drag_h_thumb)
        h_scroll_thumb.bind("<ButtonRelease-1>", end_h_thumb_drag)
        h_scroll_thumb.bind("<Enter>", lambda _e: h_scroll_thumb.config(bg=globals()["ACCENT_2"]))
        h_scroll_thumb.bind("<Leave>", lambda _e: h_scroll_thumb.config(bg=globals()["BORDER"]))

        def update_scroll_region(_event=None) -> None:
            canvas.itemconfigure(content_window, width=max(canvas.winfo_width(), content.winfo_reqwidth()))
            canvas.configure(scrollregion=canvas.bbox("all"))
            first, last = canvas.yview()
            update_scroll_thumb(str(first), str(last))
            h_first, h_last = canvas.xview()
            update_h_scroll_thumb(str(h_first), str(h_last))

        def wheel(event):
            if win.winfo_exists():
                try:
                    widget_class = event.widget.winfo_class()
                except tk.TclError:
                    widget_class = ""
                try:
                    focus_class = win.focus_get().winfo_class() if win.focus_get() else ""
                except tk.TclError:
                    focus_class = ""
                if widget_class in {"TCombobox", "Combobox", "Spinbox", "TSpinbox", "Listbox"} or focus_class in {
                    "TCombobox", "Combobox", "Spinbox", "TSpinbox",
                }:
                    return "break"
                if event.state & 0x0001:
                    canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
                else:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return None

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_scroll_region)
        canvas.bind_all("<MouseWheel>", wheel)

        footer = tk.Frame(win, bg=g["BG"])
        footer.pack(fill="x", side="bottom")
        msg = tk.Label(footer, text=t("settings.footer_hint"), bg=g["BG"], fg=g["MUTED"], font=FONT_UI, anchor="w")
        msg.pack(fill="x", padx=22, pady=(8, 12))
        win.bind(
            "<Configure>",
            lambda _event: msg.configure(wraplength=max(220, win.winfo_width() - 44)),
            add="+",
        )

        def row(
            parent: tk.Widget,
            label: str,
            value: str,
            browse: Callable[[], str] | None = None,
            after_browse: Callable[[], None] | None = None,
            action_text: str | None = None,
            action: Callable[[], None] | None = None,
        ) -> tk.Entry:
            _g = globals()
            frame = tk.Frame(parent, bg=_g["BG"])
            frame.pack(fill="x", padx=18, pady=6)
            label_widget = tk.Label(
                frame,
                text=label,
                bg=_g["BG"],
                fg=_g["TEXT"],
                font=FONT_CONTROL,
                width=16,
                anchor="w",
            )
            input_frame = tk.Frame(frame, bg=_g["BG"])
            entry = tk.Entry(
                input_frame,
                bg=_g["SURFACE"],
                fg=_g["TEXT"],
                insertbackground=_g["TEXT"],
                relief="flat",
                font=FONT_CONTROL,
            )
            entry.insert(0, value)
            entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(4, 6))
            setattr(entry, "_label_widget", label_widget)
            if browse:
                browse_button = tk.Button(
                    input_frame,
                    text=t("settings.browse"),
                    command=lambda: self._browse_into(entry, browse, after_browse),
                    bg=_g["BORDER"],
                    fg=_g["TEXT"],
                    relief="flat",
                )
                browse_button.pack(side="right")
                setattr(entry, "_browse_button", browse_button)
            if action_text and action:
                action_button = tk.Button(input_frame, text=action_text, command=action, bg=_g["BORDER"], fg=_g["TEXT"], relief="flat")
                action_button.pack(side="right")
                setattr(entry, "_action_button", action_button)

            row_layout_state = {"compact": None}

            def layout_row(_event=None) -> None:
                compact = frame.winfo_width() < 430
                if row_layout_state["compact"] == compact:
                    return
                row_layout_state["compact"] = compact
                label_widget.pack_forget()
                input_frame.pack_forget()
                if compact:
                    label_widget.configure(width=0)
                    label_widget.pack(fill="x", anchor="w", pady=(0, 3))
                    input_frame.pack(fill="x")
                else:
                    label_widget.configure(width=16)
                    label_widget.pack(side="left")
                    input_frame.pack(side="left", fill="x", expand=True)

            frame.bind("<Configure>", layout_row)
            frame.after_idle(layout_row)
            return entry

        def add_dual_choice_row(
            parent: tk.Widget,
            label_text: str,
            option_keys: tuple[object, ...],
            option_labels: dict[object, str],
            on_select: Callable[[object], None],
        ) -> tuple[tk.Label, dict[object, tk.Label], tk.Frame]:
            _g = globals()
            frame = tk.Frame(parent, bg=_g["BG"])
            frame.pack(fill="x", padx=18, pady=6)
            label = tk.Label(
                frame,
                text=label_text,
                bg=_g["BG"],
                fg=_g["TEXT"],
                font=FONT_CONTROL,
                width=16,
                anchor="w",
                justify="left",
            )
            choices = tk.Frame(frame, bg=_g["SURFACE"])
            choices.grid_columnconfigure(0, weight=1, uniform="choice_col")
            choices.grid_columnconfigure(1, weight=1, uniform="choice_col")
            buttons: dict[object, tk.Label] = {}
            layout_state = {"compact": None}

            def layout_row(_event=None) -> None:
                compact = frame.winfo_width() < 430
                if layout_state["compact"] == compact:
                    if compact:
                        label.configure(wraplength=max(220, frame.winfo_width() - 36))
                    return
                layout_state["compact"] = compact
                label.grid_forget()
                choices.grid_forget()
                if compact:
                    frame.grid_columnconfigure(0, weight=1)
                    frame.grid_columnconfigure(1, weight=0)
                    label.configure(width=0, wraplength=max(220, frame.winfo_width() - 36))
                    label.grid(row=0, column=0, sticky="w", pady=(0, 4))
                    choices.grid(row=1, column=0, sticky="ew")
                else:
                    frame.grid_columnconfigure(0, weight=0)
                    frame.grid_columnconfigure(1, weight=1)
                    label.configure(width=16, wraplength=0)
                    label.grid(row=0, column=0, sticky="nw", pady=2)
                    choices.grid(row=0, column=1, sticky="ew", padx=(4, 6))

            for column, key in enumerate(option_keys):
                button = tk.Label(
                    choices,
                    text=option_labels[key],
                    bg=_g["SURFACE"],
                    fg=_g["TEXT_SOFT"],
                    font=FONT_CONTROL,
                    cursor="hand2",
                    pady=6,
                    padx=8,
                    anchor="center",
                    highlightthickness=1,
                    highlightbackground=_g["BORDER"],
                )
                padx = (0, 4) if column == 0 else (4, 0)
                button.grid(row=0, column=column, sticky="nsew", padx=padx)
                button.bind("<Button-1>", lambda _event, value=key: on_select(value))
                buttons[key] = button

            frame.bind("<Configure>", layout_row)
            frame.after_idle(layout_row)
            return label, buttons, choices

        def style_dual_choice_button(button: tk.Label, selected: bool) -> None:
            _g = globals()
            button.config(
                bg=_g["SIDEBAR_HOVER"] if selected else _g["SURFACE"],
                fg=_g["TEXT"] if selected else _g["TEXT_SOFT"],
                font=FONT_CONTROL,
                highlightbackground=_g["ACCENT_2"] if selected else _g["BORDER"],
                highlightcolor=_g["ACCENT_2"] if selected else _g["BORDER"],
                highlightthickness=2 if selected else 1,
            )

        settings_title_label = tk.Label(content, text=t("settings.title"), bg=g["BG"], fg=g["TEXT"], font=FONT_WINDOW_TITLE)
        settings_title_label.pack(pady=(18, 10))
        settings_body = tk.Frame(content, bg=g["BG"])
        settings_body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        settings_nav = tk.Frame(
            settings_body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=4,
            pady=4,
        )
        settings_nav.pack(fill="x", padx=4, pady=(0, 12))
        settings_pages = tk.Frame(settings_body, bg=g["BG"])
        settings_pages.pack(fill="both", expand=True)
        pages = {
            "general": tk.Frame(settings_pages, bg=g["BG"]),
            "appearance": tk.Frame(settings_pages, bg=g["BG"]),
            "layout": tk.Frame(settings_pages, bg=g["BG"]),
            "shortcuts": tk.Frame(settings_pages, bg=g["BG"]),
            "plugins": tk.Frame(settings_pages, bg=g["BG"]),
        }
        page_buttons: dict[str, tk.Label] = {}
        active_page = tk.StringVar(value="general")
        page_finalize: dict[str, Callable[[], None]] = {}

        def _settings_win_handle() -> int | None:
            try:
                return self._window_handle(win)
            except (AttributeError, tk.TclError, ValueError):
                return None

        def _with_settings_redraw_suspended(action: Callable[[], None]) -> None:
            handle = _settings_win_handle()
            if handle is not None:
                set_window_redraw(handle, False)
            try:
                action()
            finally:
                if handle is not None:
                    win.update_idletasks()
                    set_window_redraw(handle, True)
                    redraw_window(handle)

        def refresh_page_nav() -> None:
            _g = globals()
            settings_nav.configure(bg=_g["SURFACE"], highlightbackground=_g["BORDER"])
            for key, button in page_buttons.items():
                selected = active_page.get() == key
                button.configure(
                    bg=_g["SURFACE_2"] if selected else _g["SURFACE"],
                    fg=_g["TEXT"] if selected else _g["TEXT_SOFT"],
                    font=FONT_CONTROL,
                    highlightbackground=_g["ACCENT"] if selected else _g["SURFACE"],
                    highlightcolor=_g["ACCENT"] if selected else _g["SURFACE"],
                )

        def show_settings_page(name: str) -> None:
            if name not in pages:
                return

            def switch_page() -> None:
                active_page.set(name)
                for page in pages.values():
                    page.pack_forget()
                pages[name].pack(fill="both", expand=True)
                refresh_page_nav()
                canvas.yview_moveto(0)
                win.update_idletasks()
                finalize = page_finalize.get(name)
                if finalize is not None:
                    finalize()
                update_scroll_region()

            _with_settings_redraw_suspended(switch_page)

        for key, label_text in (
            ("general", t("settings.page.general")),
            ("appearance", t("settings.page.appearance")),
            ("layout", t("settings.page.layout")),
            ("shortcuts", t("settings.page.shortcuts")),
            ("plugins", t("settings.page.plugins")),
        ):
            _g = globals()
            button = tk.Label(
                settings_nav,
                text=label_text,
                bg=_g["SURFACE"],
                fg=_g["TEXT_SOFT"],
                font=FONT_CONTROL,
                anchor="center",
                padx=14,
                pady=7,
                cursor="hand2",
                highlightthickness=1,
                highlightbackground=_g["SURFACE"],
            )
            button.pack(side="left", fill="x", expand=True, padx=2)
            button.bind("<Button-1>", lambda _e, value=key: show_settings_page(value))
            page_buttons[key] = button

        general_page = pages["general"]
        appearance_page = pages["appearance"]
        layout_page = pages["layout"]
        shortcuts_page = pages["shortcuts"]
        plugins_page = pages["plugins"]
        shortcuts_hint_label = tk.Label(
            shortcuts_page,
            text=t("settings.shortcuts_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=FONT_UI,
            anchor="w",
        )
        shortcuts_hint_label.pack(fill="x", padx=18, pady=(2, 8))
        plugins_hint_label = tk.Label(
            plugins_page,
            text=t("settings.plugins_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=FONT_UI,
            anchor="w",
            justify="left",
            wraplength=520,
        )
        plugins_hint_label.pack(fill="x", padx=18, pady=(2, 10))
        show_settings_page("general")

        def dropdown_control(
            parent: tk.Widget,
            variable: tk.StringVar,
            values: list[str],
            on_select: Callable[[], None],
            *,
            max_rows: int = 8,
            preview_font: bool = False,
        ) -> dict[str, Callable]:
            state = {
                "open": False,
                "values": list(values),
                "win_click_bind": None,
                "root_click_bind": None,
            }
            shell = tk.Frame(parent, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"])
            shell.pack(fill="x")
            button = tk.Frame(shell, bg=g["SURFACE"], cursor="hand2", padx=10, pady=7)
            button.pack(fill="x")
            value_label = tk.Label(
                button,
                text=variable.get(),
                bg=g["SURFACE"],
                fg=g["TEXT"],
                font=FONT_CONTROL,
                anchor="w",
                cursor="hand2",
            )
            value_label.pack(side="left", fill="x", expand=True)
            arrow_canvas = tk.Canvas(
                button,
                bg=g["SURFACE"],
                width=24,
                height=20,
                highlightthickness=0,
                borderwidth=0,
                cursor="hand2",
            )
            arrow_canvas.pack(side="right")

            def draw_arrow(opened: bool = False) -> None:
                arrow_canvas.delete("all")
                color = g["ACCENT"] if opened else g["TEXT_SOFT"]
                if opened:
                    points = (7, 12, 12, 7, 17, 12)
                else:
                    points = (7, 8, 12, 13, 17, 8)
                arrow_canvas.create_line(*points, fill=color, width=2, capstyle=tk.ROUND, joinstyle=tk.ROUND)

            draw_arrow(False)
            def refresh_display() -> None:
                value = variable.get()
                value_label.configure(text=value)
                if preview_font:
                    try:
                        value_label.configure(font=(value or "Segoe UI", 10))
                    except tk.TclError:
                        value_label.configure(font=FONT_CONTROL)

            def close_dropdown() -> None:
                if not state["open"]:
                    return
                state["open"] = False
                for widget, key in ((win, "win_click_bind"), (self.root, "root_click_bind")):
                    bind_id = state.get(key)
                    if bind_id:
                        try:
                            widget.unbind("<ButtonPress-1>", str(bind_id))
                        except tk.TclError:
                            pass
                        state[key] = None
                popup = state.get("popup")
                state["popup"] = None
                state["listbox"] = None
                if popup is not None:
                    try:
                        popup.destroy()
                    except tk.TclError:
                        pass
                draw_arrow(False)

            def open_dropdown() -> None:
                if state["open"]:
                    close_dropdown()
                    return
                values_now = list(state["values"])
                rows = max(1, min(max_rows, len(values_now)))
                popup = tk.Frame(win, bg=g["BORDER"], highlightthickness=0)
                width = max(180, shell.winfo_width())
                row_height = 25
                height = rows * row_height + 2
                x = shell.winfo_rootx() - win.winfo_rootx()
                y = shell.winfo_rooty() - win.winfo_rooty() + shell.winfo_height() + 2
                popup.place(x=x, y=y, width=width, height=height)
                panel = tk.Frame(popup, bg=g["SURFACE_2"], highlightthickness=1, highlightbackground=g["BORDER"])
                panel.pack(fill="both", expand=True)
                list_wrap = tk.Frame(panel, bg=g["SURFACE_2"])
                list_wrap.pack(side="left", fill="both", expand=True)
                listbox = tk.Listbox(
                    list_wrap,
                    bg=g["SURFACE_2"],
                    fg=g["TEXT"],
                    selectbackground=g["ACCENT"],
                    selectforeground=self._contrast_text(g["ACCENT"]),
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=0,
                    activestyle="none",
                    exportselection=False,
                    font=FONT_CONTROL,
                    height=rows,
                )
                scroll_canvas = tk.Canvas(
                    panel,
                    bg=g["SURFACE_2"],
                    width=12,
                    highlightthickness=0,
                    borderwidth=0,
                    cursor="sb_v_double_arrow",
                )
                scroll_thumb = {"id": None, "drag_y": 0, "first": 0.0}

                def update_scrollbar(first: str, last: str) -> None:
                    if len(values_now) <= rows:
                        scroll_canvas.pack_forget()
                        return
                    scroll_canvas.pack(side="right", fill="y")
                    scroll_canvas.delete("all")
                    height_now = max(1, scroll_canvas.winfo_height())
                    start = float(first)
                    end = float(last)
                    y1 = max(3, int(start * height_now))
                    y2 = min(height_now - 3, max(y1 + 18, int(end * height_now)))
                    scroll_canvas.create_line(
                        6,
                        4,
                        6,
                        height_now - 4,
                        fill=g["BORDER"],
                        width=4,
                        capstyle=tk.ROUND,
                    )
                    scroll_thumb["id"] = scroll_canvas.create_line(
                        6,
                        y1,
                        6,
                        y2,
                        fill=g["ACCENT"],
                        width=5,
                        capstyle=tk.ROUND,
                    )

                def scrollbar_to_pointer(event) -> str:
                    if len(values_now) <= rows:
                        return "break"
                    height_now = max(1, scroll_canvas.winfo_height())
                    listbox.yview_moveto(max(0.0, min(1.0, event.y / height_now)))
                    return "break"

                def start_scroll_drag(event) -> str:
                    first, _last = listbox.yview()
                    scroll_thumb["drag_y"] = event.y_root
                    scroll_thumb["first"] = first
                    return "break"

                def drag_scroll_thumb(event) -> str:
                    height_now = max(1, scroll_canvas.winfo_height())
                    delta = (event.y_root - scroll_thumb["drag_y"]) / height_now
                    listbox.yview_moveto(max(0.0, min(1.0, scroll_thumb["first"] + delta)))
                    return "break"

                listbox.configure(yscrollcommand=update_scrollbar)
                listbox.pack(fill="both", expand=True)
                scroll_canvas.bind("<Button-1>", scrollbar_to_pointer)
                scroll_canvas.bind("<ButtonPress-1>", start_scroll_drag, add="+")
                scroll_canvas.bind("<B1-Motion>", drag_scroll_thumb)
                listbox.delete(0, tk.END)
                for item in values_now:
                    listbox.insert(tk.END, item)
                if variable.get() in values_now:
                    index = values_now.index(variable.get())
                    listbox.selection_set(index)
                    listbox.see(index)
                state["open"] = True
                state["popup"] = popup
                state["listbox"] = listbox
                draw_arrow(True)
                listbox.bind("<ButtonRelease-1>", choose_event)
                listbox.bind("<Return>", lambda _event: choose_index(listbox.curselection()[0]) if listbox.curselection() else "break")
                listbox.bind("<Escape>", lambda _event: close_dropdown() or "break")
                listbox.bind("<MouseWheel>", scroll_list)
                popup.bind("<Escape>", lambda _event: close_dropdown() or "break")
                popup.lift()
                popup.after_idle(lambda: (update_scrollbar(*listbox.yview()), listbox.focus_set()))
                popup.after_idle(bind_outside_click)

            def widget_contains_pointer(widget: tk.Widget | None, event) -> bool:
                if widget is None:
                    return False
                try:
                    x = event.x_root
                    y = event.y_root
                    left = widget.winfo_rootx()
                    top = widget.winfo_rooty()
                    return left <= x < left + widget.winfo_width() and top <= y < top + widget.winfo_height()
                except tk.TclError:
                    return False

            def close_if_outside(event) -> None:
                if not state["open"]:
                    return
                popup = state.get("popup")
                if widget_contains_pointer(shell, event) or widget_contains_pointer(popup, event):
                    return
                close_dropdown()

            def bind_outside_click() -> None:
                if not state["open"]:
                    return
                if state.get("win_click_bind") is None:
                    state["win_click_bind"] = win.bind("<ButtonPress-1>", close_if_outside, add="+")
                if state.get("root_click_bind") is None:
                    state["root_click_bind"] = self.root.bind("<ButtonPress-1>", close_if_outside, add="+")

            def choose_index(index: int) -> str:
                values_now = list(state["values"])
                if 0 <= index < len(values_now):
                    variable.set(values_now[index])
                    refresh_display()
                    close_dropdown()
                    on_select()
                return "break"

            def choose_event(event) -> str:
                listbox = state.get("listbox")
                if not isinstance(listbox, tk.Listbox):
                    return "break"
                return choose_index(listbox.nearest(event.y))

            def scroll_list(event) -> str:
                listbox = state.get("listbox")
                if not isinstance(listbox, tk.Listbox):
                    return "break"
                listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
                return "break"

            def set_values(new_values: list[str]) -> None:
                state["values"] = list(new_values)
                refresh_display()
                if state["open"]:
                    close_dropdown()

            for target in (button, value_label, arrow_canvas):
                target.bind("<Button-1>", lambda _event: open_dropdown() or "break")
            refresh_display()
            return {"set_values": set_values, "refresh": refresh_display, "close": close_dropdown}

        language_labels = {code: t(f"lang.{code}") for code in SUPPORTED_LANGUAGES}
        label_to_code = {label: code for code, label in language_labels.items()}
        language_frame = tk.Frame(general_page, bg=g["BG"])
        language_frame.pack(fill="x", padx=18, pady=(6, 10))
        language_label = tk.Label(
            language_frame,
            text=t("settings.language"),
            bg=g["BG"],
            fg=g["TEXT"],
            font=FONT_CONTROL,
            anchor="w",
        )
        language_label.pack(fill="x", pady=(0, 6))
        language_var = tk.StringVar(value=language_labels.get(self.config.language, language_labels["en"]))
        language_dropdown = dropdown_control(
            language_frame,
            language_var,
            [language_labels[code] for code in SUPPORTED_LANGUAGES],
            lambda: preview_language(),
            max_rows=6,
        )

        def refresh_language_options(selected_code: str | None = None) -> None:
            nonlocal language_labels, label_to_code
            selected_code = selected_code or label_to_code.get(language_var.get(), self.config.language)
            language_labels = {code: t(f"lang.{code}") for code in SUPPORTED_LANGUAGES}
            label_to_code = {label: code for code, label in language_labels.items()}
            language_var.set(language_labels.get(selected_code, language_labels["en"]))
            language_dropdown["set_values"]([language_labels[code] for code in SUPPORTED_LANGUAGES])
            language_dropdown["refresh"]()

        def preview_language(_event=None) -> None:
            selected = language_var.get()
            code = label_to_code.get(selected, normalize_language(selected))
            self.config.language = code
            set_language(code)
            self._apply_language()
            refresh_language_options(code)
            refresh_settings_language()
            msg.config(text=t("settings.msg.language_changed"), fg=globals()["TEXT"])

        shortcut_entries: dict[str, tk.Entry] = {}
        shortcut_record_buttons: dict[str, tk.Button] = {}
        shortcut_recording = False
        current_shortcuts = normalize_command_shortcuts(self.config.command_shortcuts)

        def record_command_shortcut(command_id: str) -> None:
            nonlocal shortcut_recording
            if shortcut_recording:
                return
            shortcut_recording = True
            self._unregister_hotkey()
            for key, button in shortcut_record_buttons.items():
                button.configure(
                    text=t("settings.recording") if key == command_id else t("settings.record"),
                    state="disabled",
                )
            label = command_label(command_id)
            msg.config(text=t("settings.msg.press_shortcut", label=label), fg=globals()["TEXT"])

            def worker() -> None:
                try:
                    recorded = normalize_hotkey(read_hotkey_clean(suppress=False))
                    if not validate_hotkey(recorded):
                        raise ValueError(recorded)
                except Exception:
                    self.root.after(0, finish_recording, None)
                else:
                    self.root.after(0, finish_recording, recorded)

            def finish_recording(recorded: str | None) -> None:
                nonlocal shortcut_recording
                shortcut_recording = False
                for button in shortcut_record_buttons.values():
                    button.configure(text=t("settings.record"), state="normal")
                if recorded:
                    set_entry(shortcut_entries[command_id], format_hotkey_display(recorded))
                    msg.config(
                        text=t("settings.msg.shortcut_recorded", label=label, hotkey=format_hotkey_display(recorded)),
                        fg=globals()["TEXT"],
                    )
                else:
                    msg.config(text=t("settings.msg.shortcut_failed", label=label), fg=globals()["DANGER"])
                self._register_hotkey()

            threading.Thread(target=worker, daemon=True).start()

        for command_id, (_label, _default) in COMMAND_SHORTCUTS.items():
            shortcut_row = tk.Frame(shortcuts_page, bg=g["BG"])
            shortcut_row.pack(fill="x", padx=18, pady=4)
            shortcut_label = tk.Label(
                shortcut_row,
                text=command_label(command_id),
                bg=g["BG"],
                fg=g["TEXT"],
                font=FONT_CONTROL,
                width=25,
                anchor="w",
            )
            shortcut_label.pack(side="left")
            shortcut_entry = tk.Entry(
                shortcut_row,
                bg=g["SURFACE"],
                fg=g["TEXT"],
                insertbackground=g["TEXT"],
                relief="flat",
                font=FONT_CONTROL,
            )
            shortcut_entry.insert(0, format_hotkey_display(current_shortcuts.get(command_id, "")))
            shortcut_entry.pack(side="left", fill="x", expand=True, ipady=4)
            record_button = tk.Button(
                shortcut_row,
                text=t("settings.record"),
                command=lambda value=command_id: record_command_shortcut(value),
                bg=g["BORDER"],
                fg=g["TEXT"],
                activebackground=g["ACCENT"],
                activeforeground=self._contrast_text(g["ACCENT"]),
                relief="flat",
                padx=8,
                pady=3,
                cursor="hand2",
            )
            record_button.pack(side="right", padx=(6, 0))
            shortcut_entries[command_id] = shortcut_entry
            shortcut_record_buttons[command_id] = record_button
            setattr(shortcut_entry, "_label_widget", shortcut_label)

        def reset_shortcuts() -> None:
            for command_id, entry in shortcut_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, format_hotkey_display(DEFAULT_COMMAND_SHORTCUTS[command_id]))
            msg.config(text=t("settings.msg.shortcuts_restored"), fg=globals()["TEXT"])

        restore_shortcuts_button = tk.Button(
            shortcuts_page,
            text=t("settings.restore_defaults"),
            command=reset_shortcuts,
            bg=g["BORDER"],
            fg=g["TEXT"],
            activebackground=g["ACCENT"],
            activeforeground=self._contrast_text(g["ACCENT"]),
            relief="flat",
            padx=12,
            pady=6,
        )
        restore_shortcuts_button.pack(anchor="e", padx=18, pady=(8, 4))

        plugin_rows: list[dict[str, object]] = []
        plugin_shortcut_entries: dict[str, tk.Label] = {}
        plugin_shortcut_record_buttons: dict[str, tk.Button] = {}
        plugin_shortcut_recording = False
        current_plugin_shortcuts = normalize_plugin_shortcuts(getattr(self.config, "plugin_shortcuts", {}) or {})
        sticky_plugin_double_ctrl = bool(getattr(self.config, "sticky_notes_double_ctrl", True))
        plugins_list = tk.Frame(plugins_page, bg=g["BG"])
        plugins_list.pack(fill="x", padx=18, pady=(0, 8))

        def plugin_shortcut_display(plugin_id: str) -> str:
            shortcut = current_plugin_shortcuts.get(plugin_id, "")
            if plugin_id == "sticky_notes" and sticky_plugin_double_ctrl:
                return t("settings.plugins.double_ctrl")
            return format_hotkey_display(shortcut)

        def set_plugin_shortcut_display(plugin_id: str) -> None:
            label_widget = plugin_shortcut_entries.get(plugin_id)
            if label_widget is not None:
                label_widget.configure(text=plugin_shortcut_display(plugin_id) or t("settings.plugins.no_shortcut"))

        def record_plugin_shortcut(plugin_id: str) -> None:
            nonlocal plugin_shortcut_recording, sticky_plugin_double_ctrl
            if plugin_shortcut_recording:
                return
            plugin_shortcut_recording = True
            self._unregister_hotkey()
            self._unregister_sticky_notes_hotkey()
            self._unregister_plugin_shortcuts()
            for key, button in plugin_shortcut_record_buttons.items():
                button.configure(text=t("settings.recording") if key == plugin_id else t("settings.record"), state="disabled")
            plugin = next((item for item in BUILTIN_PLUGINS if item.id == plugin_id), None)
            label = t(plugin.name_key) if plugin is not None else plugin_id
            msg.config(text=t("settings.msg.press_shortcut", label=label), fg=globals()["TEXT"])

            def worker() -> None:
                try:
                    recorded = normalize_hotkey(read_hotkey_clean(suppress=False))
                    if not validate_hotkey(recorded):
                        raise ValueError(recorded)
                except Exception:
                    self.root.after(0, finish_recording, None)
                else:
                    self.root.after(0, finish_recording, recorded)

            def finish_recording(recorded: str | None) -> None:
                nonlocal plugin_shortcut_recording, sticky_plugin_double_ctrl
                plugin_shortcut_recording = False
                for key, button in plugin_shortcut_record_buttons.items():
                    state = tk.NORMAL if next((item for item in BUILTIN_PLUGINS if item.id == key and item.entrypoint), None) else tk.DISABLED
                    button.configure(text=t("settings.record"), state=state)
                if recorded:
                    if plugin_id == "sticky_notes" and normalize_hotkey(recorded) in {"ctrl", "control"}:
                        sticky_plugin_double_ctrl = True
                        current_plugin_shortcuts.pop(plugin_id, None)
                        set_plugin_shortcut_display(plugin_id)
                        msg.config(
                            text=t("settings.msg.shortcut_recorded", label=label, hotkey=t("settings.plugins.double_ctrl")),
                            fg=globals()["TEXT"],
                        )
                    elif is_modifier_only_hotkey(recorded):
                        msg.config(text=t("settings.msg.shortcut_failed", label=label), fg=globals()["DANGER"])
                    else:
                        current_plugin_shortcuts[plugin_id] = recorded
                        if plugin_id == "sticky_notes":
                            sticky_plugin_double_ctrl = False
                        set_plugin_shortcut_display(plugin_id)
                        msg.config(text=t("settings.msg.shortcut_recorded", label=label, hotkey=format_hotkey_display(recorded)), fg=globals()["TEXT"])
                else:
                    msg.config(text=t("settings.msg.shortcut_failed", label=label), fg=globals()["DANGER"])
                self._register_hotkey()
                self._register_sticky_notes_hotkey()
                self._register_plugin_shortcuts()
                refresh_plugin_rows()

            threading.Thread(target=worker, daemon=True).start()

        def refresh_plugin_rows() -> None:
            _g = globals()
            for row_state in plugin_rows:
                plugin = row_state["plugin"]
                state = plugin_status(self.config, plugin.id)
                frame = row_state["frame"]
                icon_label = row_state["icon"]
                title_label = row_state["title"]
                description_label = row_state["description"]
                status_label = row_state["status"]
                toggle_button = row_state["toggle"]
                remove_button = row_state["remove"]
                shortcut_entry = row_state["shortcut_entry"]
                shortcut_button = row_state["shortcut_button"]
                is_removed = state == "removed"
                frame.configure(
                    bg=_g["SURFACE"] if not is_removed else _g["BG"],
                    highlightbackground=_g["BORDER"],
                )
                icon_label.configure(bg=frame.cget("bg"), fg=_g["TEXT"] if not is_removed else _g["MUTED"])
                title_label.configure(text=t(plugin.name_key), bg=frame.cget("bg"), fg=_g["TEXT"] if not is_removed else _g["MUTED"])
                description_label.configure(text=t(plugin.description_key), bg=frame.cget("bg"), fg=_g["TEXT_SOFT"] if not is_removed else _g["MUTED"])
                shortcut_entry.configure(
                    bg=_g["SURFACE"] if not is_removed else _g["BG"],
                    fg=_g["TEXT"] if plugin.entrypoint and not is_removed else _g["MUTED"],
                )
                set_plugin_shortcut_display(plugin.id)
                status_label.configure(
                    text=t(f"settings.plugins.status.{state}"),
                    bg=frame.cget("bg"),
                    fg=_g["ACCENT_2"] if state == "enabled" else _g["MUTED"],
                )
                if state == "removed":
                    toggle_button.configure(text=t("settings.plugins.restore"), state=tk.NORMAL)
                    remove_button.configure(text=t("settings.plugins.remove"), state=tk.DISABLED)
                    shortcut_button.configure(text=t("settings.record"), state=tk.DISABLED)
                elif state == "disabled":
                    toggle_button.configure(text=t("settings.plugins.enable"), state=tk.NORMAL)
                    remove_button.configure(text=t("settings.plugins.remove"), state=tk.NORMAL)
                    shortcut_button.configure(text=t("settings.record"), state=tk.DISABLED)
                else:
                    toggle_button.configure(text=t("settings.plugins.disable"), state=tk.NORMAL)
                    remove_button.configure(text=t("settings.plugins.remove"), state=tk.NORMAL)
                    shortcut_button.configure(text=t("settings.record"), state=tk.DISABLED if not plugin.entrypoint else tk.NORMAL)
                for button in (toggle_button, remove_button, shortcut_button):
                    button.configure(
                        bg=_g["BORDER"],
                        fg=_g["TEXT"],
                        activebackground=_g["ACCENT"],
                        activeforeground=self._contrast_text(_g["ACCENT"]),
                    )

        def toggle_plugin(plugin_id: str) -> None:
            state = plugin_status(self.config, plugin_id)
            if state == "removed":
                restore_plugin(self.config, plugin_id)
                msg.config(text=t("settings.plugins.msg.restored"), fg=globals()["TEXT"])
            elif state == "disabled":
                enable_plugin(self.config, plugin_id)
                msg.config(text=t("settings.plugins.msg.enabled"), fg=globals()["TEXT"])
            else:
                disable_plugin(self.config, plugin_id)
                msg.config(text=t("settings.plugins.msg.disabled"), fg=globals()["TEXT"])
            self._register_sticky_notes_hotkey()
            self._register_plugin_shortcuts()
            refresh_plugin_rows()

        def delete_plugin(plugin_id: str) -> None:
            remove_plugin(self.config, plugin_id)
            msg.config(text=t("settings.plugins.msg.removed"), fg=globals()["TEXT"])
            self._register_sticky_notes_hotkey()
            self._register_plugin_shortcuts()
            refresh_plugin_rows()

        for plugin in BUILTIN_PLUGINS:
            plugin_frame = tk.Frame(
                plugins_list,
                bg=g["SURFACE"],
                highlightthickness=1,
                highlightbackground=g["BORDER"],
                padx=10,
                pady=8,
            )
            plugin_frame.pack(fill="x", pady=5)
            icon_label = tk.Label(plugin_frame, text=plugin.icon, bg=g["SURFACE"], fg=g["TEXT"], font=FONT_PLUGIN_ICON_SMALL, width=3)
            icon_label.pack(side="left", padx=(0, 8))
            text_frame = tk.Frame(plugin_frame, bg=g["SURFACE"])
            text_frame.pack(side="left", fill="x", expand=True)
            title_label = tk.Label(text_frame, text=t(plugin.name_key), bg=g["SURFACE"], fg=g["TEXT"], font=FONT_CARD_TITLE_STRONG, anchor="w")
            title_label.pack(fill="x")
            description_label = tk.Label(
                text_frame,
                text=t(plugin.description_key),
                bg=g["SURFACE"],
                fg=g["TEXT_SOFT"],
                font=FONT_UI_SMALL,
                anchor="w",
                justify="left",
                wraplength=320,
            )
            description_label.pack(fill="x", pady=(2, 0))
            status_label = tk.Label(plugin_frame, text="", bg=g["SURFACE"], fg=g["MUTED"], font=FONT_UI_SMALL, width=10)
            status_label.pack(side="left", padx=(8, 6))
            toggle_button = tk.Button(
                plugin_frame,
                text="",
                command=lambda value=plugin.id: toggle_plugin(value),
                bg=g["BORDER"],
                fg=g["TEXT"],
                relief="flat",
                padx=8,
                pady=3,
                cursor="hand2",
            )
            toggle_button.pack(side="left", padx=(0, 5))
            remove_button = tk.Button(
                plugin_frame,
                text="",
                command=lambda value=plugin.id: delete_plugin(value),
                bg=g["BORDER"],
                fg=g["TEXT"],
                relief="flat",
                padx=8,
                pady=3,
                cursor="hand2",
            )
            remove_button.pack(side="left")
            shortcut_entry = tk.Label(
                plugin_frame,
                text=plugin_shortcut_display(plugin.id) or t("settings.plugins.no_shortcut"),
                bg=g["SURFACE"],
                fg=g["TEXT"],
                font=FONT_UI,
                width=14,
                anchor="w",
            )
            shortcut_entry.pack(side="left", padx=(8, 6))
            shortcut_button = tk.Button(
                plugin_frame,
                text=t("settings.record"),
                command=lambda value=plugin.id: record_plugin_shortcut(value),
                bg=g["BORDER"],
                fg=g["TEXT"],
                relief="flat",
                padx=8,
                pady=3,
                cursor="hand2",
            )
            shortcut_button.pack(side="left")
            plugin_shortcut_entries[plugin.id] = shortcut_entry
            plugin_shortcut_record_buttons[plugin.id] = shortcut_button
            plugin_rows.append(
                {
                    "plugin": plugin,
                    "frame": plugin_frame,
                    "icon": icon_label,
                    "title": title_label,
                    "description": description_label,
                    "status": status_label,
                    "toggle": toggle_button,
                    "remove": remove_button,
                    "shortcut_entry": shortcut_entry,
                    "shortcut_button": shortcut_button,
                }
            )
        e_notes = row(general_page, t("settings.notes_folder"), self.config.notes_directory, lambda: filedialog.askdirectory(parent=win), lambda: apply_workspace_only())

        def browse_attachments_folder() -> None:
            root = Path(e_notes.get().strip() or self.config.notes_directory).expanduser().resolve()
            selected = filedialog.askdirectory(
                parent=win,
                title=t("settings.attachments_browse_title"),
                initialdir=str(root),
            )
            if not selected:
                return
            try:
                relative = Path(selected).resolve().relative_to(root)
            except ValueError:
                msg.config(text=t("settings.msg.attachments_inside"), fg=globals()["DANGER"])
                return
            if relative == Path("."):
                msg.config(text=t("settings.msg.attachments_subfolder"), fg=globals()["DANGER"])
                return
            e_attachments.delete(0, tk.END)
            e_attachments.insert(0, relative.as_posix())
            msg.config(text=t("settings.msg.attachments_preview", path=relative.as_posix()), fg=globals()["TEXT"])

        e_attachments = row(
            general_page,
            t("settings.attachments_folder"),
            self.config.attachments_folder,
            action_text=t("settings.browse"),
            action=browse_attachments_folder,
        )
        backups_label = tk.Label(
            general_page,
            text=t("settings.backups", path=BACKUP_DIR),
            bg=g["BG"],
            fg=g["MUTED"],
            font=FONT_UI_SMALL,
            anchor="w",
            wraplength=390,
            justify="left",
        )
        backups_label.pack(fill="x", padx=22, pady=(0, 6))
        record_btn_ref: list[tk.Button] = []
        hotkey_recording = False
        e_hotkey: tk.Entry

        def set_entry(entry: tk.Entry, value: str) -> None:
            state = str(entry.cget("state"))
            if state == "disabled":
                entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, value)
            if state == "disabled":
                entry.configure(state="disabled")

        refresh_plugin_rows()

        def apply_workspace_only() -> bool:
            old_notes_dir = self.config.notes_directory
            notes_dir = e_notes.get().strip() or AppConfig().notes_directory
            workspace_changed = Path(notes_dir).expanduser().resolve() != Path(old_notes_dir).expanduser().resolve()
            if workspace_changed:
                self._switch_workspace(notes_dir)
            else:
                self.config.notes_directory = notes_dir
                self._refresh_explorer()
            if e_notes.get().strip() != self.config.notes_directory:
                set_entry(e_notes, self.config.notes_directory)
            msg.config(text=t("settings.msg.files_preview", path=self.config.notes_directory), fg=globals()["TEXT"])
            return workspace_changed

        live_workspace_after: str | None = None

        def schedule_live_workspace() -> None:
            nonlocal live_workspace_after
            if live_workspace_after is not None:
                try:
                    win.after_cancel(live_workspace_after)
                except tk.TclError:
                    pass
            live_workspace_after = win.after(450, apply_live_workspace)

        def apply_live_workspace() -> None:
            nonlocal live_workspace_after
            live_workspace_after = None
            raw = e_notes.get().strip()
            if not raw:
                return
            candidate = Path(raw).expanduser()
            if not candidate.exists() or not candidate.is_dir():
                return
            apply_workspace_only()

        e_notes.bind("<Return>", lambda _e: apply_workspace_only())
        e_notes.bind("<KeyRelease>", lambda _e: schedule_live_workspace())
        e_notes.bind("<FocusOut>", lambda _e: apply_live_workspace())

        def record_hotkey() -> None:
            nonlocal hotkey_recording
            if hotkey_recording:
                return
            hotkey_recording = True
            record_btn = record_btn_ref[0]
            record_btn.config(text=t("settings.recording"), state="disabled")
            msg.config(text=t("settings.msg.press_hotkey"), fg=globals()["TEXT"])
            self._unregister_hotkey()

            def worker() -> None:
                try:
                    normalized = normalize_hotkey(read_hotkey_clean(suppress=False))
                    if not validate_hotkey(normalized):
                        raise ValueError(normalized)
                except Exception:
                    self.root.after(0, finish_recording, None)
                else:
                    self.root.after(0, finish_recording, normalized)

            def finish_recording(recorded: str | None) -> None:
                nonlocal hotkey_recording
                hotkey_recording = False
                record_btn.config(text=t("settings.record"), state="normal")
                if recorded:
                    set_entry(e_hotkey, format_hotkey_display(recorded))
                    msg.config(text=t("settings.msg.hotkey_recorded", hotkey=format_hotkey_display(recorded)), fg=globals()["TEXT"])
                else:
                    msg.config(text=t("settings.msg.hotkey_failed"), fg=globals()["DANGER"])
                self._register_hotkey()

            threading.Thread(target=worker, daemon=True).start()

        e_hotkey = row(general_page, t("settings.hotkey"), format_hotkey_display(self.config.hotkey), action_text=t("settings.record"), action=record_hotkey)
        record_btn_ref.append(getattr(e_hotkey, "_action_button"))

        position_var = tk.StringVar(value=self.config.app_position)
        position_labels = {"left": t("position.left"), "right": t("position.right")}

        def select_position(value: str, preview: bool = True) -> None:
            if value not in {"left", "right"}:
                return
            position_var.set(value)
            for key, button in position_buttons.items():
                style_dual_choice_button(button, key == value)
            if not preview or value == self.config.app_position:
                return

            previous_position = self.config.app_position
            self.config.app_position = value
            self._apply_header_alignment()

            def finish_preview() -> None:
                self._update_width_resize_handles()
                if self.is_open and self.explorer_visible:
                    self.explorer.deiconify()
                    self.explorer.lift()
                    self.root.lift()
                win.lift()
                msg.config(
                    text=t("settings.msg.layout_preview", side=position_labels[value]),
                    fg=globals()["TEXT"],
                )

            if self.is_open:
                self._animate_side_switch(previous_position, callback=finish_preview)
            else:
                self._place_layout(False)
                finish_preview()

        position_label, position_buttons, _position_choices = add_dual_choice_row(
            layout_page,
            t("settings.app_position"),
            ("left", "right"),
            position_labels,
            lambda value: select_position(str(value)),
        )
        select_position(position_var.get(), preview=False)

        theme_frame = tk.Frame(appearance_page, bg=g["BG"])
        theme_frame.pack(fill="x", padx=18, pady=6)
        theme_label = tk.Label(
            theme_frame,
            text=t("settings.color_theme"),
            bg=g["BG"],
            fg=g["TEXT"],
            font=FONT_CONTROL,
            width=16,
            anchor="nw",
            pady=7,
        )
        theme_label.pack(side="left")
        theme_choices = tk.Frame(theme_frame, bg=g["BG"])
        theme_choices.pack(side="left", fill="x", expand=True, padx=(4, 6))
        theme_choices.grid_columnconfigure(0, weight=1, uniform="theme")
        theme_choices.grid_columnconfigure(1, weight=1, uniform="theme")
        theme_var = tk.StringVar(value=self.config.theme)
        theme_tiles: dict[str, tuple[tk.Frame, tk.Label, tk.Frame, tk.Frame]] = {}

        def refresh_theme_tiles() -> None:
            _g = globals()
            selected_name = theme_var.get()
            for theme_name, (tile, title, swatches, indicator) in theme_tiles.items():
                selected = theme_name == selected_name
                palette = theme_module.THEMES[theme_name]
                tile_bg = _g["SURFACE_2"] if selected else _g["SURFACE"]
                tile.configure(
                    bg=tile_bg,
                    highlightbackground=_g["ACCENT"] if selected else _g["BORDER"],
                    highlightcolor=_g["ACCENT"] if selected else _g["BORDER"],
                    highlightthickness=2 if selected else 1,
                )
                swatches.configure(bg=tile_bg)
                indicator.configure(bg=_g["ACCENT"] if selected else tile_bg)
                title.configure(
                    text=palette["NAME"],
                    bg=tile_bg,
                    fg=_g["TEXT"] if selected else _g["TEXT_SOFT"],
                    font=FONT_UI,
                )

        def select_theme(value: str) -> None:
            if value not in theme_module.THEMES:
                return
            if value == theme_var.get() and value == getattr(self, "_active_theme", None):
                return
            theme_var.set(value)
            self._apply_theme(value, rerender_read=False, flush=False)
            refresh_theme_tiles()
            refresh_setting_toggles()
            refresh_page_nav()
            draw_alpha_slider()
            msg.config(text=t("settings.msg.theme_preview", name=theme_module.THEMES[value]["NAME"]), fg=globals()["TEXT"])

        for index, (theme_name, palette) in enumerate(theme_module.THEMES.items()):
            _g = globals()
            tile = tk.Frame(
                theme_choices,
                bg=_g["SURFACE"],
                cursor="hand2",
                highlightbackground=_g["BORDER"],
                highlightthickness=1,
                padx=7,
                pady=6,
            )
            tile.grid(row=index // 2, column=index % 2, sticky="ew", padx=(0, 5), pady=3)
            indicator = tk.Frame(tile, bg=_g["SURFACE"], width=3, cursor="hand2")
            indicator.pack(side="left", fill="y", padx=(0, 6))
            indicator.pack_propagate(False)
            swatches = tk.Frame(tile, bg=_g["SURFACE"], cursor="hand2")
            swatches.pack(side="left", padx=(0, 7))
            main_swatch = tk.Label(swatches, bg=palette["BG"], width=2, height=1, cursor="hand2")
            explorer_swatch = tk.Label(swatches, bg=palette["SIDEBAR"], width=2, height=1, cursor="hand2")
            main_swatch.pack(side="left")
            explorer_swatch.pack(side="left")
            main_swatch._theme_swatch = True
            explorer_swatch._theme_swatch = True
            title = tk.Label(
                tile,
                text=palette["NAME"],
                bg=_g["SURFACE"],
                fg=_g["TEXT_SOFT"],
                font=FONT_UI,
                anchor="w",
                cursor="hand2",
            )
            title.pack(side="left", fill="x", expand=True)
            for target in (tile, indicator, swatches, main_swatch, explorer_swatch, title):
                target.bind("<Button-1>", lambda _e, value=theme_name: select_theme(value))
            theme_tiles[theme_name] = (tile, title, swatches, indicator)
        refresh_theme_tiles()

        typography_frame = tk.Frame(appearance_page, bg=g["BG"])
        typography_frame.pack(fill="x", padx=18, pady=(10, 6))
        typography_label = tk.Label(
            typography_frame,
            text=t("settings.typography"),
            bg=g["BG"],
            fg=g["TEXT"],
            font=FONT_CONTROL,
            anchor="w",
        )
        typography_label.pack(fill="x", pady=(0, 6))
        typography_panel = tk.Frame(
            typography_frame,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=8,
            pady=8,
        )
        typography_panel.pack(fill="x")
        controls_row = tk.Frame(typography_panel, bg=g["SURFACE"])
        controls_row.pack(fill="x")
        available_fonts = getattr(self, "_available_font_families", None)
        if available_fonts is None:
            available_fonts = tuple(sorted(set(tkfont.families(self.root)), key=str.casefold))
            self._available_font_families = available_fonts
        font_family_var = tk.StringVar(value=self.config.font_family)
        font_shell = tk.Frame(controls_row, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"])
        font_shell.pack(side="left", fill="x", expand=True, padx=(0, 8))
        font_dropdown = dropdown_control(
            font_shell,
            font_family_var,
            available_fonts,
            lambda: preview_typography(),
            max_rows=9,
            preview_font=True,
        )
        font_size_var = tk.IntVar(value=self.config.font_size)
        size_frame = tk.Frame(
            controls_row,
            bg=g["SURFACE_2"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
        )
        size_frame.pack(side="right")
        size_down = tk.Label(
            size_frame,
            text="-",
            bg=g["SURFACE_2"],
            fg=g["TEXT_SOFT"],
            font=FONT_PREVIEW_TITLE,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        size_value = tk.Label(
            size_frame,
            text=str(font_size_var.get()),
            bg=g["SURFACE_2"],
            fg=g["TEXT"],
            font=FONT_PREVIEW_LABEL,
            width=3,
            pady=6,
        )
        size_up = tk.Label(
            size_frame,
            text="+",
            bg=g["SURFACE_2"],
            fg=g["TEXT_SOFT"],
            font=FONT_PREVIEW_TITLE,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        size_down.pack(side="left")
        size_value.pack(side="left")
        size_up.pack(side="left")
        typography_preview = tk.Label(
            typography_panel,
            text="Aa Markdown 123",
            bg=g["SURFACE"],
            fg=g["TEXT_SOFT"],
            anchor="w",
            pady=8,
        )
        typography_preview.pack(fill="x", pady=(8, 0))

        def refresh_typography_preview_label() -> tuple[str, int] | None:
            family = font_family_var.get().strip() or "Segoe UI"
            try:
                size = max(8, min(20, int(font_size_var.get())))
            except (tk.TclError, ValueError):
                return None
            font_size_var.set(size)
            size_value.configure(text=str(size))
            typography_preview.configure(font=(family, size + 1), text=f"{family}  {size} pt")
            return family, size

        def preview_typography(*_args) -> None:
            preview = refresh_typography_preview_label()
            if preview is None:
                return
            family, size = preview
            self.config.font_family = family
            self.config.font_size = size
            self._apply_typography()
            refresh_page_nav()
            win.after_idle(update_scroll_region)
            msg.config(text=t("settings.msg.typography_preview", family=family, size=size), fg=globals()["TEXT"])

        def adjust_font_size(delta: int) -> str:
            try:
                current_size = int(font_size_var.get())
            except (tk.TclError, ValueError):
                current_size = self.config.font_size
            font_size_var.set(max(8, min(20, current_size + delta)))
            preview_typography()
            return "break"

        size_down.bind("<Button-1>", lambda _event: adjust_font_size(-1))
        size_up.bind("<Button-1>", lambda _event: adjust_font_size(1))
        font_dropdown["refresh"]()
        refresh_typography_preview_label()

        e_width = row(layout_page, t("settings.panel_width"), str(self.config.width))
        e_explorer = row(layout_page, t("settings.explorer_width"), str(self.config.explorer_width))
        width_hint = tk.Label(
            layout_page,
            text="",
            bg=g["BG"],
            fg=g["MUTED"],
            font=FONT_UI,
            anchor="w",
        )
        width_hint.pack(fill="x", padx=18, pady=(0, 6))

        def refresh_width_hint() -> None:
            work_width = max(1, self.work_right - self.work_left)
            panel_min, panel_max = panel_width_limits(work_width)
            explorer_min, explorer_max = explorer_width_limits(work_width)
            width_hint.config(
                text=t(
                    "settings.width_range_hint",
                    panel_min=panel_min,
                    panel_max=panel_max,
                    explorer_min=explorer_min,
                    explorer_max=explorer_max,
                )
            )

        refresh_width_hint()
        e_nav = row(layout_page, t("settings.nav_width"), str(self.config.nav_width))
        nav_anchor_var = tk.StringVar(
            value=str(getattr(self.config, "nav_bar_anchor", "panel_edge"))
            if str(getattr(self.config, "nav_bar_anchor", "panel_edge")) in {"panel_edge", "screen_edge"}
            else "panel_edge"
        )

        def apply_nav_preview() -> None:
            if not win.winfo_exists():
                return
            anchor = nav_anchor_var.get()
            self.config.nav_bar_anchor = anchor if anchor in {"panel_edge", "screen_edge"} else "panel_edge"
            self._place_layout(self.is_open)
            self._raise_nav_bar()
            self._refresh_nav_bar_visual()
            mode = nav_anchor_labels.get(self.config.nav_bar_anchor, self.config.nav_bar_anchor)
            msg.config(text=t("settings.msg.nav_anchor_preview", mode=mode), fg=globals()["TEXT"])

        def select_nav_anchor(value: str, preview: bool = True) -> None:
            if value not in {"panel_edge", "screen_edge"}:
                return
            nav_anchor_var.set(value)
            for key, button in nav_anchor_buttons.items():
                style_dual_choice_button(button, key == value)
            if preview:
                apply_nav_preview()

        nav_anchor_labels = {
            "panel_edge": t("nav_anchor.panel_edge"),
            "screen_edge": t("nav_anchor.screen_edge"),
        }
        nav_anchor_label, nav_anchor_buttons, _nav_anchor_choices = add_dual_choice_row(
            layout_page,
            t("settings.nav_bar.anchor"),
            ("panel_edge", "screen_edge"),
            nav_anchor_labels,
            lambda value: select_nav_anchor(str(value)),
        )
        select_nav_anchor(nav_anchor_var.get(), preview=False)
        width_preview_after: str | None = None
        syncing_width_entries = False

        def set_width_entry(entry: tk.Entry, value: int) -> None:
            if entry.get().strip() == str(value):
                return
            entry.delete(0, tk.END)
            entry.insert(0, str(value))

        def sync_width_entries(panel_width: int, explorer_width: int) -> None:
            nonlocal syncing_width_entries
            if not win.winfo_exists():
                return
            syncing_width_entries = True
            try:
                set_width_entry(e_width, panel_width)
                set_width_entry(e_explorer, explorer_width)
            finally:
                syncing_width_entries = False

        self._settings_width_sync = sync_width_entries

        def apply_width_preview() -> None:
            nonlocal width_preview_after
            width_preview_after = None
            if syncing_width_entries or not win.winfo_exists():
                return
            try:
                panel_width = int(e_width.get().strip())
                explorer_width = int(e_explorer.get().strip())
                nav_width = int(e_nav.get().strip())
            except ValueError:
                return
            work_width = max(1, self.work_right - self.work_left)
            panel_min, panel_max = panel_width_limits(work_width)
            explorer_min, explorer_max = explorer_width_limits(work_width)
            if not panel_min <= panel_width <= panel_max or not explorer_min <= explorer_width <= explorer_max:
                return
            if not 4 <= nav_width <= 24:
                return
            if panel_width == self.panel_w and explorer_width == self.explorer_w and nav_width == self.nav_w:
                return
            self.panel_w = panel_width
            self.explorer_w = explorer_width
            self.nav_w = nav_width
            self.config.width = panel_width
            self.config.explorer_width = explorer_width
            self.config.nav_width = nav_width
            self._apply_live_width_layout()
            self._refresh_after_width_drag()
            msg.config(text=t("settings.msg.width_preview"), fg=globals()["TEXT"])

        def schedule_width_preview(_event=None) -> None:
            nonlocal width_preview_after
            if syncing_width_entries:
                return
            if width_preview_after is not None:
                try:
                    win.after_cancel(width_preview_after)
                except tk.TclError:
                    pass
            width_preview_after = win.after(140, apply_width_preview)

        for width_entry in (e_width, e_explorer, e_nav):
            width_entry.bind("<KeyRelease>", schedule_width_preview)
            width_entry.bind("<Return>", lambda _event: apply_width_preview())
            width_entry.bind("<FocusOut>", lambda _event: apply_width_preview())
        opacity_frame = tk.Frame(appearance_page, bg=g["BG"])
        opacity_frame.pack(fill="x", padx=18, pady=6)
        opacity_label = tk.Label(
            opacity_frame,
            text=t("settings.opacity"),
            bg=g["BG"],
            fg=g["TEXT"],
            font=FONT_CONTROL,
            width=16,
            anchor="w",
        )
        opacity_label.pack(side="left")
        alpha_var = tk.DoubleVar(value=self.config.alpha)
        alpha_value = tk.Label(
            opacity_frame,
            text=f"{round(self.config.alpha * 100)}%",
            bg=g["BG"],
            fg=g["TEXT_SOFT"],
            font=FONT_UI,
            width=5,
            anchor="e",
        )

        def preview_opacity(value: str) -> None:
            alpha = max(0.30, min(1.0, float(value)))
            self._preview_alpha = alpha
            self._apply_content_opacity(alpha)
            alpha_value.config(text=f"{round(alpha * 100)}%")
            msg.config(text=t("settings.msg.opacity_preview"), fg=globals()["TEXT"])

        alpha_scale = tk.Canvas(
            opacity_frame,
            height=30,
            bg=g["BG"],
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
            takefocus=True,
        )

        def _alpha_slider_draw_width() -> int:
            width = alpha_scale.winfo_width()
            if width > 1:
                return max(40, width)
            frame_w = opacity_frame.winfo_width()
            if frame_w > 1:
                return max(40, frame_w - 130)
            pages_w = settings_pages.winfo_width()
            if pages_w > 1:
                return max(40, pages_w - 50)
            return max(220, settings_w - 200)

        def draw_alpha_slider(_event=None) -> None:
            _g = globals()
            alpha_scale.delete("all")
            width = _alpha_slider_draw_width()
            left, right, center_y = 11, width - 11, 15
            progress = (alpha_var.get() - 0.30) / 0.70
            progress = max(0.0, min(1.0, progress))
            thumb_x = left + (right - left) * progress
            glow = _g["ACCENT"]
            alpha_scale.create_line(left, center_y, right, center_y, fill=_g["BORDER"], width=8, capstyle=tk.ROUND)
            alpha_scale.create_line(left, center_y, right, center_y, fill=_g["SURFACE_2"], width=5, capstyle=tk.ROUND)
            alpha_scale.create_line(left, center_y, thumb_x, center_y, fill=glow, width=8, capstyle=tk.ROUND)
            alpha_scale.create_line(left, center_y, thumb_x, center_y, fill=_g["ACCENT_2"], width=4, capstyle=tk.ROUND)
            for radius, color in ((11, _g["BG"]), (10, glow), (8, _g["SURFACE_2"]), (6, _g["SURFACE"])):
                alpha_scale.create_oval(
                    thumb_x - radius,
                    center_y - radius,
                    thumb_x + radius,
                    center_y + radius,
                    fill=color,
                    outline="",
                )
            alpha_scale.create_oval(
                thumb_x - 4,
                center_y - 4,
                thumb_x + 4,
                center_y + 4,
                fill=_g["ACCENT_2"],
                outline="",
            )

        def set_alpha_from_x(x: int) -> None:
            width = _alpha_slider_draw_width()
            progress = max(0.0, min(1.0, (x - 11) / max(1, width - 22)))
            alpha = round(0.30 + progress * 0.70, 3)
            alpha_var.set(alpha)
            preview_opacity(str(alpha))
            draw_alpha_slider()

        def nudge_alpha(delta: float) -> str:
            alpha = max(0.30, min(1.0, alpha_var.get() + delta))
            alpha_var.set(round(alpha, 3))
            preview_opacity(str(alpha_var.get()))
            draw_alpha_slider()
            return "break"

        alpha_scale.bind("<Configure>", draw_alpha_slider)
        alpha_scale.bind("<Button-1>", lambda event: (alpha_scale.focus_set(), set_alpha_from_x(event.x)))
        alpha_scale.bind("<B1-Motion>", lambda event: set_alpha_from_x(event.x))
        alpha_scale.bind("<Left>", lambda _event: nudge_alpha(-0.01))
        alpha_scale.bind("<Right>", lambda _event: nudge_alpha(0.01))
        alpha_scale.bind("<Shift-Left>", lambda _event: nudge_alpha(-0.05))
        alpha_scale.bind("<Shift-Right>", lambda _event: nudge_alpha(0.05))
        alpha_scale.pack(side="left", fill="x", expand=True, padx=(4, 4))
        alpha_value.pack(side="right", padx=(2, 6))

        def finalize_appearance_page() -> None:
            refresh_theme_tiles()
            refresh_typography_preview_label()
            font_dropdown["refresh"]()
            draw_alpha_slider()

        page_finalize["appearance"] = finalize_appearance_page

        def _plugins_description_wraplength() -> int:
            width = plugins_list.winfo_width()
            if width > 1:
                return max(180, width - 160)
            page_w = plugins_page.winfo_width()
            if page_w > 1:
                return max(180, page_w - 196)
            return max(180, settings_w - 240)

        def finalize_plugins_page() -> None:
            refresh_plugin_rows()
            wraplength = _plugins_description_wraplength()
            plugins_hint_label.configure(wraplength=max(220, wraplength + 36))
            for row_state in plugin_rows:
                row_state["description"].configure(wraplength=wraplength)

        page_finalize["plugins"] = finalize_plugins_page

        bools = tk.Frame(
            general_page,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=8,
            pady=8,
        )
        bools.pack(fill="x", padx=18, pady=(8, 4))
        auto_save_var = tk.BooleanVar(value=self.config.auto_save)
        remember_var = tk.BooleanVar(value=self.config.remember_last_note)
        explorer_var = tk.BooleanVar(value=self.config.explorer_open)
        start_on_boot_var = tk.BooleanVar(value=self.config.start_on_boot)
        setting_toggles: list[tuple[str, tk.BooleanVar, tk.Frame, tk.Label, tk.Label]] = []

        def make_toggle_image(selected: bool) -> ImageTk.PhotoImage:
            _g = globals()
            width, height, scale = 38, 20, 4
            size = (width * scale, height * scale)
            image = Image.new("RGBA", size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            radius = height * scale // 2
            track_box = (1 * scale, 2 * scale, (width - 1) * scale, (height - 2) * scale)
            track_fill = _g["ACCENT"] if selected else _g["SURFACE_2"]
            track_outline = _g["ACCENT_2"] if selected else _g["BORDER"]
            draw.rounded_rectangle(
                track_box,
                radius=radius,
                fill=track_fill,
                outline=track_outline,
                width=scale,
            )
            knob_center_x = 28 if selected else 10
            knob_radius = 7
            shadow = (
                (knob_center_x - knob_radius + 1) * scale,
                (10 - knob_radius + 1) * scale,
                (knob_center_x + knob_radius + 1) * scale,
                (10 + knob_radius + 1) * scale,
            )
            knob = (
                (knob_center_x - knob_radius) * scale,
                (10 - knob_radius) * scale,
                (knob_center_x + knob_radius) * scale,
                (10 + knob_radius) * scale,
            )
            draw.ellipse(shadow, fill=(0, 0, 0, 42 if selected else 26))
            draw.ellipse(
                knob,
                fill=self._contrast_text(_g["ACCENT"]) if selected else _g["SURFACE"],
                outline=_g["ACCENT_2"] if selected else _g["BORDER"],
                width=scale,
            )
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            return ImageTk.PhotoImage(image.resize((width, height), resample_filter))

        def refresh_setting_toggles() -> None:
            _g = globals()
            for text_key, var, row_frame, switch, text_label in setting_toggles:
                selected = var.get()
                row_frame.configure(bg=_g["SURFACE"])
                switch.configure(bg=_g["SURFACE"])
                toggle_image = make_toggle_image(selected)
                switch.configure(image=toggle_image)
                switch._toggle_image = toggle_image  # type: ignore[attr-defined]
                text_label.configure(
                    text=t(text_key),
                    bg=_g["SURFACE"],
                    fg=_g["TEXT"] if selected else _g["TEXT_SOFT"],
                    font=FONT_UI,
                )

        def add_setting_toggle(text_key: str, var: tk.BooleanVar) -> None:
            _g = globals()
            row_frame = tk.Frame(bools, bg=_g["SURFACE"], cursor="hand2", padx=5, pady=6)
            row_frame.pack(fill="x", pady=1)
            switch = tk.Label(
                row_frame,
                bg=_g["SURFACE"],
                cursor="hand2",
                highlightthickness=0,
                borderwidth=0,
                padx=0,
                pady=0,
            )
            switch.pack(side="left", padx=(0, 9))
            text_label = tk.Label(
                row_frame,
                text=t(text_key),
                bg=_g["SURFACE"],
                fg=_g["TEXT"],
                font=FONT_UI,
                anchor="w",
                cursor="hand2",
            )
            text_label.pack(side="left", fill="x", expand=True)

            def toggle(_event=None) -> None:
                var.set(not var.get())
                refresh_setting_toggles()

            def enter(_event=None) -> None:
                text_label.configure(fg=globals()["TEXT"])

            def leave(_event=None) -> None:
                refresh_setting_toggles()

            for target in (row_frame, switch, text_label):
                target.bind("<Button-1>", toggle)
                target.bind("<Enter>", enter)
                target.bind("<Leave>", leave)
            setting_toggles.append((text_key, var, row_frame, switch, text_label))

        for text_key, var in (
            ("settings.toggle.auto_save", auto_save_var),
            ("settings.toggle.remember_note", remember_var),
            ("settings.toggle.explorer", explorer_var),
            ("settings.toggle.startup", start_on_boot_var),
        ):
            add_setting_toggle(text_key, var)
        refresh_setting_toggles()

        def update_entry_label(entry: tk.Entry, text_key: str) -> None:
            label_widget = getattr(entry, "_label_widget", None)
            if label_widget is not None:
                label_widget.configure(text=t(text_key))

        def refresh_settings_language() -> None:
            win.title(t("settings.window_title", app=APP_NAME))
            settings_title_label.configure(text=t("settings.title"))
            shortcuts_hint_label.configure(text=t("settings.shortcuts_hint"))
            plugins_hint_label.configure(text=t("settings.plugins_hint"))
            for key, button in page_buttons.items():
                button.configure(text=t(f"settings.page.{key}"))
            language_label.configure(text=t("settings.language"))
            update_entry_label(e_notes, "settings.notes_folder")
            update_entry_label(e_attachments, "settings.attachments_folder")
            update_entry_label(e_hotkey, "settings.hotkey")
            update_entry_label(e_width, "settings.panel_width")
            update_entry_label(e_explorer, "settings.explorer_width")
            update_entry_label(e_nav, "settings.nav_width")
            position_label.configure(text=t("settings.app_position"))
            position_labels.update({"left": t("position.left"), "right": t("position.right")})
            for key, button in position_buttons.items():
                button.configure(text=position_labels[key])
            select_position(position_var.get(), preview=False)
            nav_anchor_label.configure(text=t("settings.nav_bar.anchor"))
            nav_anchor_labels.update(
                {
                    "panel_edge": t("nav_anchor.panel_edge"),
                    "screen_edge": t("nav_anchor.screen_edge"),
                }
            )
            for key, button in nav_anchor_buttons.items():
                button.configure(text=nav_anchor_labels[key])
            select_nav_anchor(nav_anchor_var.get(), preview=False)
            theme_label.configure(text=t("settings.color_theme"))
            typography_label.configure(text=t("settings.typography"))
            opacity_label.configure(text=t("settings.opacity"))
            backups_label.configure(text=t("settings.backups", path=BACKUP_DIR))
            refresh_width_hint()
            browse_button = getattr(e_notes, "_browse_button", None)
            if browse_button is not None:
                browse_button.configure(text=t("settings.browse"))
            attachments_button = getattr(e_attachments, "_action_button", None)
            if attachments_button is not None:
                attachments_button.configure(text=t("settings.browse"))
            hotkey_button = getattr(e_hotkey, "_action_button", None)
            if hotkey_button is not None:
                hotkey_button.configure(text=t("settings.record"))
            for command_id, entry in shortcut_entries.items():
                label_widget = getattr(entry, "_label_widget", None)
                if label_widget is not None:
                    label_widget.configure(text=command_label(command_id))
            for button in shortcut_record_buttons.values():
                if str(button.cget("state")) != tk.DISABLED:
                    button.configure(text=t("settings.record"))
            restore_shortcuts_button.configure(text=t("settings.restore_defaults"))
            finalize_plugins_page()
            refresh_setting_toggles()
            refresh_page_nav()
            win.after_idle(update_scroll_region)

        def apply_runtime_settings(
            workspace_changed: bool,
            previous_position: str,
            previous_panel_width: int,
            previous_explorer_width: int,
        ) -> None:
            self.panel_w = self.config.width
            self.explorer_w = self.config.explorer_width
            self.nav_w = self.config.nav_width
            self.explorer_frame.config(width=self.explorer_w)
            self._apply_content_opacity(self.config.alpha)
            self._apply_header_alignment()
            self._register_hotkey()
            self._register_sticky_notes_hotkey()
            self._register_plugin_shortcuts()
            self._register_command_shortcuts()
            position_changed = previous_position != self.config.app_position

            def finish_layout() -> None:
                self._update_width_resize_handles()
                if self.is_open and self.explorer_visible:
                    self._refresh_explorer()
                    self.explorer.deiconify()
                    self.explorer.lift()
                    self.root.lift()
                elif not self.explorer_visible:
                    self.explorer.withdraw()
                self._raise_nav_bar()
                self._refresh_nav_bar_visual()
                self._update_hotkey_hints()

            if self.is_open and position_changed:
                self._animate_side_switch(previous_position, callback=finish_layout)
            else:
                self._place_layout(self.is_open)
                self.root.update_idletasks()
                self.explorer.update_idletasks()
                finish_layout()
            if not workspace_changed and self.explorer_visible:
                self._refresh_explorer()

        def save_settings() -> bool:
            _g = globals()
            new_hotkey = normalize_hotkey(e_hotkey.get())
            if not validate_hotkey(new_hotkey):
                msg.config(text=t("settings.msg.invalid_hotkey"), fg=_g["DANGER"])
                return False
            command_shortcuts: dict[str, str] = {}
            for command_id, entry in shortcut_entries.items():
                shortcut = normalize_hotkey(entry.get())
                if shortcut and not validate_hotkey(shortcut):
                    label = command_label(command_id)
                    msg.config(text=t("settings.msg.invalid_shortcut", label=label), fg=_g["DANGER"])
                    return False
                command_shortcuts[command_id] = shortcut
            conflicts = shortcut_conflicts(command_shortcuts)
            if conflicts:
                shortcut, command_ids = next(iter(conflicts.items()))
                labels = ", ".join(command_label(item) for item in command_ids)
                msg.config(text=t("settings.msg.shortcut_conflict", hotkey=format_hotkey_display(shortcut), labels=labels), fg=_g["DANGER"])
                return False
            panel_conflict = [
                command_id
                for command_id, shortcut in command_shortcuts.items()
                if shortcut and shortcut == new_hotkey
            ]
            if panel_conflict:
                label = command_label(panel_conflict[0])
                msg.config(text=t("settings.msg.panel_hotkey_conflict", label=label), fg=_g["DANGER"])
                return False
            plugin_shortcuts = {
                plugin_id: normalize_hotkey(shortcut)
                for plugin_id, shortcut in current_plugin_shortcuts.items()
                if normalize_hotkey(shortcut)
            }
            if sticky_plugin_double_ctrl:
                plugin_shortcuts.pop("sticky_notes", None)
            for plugin_id, shortcut in plugin_shortcuts.items():
                if is_modifier_only_hotkey(shortcut) or not validate_hotkey(shortcut):
                    plugin = next((item for item in BUILTIN_PLUGINS if item.id == plugin_id), None)
                    label = t(plugin.name_key) if plugin is not None else plugin_id
                    msg.config(text=t("settings.msg.invalid_shortcut", label=label), fg=_g["DANGER"])
                    return False
                if shortcut == new_hotkey:
                    plugin = next((item for item in BUILTIN_PLUGINS if item.id == plugin_id), None)
                    label = t(plugin.name_key) if plugin is not None else plugin_id
                    msg.config(text=t("settings.msg.panel_hotkey_conflict", label=label), fg=_g["DANGER"])
                    return False
                for command_id, command_shortcut in command_shortcuts.items():
                    if command_shortcut and command_shortcut == shortcut:
                        plugin = next((item for item in BUILTIN_PLUGINS if item.id == plugin_id), None)
                        plugin_label = t(plugin.name_key) if plugin is not None else plugin_id
                        command_text = command_label(command_id)
                        msg.config(
                            text=t("settings.msg.shortcut_conflict", hotkey=format_hotkey_display(shortcut), labels=f"{plugin_label}, {command_text}"),
                            fg=_g["DANGER"],
                        )
                        return False
            seen_plugin_shortcuts: dict[str, list[str]] = {}
            for plugin_id, shortcut in plugin_shortcuts.items():
                seen_plugin_shortcuts.setdefault(shortcut, []).append(plugin_id)
            plugin_conflicts = {shortcut: ids for shortcut, ids in seen_plugin_shortcuts.items() if len(ids) > 1}
            if plugin_conflicts:
                shortcut, plugin_ids = next(iter(plugin_conflicts.items()))
                labels = []
                for plugin_id in plugin_ids:
                    plugin = next((item for item in BUILTIN_PLUGINS if item.id == plugin_id), None)
                    labels.append(t(plugin.name_key) if plugin is not None else plugin_id)
                msg.config(text=t("settings.msg.shortcut_conflict", hotkey=format_hotkey_display(shortcut), labels=", ".join(labels)), fg=_g["DANGER"])
                return False
            try:
                panel_width = int(e_width.get().strip())
                explorer_width = int(e_explorer.get().strip())
                nav_width = int(e_nav.get().strip())
                alpha = round(float(alpha_var.get()), 3)
                font_size = max(8, min(20, int(font_size_var.get())))
            except (tk.TclError, ValueError):
                msg.config(text=t("settings.msg.numeric_required"), fg=_g["DANGER"])
                return False
            work_width = max(1, self.work_right - self.work_left)
            panel_min, panel_max = panel_width_limits(work_width)
            explorer_min, explorer_max = explorer_width_limits(work_width)
            if not panel_min <= panel_width <= panel_max:
                msg.config(
                    text=t("settings.msg.panel_width_range", min=panel_min, max=panel_max),
                    fg=_g["DANGER"],
                )
                return False
            if not explorer_min <= explorer_width <= explorer_max:
                msg.config(
                    text=t("settings.msg.explorer_width_range", min=explorer_min, max=explorer_max),
                    fg=_g["DANGER"],
                )
                return False
            if not 4 <= nav_width <= 24:
                msg.config(text=t("settings.msg.nav_width_range"), fg=_g["DANGER"])
                return False
            if not 0.30 <= alpha <= 1.0:
                msg.config(text=t("settings.msg.opacity_range"), fg=_g["DANGER"])
                return False
            notes_dir = e_notes.get().strip() or AppConfig().notes_directory
            notes_path = Path(notes_dir).expanduser()
            if notes_path.exists() and not notes_path.is_dir():
                msg.config(text=t("settings.msg.notes_not_dir"), fg=_g["DANGER"])
                return False
            raw_attachments_folder = e_attachments.get().strip().replace("\\", "/").strip("/")
            attachments_folder = normalize_relative_folder(
                raw_attachments_folder,
                AppConfig().attachments_folder,
            )
            attachments_path = Path(attachments_folder)
            if (
                not raw_attachments_folder
                or attachments_path.is_absolute()
                or ".." in Path(raw_attachments_folder).parts
                or attachments_folder != Path(raw_attachments_folder).as_posix()
            ):
                msg.config(text=t("settings.msg.attachments_relative"), fg=_g["DANGER"])
                return False
            try:
                set_startup_enabled(start_on_boot_var.get())
            except OSError as exc:
                msg.config(text=t("settings.msg.startup_failed", exc=exc), fg=_g["DANGER"])
                return False
            try:
                win.withdraw()
                win.update_idletasks()
            except tk.TclError:
                pass
            workspace_changed = apply_workspace_only()
            previous_position = self.config.app_position
            previous_panel_width = self.panel_w
            previous_explorer_width = self.explorer_w
            self.config.hotkey = new_hotkey
            self.config.command_shortcuts = command_shortcuts
            self.config.plugin_shortcuts = plugin_shortcuts
            self.config.sticky_notes_double_ctrl = sticky_plugin_double_ctrl
            self.config.obsidian_vault = ""
            self.config.width = panel_width
            self.config.explorer_width = explorer_width
            self.config.nav_width = nav_width
            anchor = nav_anchor_var.get()
            self.config.nav_bar_anchor = anchor if anchor in {"panel_edge", "screen_edge"} else "panel_edge"
            self.config.alpha = alpha
            self._preview_alpha = None
            self.config.app_position = position_var.get() if position_var.get() in {"left", "right"} else "right"
            self.config.theme = theme_var.get() if theme_var.get() in theme_module.THEMES else theme_module.DEFAULT_THEME
            if self.config.theme != getattr(self, "_active_theme", None):
                self._apply_theme(self.config.theme)
            self.config.font_family = font_family_var.get().strip() or "Segoe UI"
            self.config.font_size = font_size
            self.config.attachments_folder = attachments_folder
            self._apply_typography()
            self.config.auto_save = auto_save_var.get()
            self.config.remember_last_note = remember_var.get()
            self.config.explorer_open = explorer_var.get()
            self.config.start_on_boot = start_on_boot_var.get()
            selected_language = language_var.get()
            self.config.language = label_to_code.get(selected_language, normalize_language(selected_language))
            set_language(self.config.language)
            self.explorer_visible = self.config.explorer_open
            self.config.auto_close_on_blur = False
            self.config.auto_close_on_escape = False
            save_config(self.config)
            self._apply_language()
            apply_runtime_settings(workspace_changed, previous_position, previous_panel_width, previous_explorer_width)
            return True

        def discard_settings() -> None:
            previous_position = self.config.app_position
            previous_panel_width = self.panel_w
            previous_explorer_width = self.explorer_w
            workspace_changed = Path(self.config.notes_directory).expanduser().resolve() != Path(original["notes_directory"]).expanduser().resolve()
            self.config.notes_directory = str(original["notes_directory"])
            self.config.hotkey = str(original["hotkey"])
            self.config.command_shortcuts = dict(original["command_shortcuts"])
            self.config.plugin_shortcuts = dict(original["plugin_shortcuts"])
            self.config.sticky_notes_double_ctrl = bool(original["sticky_notes_double_ctrl"])
            self.config.obsidian_vault = ""
            self.config.width = int(original["width"])
            self.config.explorer_width = int(original["explorer_width"])
            self.config.nav_width = int(original["nav_width"])
            self.config.nav_bar_anchor = str(original["nav_bar_anchor"])
            self.config.alpha = float(original["alpha"])
            self._preview_alpha = None
            self.config.app_position = str(original["app_position"])
            self.config.theme = str(original["theme"])
            self._apply_theme(self.config.theme)
            self.config.font_family = str(original["font_family"])
            self.config.font_size = int(original["font_size"])
            self.config.attachments_folder = str(original["attachments_folder"])
            self._apply_typography()
            self.config.auto_save = bool(original["auto_save"])
            self.config.remember_last_note = bool(original["remember_last_note"])
            self.config.explorer_open = bool(original["explorer_open"])
            self.config.start_on_boot = bool(original["start_on_boot"])
            self.config.enabled_plugins = list(original["enabled_plugins"])
            self.config.disabled_plugins = list(original["disabled_plugins"])
            self.config.removed_plugins = list(original["removed_plugins"])
            self.config.language = str(original["language"])
            set_language(self.config.language)
            self.explorer_visible = self.config.explorer_open
            self.config.auto_close_on_blur = False
            self.config.auto_close_on_escape = False
            if workspace_changed:
                self._switch_workspace(self.config.notes_directory)
            self._apply_language()
            apply_runtime_settings(workspace_changed, previous_position, previous_panel_width, previous_explorer_width)

        def close_settings() -> None:
            nonlocal width_preview_after
            choice = self._ask_save_discard_dialog(t("dialog.save_settings"), parent=win)
            if choice is None:
                return
            if choice == "save":
                if not save_settings():
                    return
            else:
                try:
                    win.withdraw()
                    win.update_idletasks()
                except tk.TclError:
                    pass
                discard_settings()
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            if width_preview_after is not None:
                try:
                    win.after_cancel(width_preview_after)
                except tk.TclError:
                    pass
                width_preview_after = None
            self._settings_width_sync = None
            self._settings_open = False
            win.destroy()
            self.root.after_idle(self._update_width_resize_handles)

        win.protocol("WM_DELETE_WINDOW", close_settings)

        def prewarm_settings_pages() -> None:
            saved = active_page.get()

            def prewarm() -> None:
                for page_key in pages:
                    for page in pages.values():
                        page.pack_forget()
                    pages[page_key].pack(fill="both", expand=True)
                    win.update_idletasks()
                    finalize = page_finalize.get(page_key)
                    if finalize is not None:
                        finalize()
                    update_scroll_region()
                active_page.set(saved)
                for page in pages.values():
                    page.pack_forget()
                pages[saved].pack(fill="both", expand=True)
                refresh_page_nav()
                canvas.yview_moveto(0)
                win.update_idletasks()
                update_scroll_region()

            _with_settings_redraw_suspended(prewarm)

        prewarm_settings_pages()
        win.deiconify()
        win.lift(self.root)

    def _browse_into(self, entry: tk.Entry, browse: Callable[[], str], after: Callable[[], None] | None = None) -> None:
        value = browse()
        if value:
            entry.delete(0, tk.END)
            entry.insert(0, value)
            if after:
                after()
