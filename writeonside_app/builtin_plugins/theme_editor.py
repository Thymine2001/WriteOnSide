from __future__ import annotations

import tkinter as tk
from contextlib import contextmanager
from tkinter import colorchooser, ttk

from ..config import save_config
from ..i18n import t
from ..platform import redraw_window, set_window_redraw
from .. import theme as theme_module
from .color_picker import ScreenColorPickerSession
from ..theme import (
    COLOR_GROUPS,
    CUSTOM_THEME_IDS,
    PREVIEW_THEME_ID,
    apply_custom_themes,
    build_theme_palette,
    custom_theme_entry,
    get_theme,
    list_builtin_theme_names,
    normalize_custom_themes,
    normalize_hex_color,
    normalize_palette,
)
from ..theme import *  # noqa: F401,F403


def run(app) -> None:
    ThemeEditorWindow(app).open()


def _plugin_button(app, parent: tk.Widget, text: str, command, *, primary: bool = False, danger: bool = False) -> tk.Button:
    g = globals()
    contrast = app._contrast_text(g["ACCENT"]) if hasattr(app, "_contrast_text") else g["TEXT"]
    bg = g["DANGER"] if danger else (g["ACCENT"] if primary else g["BORDER"])
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


class ThemeEditorWindow:
    def __init__(self, app) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self._theme_widgets: dict[str, object] = {}
        self._color_vars: dict[str, tk.StringVar] = {}
        self._swatches: dict[str, tk.Label] = {}
        self._base_theme_var = tk.StringVar(value=theme_module.DEFAULT_THEME)
        self._slot_var = tk.StringVar(value=CUSTOM_THEME_IDS[0])
        self._name_var = tk.StringVar(value="")
        self._preview_active = False
        self._theme_before_preview = getattr(app, "_active_theme", theme_module.DEFAULT_THEME)
        self._theme_at_open = self._theme_before_preview
        self._pre_preview_editor: dict[str, object] | None = None
        self._slot_buttons: dict[str, tk.Label] = {}
        self._pick_session: ScreenColorPickerSession | None = None
        self._redraw_handle: int | None = None
        self._color_rows: list[tuple[tk.Frame, tk.Label, tk.Label]] = []
        self._group_labels: list[tk.Label] = []
        self._setup_labels: list[tk.Label] = []
        self._suppress_preview_refresh = False
        self._redraw_pause_depth = 0

    def open(self) -> None:
        app = self.app
        if getattr(app, "_theme_editor_open", False):
            existing = getattr(app, "_theme_editor_window", None)
            try:
                if existing is not None:
                    win = getattr(existing, "win", None)
                    if win is not None and win.winfo_exists():
                        existing._show_plugin_window()
                        return
            except tk.TclError:
                pass
            app._theme_editor_open = False

        parent = getattr(app, "_plugin_parent_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = app.root
        except tk.TclError:
            parent = app.root

        g = globals()
        win = tk.Toplevel(parent)
        self.win = win
        win._skip_theme_recolor = True
        app._theme_editor_open = True
        app._theme_editor_window = self
        win.withdraw()
        win.title(t("theme_editor.window_title"))

        work_width = max(420, app.work_right - app.work_left)
        work_height = max(360, app.work_bottom - app.work_top)
        width = min(980, max(640, work_width - 40))
        height = min(820, max(620, work_height - 40))
        x = app.work_left + max(0, (work_width - width) // 2)
        y = app.work_top + max(0, (work_height - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.minsize(min(640, width), min(560, height))
        win.configure(bg=g["BG"])
        try:
            win.transient(parent)
        except tk.TclError:
            pass
        win.resizable(True, True)

        redraw_handle = self._window_handle(win)
        if redraw_handle is not None:
            set_window_redraw(redraw_handle, False)
        self._redraw_handle = redraw_handle

        footer = tk.Label(
            win,
            text=t("theme_editor.footer_hint"),
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
        cancel_btn = _plugin_button(app, action_bar, t("theme_editor.cancel"), self._cancel)
        cancel_btn.pack(side="right", padx=(8, 0))
        save_btn = _plugin_button(app, action_bar, t("theme_editor.save"), self._save, primary=True)
        save_btn.pack(side="right", padx=(8, 0))
        preview_btn = _plugin_button(app, action_bar, t("theme_editor.preview"), self._preview)
        preview_btn.pack(side="right")
        reset_btn = _plugin_button(app, action_bar, t("theme_editor.reset"), self._reset_slot)
        reset_btn.pack(side="left")

        body = tk.Frame(win, bg=g["BG"])
        body.pack(fill="both", expand=True, padx=22, pady=(16, 8))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(1, weight=1)

        hero = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=16,
            pady=14,
        )
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self._hero_title = tk.Label(
            hero,
            text=t("theme_editor.title"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        )
        self._hero_title.pack(fill="x")
        self.subtitle = tk.Label(
            hero,
            text=t("theme_editor.subtitle"),
            bg=g["SURFACE"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=max(420, width - 80),
        )
        self.subtitle.pack(fill="x", pady=(4, 0))

        editor_card = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=12,
            pady=12,
        )
        editor_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        editor_card.grid_rowconfigure(2, weight=1)
        editor_card.grid_columnconfigure(0, weight=1)

        setup_row = tk.Frame(editor_card, bg=g["SURFACE"])
        setup_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        setup_row.grid_columnconfigure(1, weight=1)

        slot_caption = tk.Label(
            setup_row,
            text=t("theme_editor.slot"),
            bg=g["SURFACE"],
            fg=g["TEXT_SOFT"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        slot_caption.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        self._setup_labels.append(slot_caption)
        slot_row = tk.Frame(setup_row, bg=g["SURFACE"])
        slot_row.grid(row=0, column=1, sticky="w", pady=(0, 6))
        for index, slot_id in enumerate(CUSTOM_THEME_IDS, start=1):
            button = tk.Label(
                slot_row,
                text=t("theme_editor.slot_label", index=index),
                bg=g["SURFACE"],
                fg=g["TEXT_SOFT"],
                font=("Segoe UI", 9),
                padx=10,
                pady=6,
                cursor="hand2",
                highlightthickness=1,
                highlightbackground=g["BORDER"],
            )
            button.pack(side="left", padx=(0, 6))
            button.bind("<Button-1>", lambda _event, value=slot_id: self._select_slot(value))
            self._slot_buttons[slot_id] = button

        base_caption = tk.Label(
            setup_row,
            text=t("theme_editor.base_theme"),
            bg=g["SURFACE"],
            fg=g["TEXT_SOFT"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        base_caption.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        self._setup_labels.append(base_caption)
        base_names = list_builtin_theme_names()
        active = getattr(app, "_active_theme", theme_module.DEFAULT_THEME)
        if active in base_names:
            self._base_theme_var.set(active)
        elif base_names:
            self._base_theme_var.set(base_names[0])
        base_combo = ttk.Combobox(
            setup_row,
            textvariable=self._base_theme_var,
            values=[theme_module.THEMES[name]["NAME"] for name in base_names],
            state="readonly",
            style="ThemeEditor.TCombobox",
        )
        base_combo.grid(row=1, column=1, sticky="ew", pady=(0, 6))
        self._base_theme_ids = base_names
        self._base_theme_combo = base_combo
        self._style_base_combo()
        base_combo.bind("<<ComboboxSelected>>", lambda _event: self._load_from_base_selection())

        name_caption = tk.Label(
            setup_row,
            text=t("theme_editor.name"),
            bg=g["SURFACE"],
            fg=g["TEXT_SOFT"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        name_caption.grid(row=2, column=0, sticky="w", padx=(0, 8))
        self._setup_labels.append(name_caption)
        name_entry = tk.Entry(
            setup_row,
            textvariable=self._name_var,
            bg=g["SURFACE_2"],
            fg=g["TEXT"],
            insertbackground=g["ACCENT"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            highlightcolor=g["ACCENT"],
        )
        name_entry.grid(row=2, column=1, sticky="ew", ipady=5)

        self._colors_heading = tk.Label(
            editor_card,
            text=t("theme_editor.section.colors"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self._colors_heading.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        colors_host = tk.Frame(editor_card, bg=g["SURFACE"])
        colors_host.grid(row=2, column=0, sticky="nsew")
        colors_host.grid_rowconfigure(0, weight=1)
        colors_host.grid_columnconfigure(0, weight=1)

        colors_canvas = tk.Canvas(colors_host, bg=g["SURFACE"], highlightthickness=0, bd=0)
        scroll_track = tk.Frame(colors_host, bg=g["BG"], width=12, cursor="sb_v_double_arrow")
        scroll_thumb = tk.Frame(scroll_track, bg=g["BORDER"], width=5, cursor="sb_v_double_arrow")
        colors_inner = tk.Frame(colors_canvas, bg=g["SURFACE"])
        colors_window = colors_canvas.create_window((0, 0), window=colors_inner, anchor="nw")
        colors_canvas.configure(yscrollcommand=lambda first, last: update_scroll_thumb(first, last))
        colors_canvas.pack(side="left", fill="both", expand=True)
        scroll_track.pack(side="right", fill="y", padx=(4, 0))
        scroll_track.pack_propagate(False)

        def update_scroll_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                scroll_thumb.place_forget()
                return
            scroll_thumb.place(relx=0.5, rely=start, relheight=max(0.08, end - start), width=5, anchor="n")

        def sync_scroll_region(_event=None) -> None:
            try:
                colors_canvas.configure(scrollregion=colors_canvas.bbox("all"))
                first, last = colors_canvas.yview()
                update_scroll_thumb(str(first), str(last))
            except tk.TclError:
                pass

        def sync_canvas_width(event) -> None:
            try:
                colors_canvas.itemconfigure(colors_window, width=max(1, event.width))
            except tk.TclError:
                pass

        def scroll_to_pointer(event) -> None:
            height = max(1, scroll_track.winfo_height())
            colors_canvas.yview_moveto(max(0.0, min(1.0, event.y / height)))

        scroll_drag_state = {"y": 0, "first": 0.0}

        def start_thumb_drag(event) -> None:
            first, _last = colors_canvas.yview()
            scroll_drag_state["y"] = event.y_root
            scroll_drag_state["first"] = first
            scroll_thumb.configure(bg=globals()["ACCENT"])

        def drag_thumb(event) -> None:
            height = max(1, scroll_track.winfo_height())
            delta = (event.y_root - scroll_drag_state["y"]) / height
            colors_canvas.yview_moveto(max(0.0, min(1.0, scroll_drag_state["first"] + delta)))

        def end_thumb_drag(_event) -> None:
            scroll_thumb.configure(bg=globals()["BORDER"])

        def scroll_content(event) -> str:
            delta = -1 if event.delta > 0 else 1
            colors_canvas.yview_scroll(delta * 3, "units")
            return "break"

        def bind_scroll_wheel(widget: tk.Misc) -> None:
            widget.bind("<MouseWheel>", scroll_content, add="+")
            widget.bind("<Button-4>", lambda _event: colors_canvas.yview_scroll(-3, "units"), add="+")
            widget.bind("<Button-5>", lambda _event: colors_canvas.yview_scroll(3, "units"), add="+")
            for child in widget.winfo_children():
                bind_scroll_wheel(child)

        colors_inner.bind("<Configure>", sync_scroll_region)
        colors_canvas.bind("<Configure>", sync_canvas_width)
        scroll_track.bind("<Button-1>", scroll_to_pointer)
        scroll_thumb.bind("<ButtonPress-1>", start_thumb_drag)
        scroll_thumb.bind("<B1-Motion>", drag_thumb)
        scroll_thumb.bind("<ButtonRelease-1>", end_thumb_drag)
        scroll_thumb.bind("<Enter>", lambda _event: scroll_thumb.configure(bg=globals()["ACCENT_2"]))
        scroll_thumb.bind("<Leave>", lambda _event: scroll_thumb.configure(bg=globals()["BORDER"]))
        bind_scroll_wheel(colors_canvas)
        bind_scroll_wheel(scroll_track)

        for group_key, keys in COLOR_GROUPS:
            group_label = tk.Label(
                colors_inner,
                text=t(group_key),
                bg=g["SURFACE"],
                fg=g["TEXT_SOFT"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            )
            group_label.pack(fill="x", pady=(10, 4))
            self._group_labels.append(group_label)
            for color_key in keys:
                row = tk.Frame(colors_inner, bg=g["SURFACE"])
                row.pack(fill="x", pady=2)
                name_label = tk.Label(
                    row,
                    text=t(f"theme_editor.color.{color_key}"),
                    bg=g["SURFACE"],
                    fg=g["TEXT"],
                    font=("Segoe UI", 9),
                    width=18,
                    anchor="w",
                )
                name_label.pack(side="left")
                var = tk.StringVar(value=get_theme(theme_module.DEFAULT_THEME)[color_key])
                self._color_vars[color_key] = var
                swatch = tk.Label(row, text="   ", bg=var.get(), width=3, relief="flat", cursor="hand2")
                swatch.pack(side="left", padx=(0, 8))
                swatch.bind("<Button-1>", lambda _event, key=color_key: self._pick_color(key))
                self._swatches[color_key] = swatch
                value_label = tk.Label(row, textvariable=var, bg=g["SURFACE"], fg=g["MUTED"], font=("Consolas", 9), width=8, anchor="w")
                value_label.pack(side="left", padx=(0, 8))
                self._color_rows.append((row, name_label, value_label))
                pick_btn = _plugin_button(app, row, t("theme_editor.pick"), lambda key=color_key: self._pick_color(key))
                pick_btn.pack(side="right")
                eyedrop_btn = _plugin_button(app, row, t("theme_editor.eyedropper"), lambda key=color_key: self._eyedrop_color(key))
                eyedrop_btn.pack(side="right", padx=(0, 6))
                var.trace_add("write", lambda *_args, key=color_key: self._sync_swatch(key))

        bind_scroll_wheel(colors_inner)
        sync_scroll_region()

        preview_card = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=12,
            pady=12,
        )
        preview_card.grid(row=1, column=1, sticky="nsew")
        self._preview_heading = tk.Label(
            preview_card,
            text=t("theme_editor.section.preview"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self._preview_heading.pack(fill="x", pady=(0, 8))
        self.preview_panel = tk.Frame(preview_card, bg=g["BG"], highlightthickness=1, highlightbackground=g["BORDER"])
        self.preview_panel.pack(fill="both", expand=True)
        self._build_preview_widgets()

        self._theme_widgets = {
            "win": win,
            "body": body,
            "hero": hero,
            "editor_card": editor_card,
            "preview_card": preview_card,
            "footer": footer,
            "action_bar": action_bar,
            "colors_canvas": colors_canvas,
            "colors_inner": colors_inner,
            "scroll_track": scroll_track,
            "scroll_thumb": scroll_thumb,
            "name_entry": name_entry,
            "base_combo": base_combo,
            "setup_row": setup_row,
            "slot_row": slot_row,
            "colors_host": colors_host,
        }

        def close() -> None:
            if self._pick_session is not None:
                self._pick_session.cancel()
                self._pick_session = None
            self._revert_preview()
            theme_module.THEMES.pop(PREVIEW_THEME_ID, None)
            app._theme_editor_open = False
            app._theme_editor_window = None
            if getattr(app, "_refresh_theme_editor_theme", None) is refresh_theme:
                try:
                    delattr(app, "_refresh_theme_editor_theme")
                except AttributeError:
                    pass
            try:
                win.destroy()
            except tk.TclError:
                pass

        def refresh_theme() -> None:
            with self._pause_window_redraw():
                self._refresh_plugin_surface()

        app._refresh_theme_editor_theme = refresh_theme

        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _event: close())

        self._select_slot(self._initial_slot(), refresh_preview=False)
        self._theme_at_open = getattr(app, "_active_theme", theme_module.DEFAULT_THEME)
        self._theme_before_preview = self._theme_at_open
        with self._pause_window_redraw(release_on_exit=False):
            self._refresh_plugin_surface()
        self._show_plugin_window()

    def _initial_slot(self) -> str:
        active = getattr(self.app, "_active_theme", "")
        if active in CUSTOM_THEME_IDS:
            return active
        return CUSTOM_THEME_IDS[0]

    def _window_handle(self, window: tk.Misc) -> int | None:
        try:
            return self.app._window_handle(window)
        except (AttributeError, tk.TclError, ValueError):
            return None

    @contextmanager
    def _pause_window_redraw(self, *, release_on_exit: bool = True):
        handle = self._redraw_handle
        depth = self._redraw_pause_depth
        self._redraw_pause_depth = depth + 1
        if depth == 0 and handle is not None:
            set_window_redraw(handle, False)
        try:
            yield
            if self.win is not None:
                try:
                    self.win.update_idletasks()
                except tk.TclError:
                    pass
        finally:
            self._redraw_pause_depth = depth
            if depth == 0 and release_on_exit and handle is not None:
                set_window_redraw(handle, True)
                redraw_window(handle)

    def _style_base_combo(self) -> None:
        combo = getattr(self, "_base_theme_combo", None)
        win = self.win
        if combo is None or win is None:
            return
        g = globals()
        style = ttk.Style(win)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        family = getattr(self.app.config, "font_family", None) or "Segoe UI"
        size = max(9, int(getattr(self.app.config, "font_size", 10)))
        contrast = self.app._contrast_text(g["ACCENT"]) if hasattr(self.app, "_contrast_text") else g["TEXT"]
        style.configure(
            "ThemeEditor.TCombobox",
            fieldbackground=g["SURFACE_2"],
            background=g["SURFACE"],
            foreground=g["TEXT"],
            arrowcolor=g["TEXT"],
            bordercolor=g["BORDER"],
            lightcolor=g["BORDER"],
            darkcolor=g["BORDER"],
            insertcolor=g["ACCENT"],
            selectbackground=g["ACCENT"],
            selectforeground=contrast,
            font=(family, size),
        )
        style.map(
            "ThemeEditor.TCombobox",
            fieldbackground=[("readonly", g["SURFACE_2"]), ("disabled", g["SURFACE_2"])],
            foreground=[("readonly", g["TEXT"]), ("disabled", g["MUTED"])],
            selectbackground=[("readonly", g["ACCENT"])],
            selectforeground=[("readonly", contrast)],
        )
        try:
            combo.configure(style="ThemeEditor.TCombobox")
        except tk.TclError:
            pass

    def _refresh_plugin_surface(self) -> None:
        self._apply_plugin_colors()
        self._style_base_combo()
        self._refresh_slot_buttons()
        self._refresh_preview_panel()

    def _apply_plugin_colors(self) -> None:
        g = globals()
        win = self.win
        if win is not None:
            try:
                win.configure(bg=g["BG"])
            except tk.TclError:
                pass
        widgets = self._theme_widgets
        for key, widget in widgets.items():
            if key in {"base_combo", "name_entry"}:
                continue
            try:
                if isinstance(widget, tk.Canvas):
                    widget.configure(bg=g["SURFACE"])
                elif isinstance(widget, tk.Frame):
                    if key in {"hero", "editor_card", "preview_card", "colors_inner", "setup_row", "slot_row", "colors_host"}:
                        widget.configure(bg=g["SURFACE"])
                    else:
                        widget.configure(bg=g["BG"])
            except tk.TclError:
                pass
        name_entry = widgets.get("name_entry")
        if isinstance(name_entry, tk.Entry):
            try:
                name_entry.configure(
                    bg=g["SURFACE_2"],
                    fg=g["TEXT"],
                    insertbackground=g["ACCENT"],
                    highlightbackground=g["BORDER"],
                    highlightcolor=g["ACCENT"],
                )
            except tk.TclError:
                pass
        for label, bg, fg in (
            (self.subtitle, g["SURFACE"], g["MUTED"]),
            (self.status, g["BG"], g["MUTED"]),
            (getattr(self, "_hero_title", None), g["SURFACE"], g["TEXT"]),
            (getattr(self, "_colors_heading", None), g["SURFACE"], g["TEXT"]),
            (getattr(self, "_preview_heading", None), g["SURFACE"], g["TEXT"]),
        ):
            if label is not None:
                try:
                    label.configure(bg=bg, fg=fg)
                except tk.TclError:
                    pass
        for label in self._setup_labels:
            try:
                label.configure(bg=g["SURFACE"], fg=g["TEXT_SOFT"])
            except tk.TclError:
                pass
        for label in self._group_labels:
            try:
                label.configure(bg=g["SURFACE"], fg=g["TEXT_SOFT"])
            except tk.TclError:
                pass
        for row, name_label, value_label in self._color_rows:
            try:
                row.configure(bg=g["SURFACE"])
                name_label.configure(bg=g["SURFACE"], fg=g["TEXT"])
                value_label.configure(bg=g["SURFACE"], fg=g["MUTED"])
            except tk.TclError:
                pass
        scroll_track = widgets.get("scroll_track")
        scroll_thumb = widgets.get("scroll_thumb")
        if isinstance(scroll_track, tk.Frame):
            try:
                scroll_track.configure(bg=g["BG"])
            except tk.TclError:
                pass
        if isinstance(scroll_thumb, tk.Frame):
            try:
                scroll_thumb.configure(bg=g["BORDER"])
            except tk.TclError:
                pass
        if self.preview_panel is not None:
            try:
                self.preview_panel.configure(bg=g["BG"], highlightbackground=g["BORDER"])
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
        self._style_base_combo()
        if status is not None and self.status is not None:
            try:
                self.status.configure(text=status, bg=globals()["BG"], fg=globals()["MUTED"])
            except tk.TclError:
                pass
        try:
            win.update_idletasks()
            win.update()
            try:
                win.attributes("-alpha", 0.0)
            except tk.TclError:
                pass
            win.deiconify()
            win.lift()
            win.focus_force()
            win.update_idletasks()
            win.update()
            try:
                win.attributes("-alpha", 1.0)
            except tk.TclError:
                pass
        except tk.TclError:
            if handle is not None:
                set_window_redraw(handle, True)
            return
        if handle is not None:
            set_window_redraw(handle, True)
            redraw_window(handle)

    def _current_palette(self) -> dict[str, str]:
        return normalize_palette({key: var.get() for key, var in self._color_vars.items()})

    def _draft_theme_dict(self) -> dict[str, str]:
        name = self._name_var.get().strip() or t("theme_editor.default_name", index=self._slot_var.get().rsplit("_", 1)[-1])
        return build_theme_palette(self._base_theme_var.get(), self._current_palette(), display_name=name)

    def _sync_swatch(self, key: str) -> None:
        swatch = self._swatches.get(key)
        var = self._color_vars.get(key)
        if swatch is None or var is None:
            return
        color = normalize_hex_color(var.get()) or get_theme(theme_module.DEFAULT_THEME)[key]
        var.set(color)
        swatch.configure(bg=color)
        if not self._suppress_preview_refresh:
            self._refresh_preview_panel()

    def _capture_editor_state(self) -> dict[str, object]:
        return {
            "palette": self._current_palette(),
            "name": self._name_var.get(),
            "base_theme": self._base_theme_combo.get(),
        }

    def _restore_editor_state(self, state: dict[str, object]) -> None:
        palette = normalize_palette(state.get("palette"))
        self._suppress_preview_refresh = True
        try:
            for key, var in self._color_vars.items():
                var.set(palette[key])
        finally:
            self._suppress_preview_refresh = False
        self._name_var.set(str(state.get("name") or ""))
        base_theme = str(state.get("base_theme") or "")
        if base_theme:
            self._base_theme_var.set(base_theme)
        self._refresh_preview_panel()

    def _pick_color(self, key: str) -> None:
        if self.win is None:
            return
        var = self._color_vars[key]
        initial = normalize_hex_color(var.get()) or get_theme(theme_module.DEFAULT_THEME)[key]
        _rgb, chosen = colorchooser.askcolor(color=initial, parent=self.win, title=t("theme_editor.pick_title", name=t(f"theme_editor.color.{key}")))
        if not chosen:
            return
        var.set(normalize_hex_color(chosen))

    def _eyedrop_color(self, key: str) -> None:
        if self.win is None or getattr(self, "_pick_session", None) is not None:
            return
        var = self._color_vars.get(key)
        if var is None:
            return
        try:
            self.win.withdraw()
        except tk.TclError:
            pass

        def finished(result: dict | None) -> None:
            self._pick_session = None
            if result is None:
                self._show_plugin_window(status=t("theme_editor.eyedropper_cancelled"))
                return
            color = normalize_hex_color(result.get("hex")) or var.get()
            var.set(color)
            self._show_plugin_window(
                status=t("theme_editor.eyedropper_done", hex=color, name=t(f"theme_editor.color.{key}"))
            )

        self._pick_session = ScreenColorPickerSession(self.app, finished)

    def _select_slot(self, slot_id: str, *, refresh_preview: bool = True) -> None:
        if slot_id not in CUSTOM_THEME_IDS:
            return
        if self._preview_active:
            self._revert_preview()
            theme_module.THEMES.pop(PREVIEW_THEME_ID, None)
            self._pre_preview_editor = None
        self._slot_var.set(slot_id)
        self._refresh_slot_buttons()
        self._reload_slot_colors(slot_id, refresh_preview=refresh_preview)

    def _reload_slot_colors(self, slot_id: str, *, refresh_preview: bool = True) -> None:
        entry = custom_theme_entry(self.app.config.custom_themes, slot_id)
        self._suppress_preview_refresh = True
        try:
            if entry is not None:
                self._name_var.set(str(entry["name"]))
                palette = normalize_palette(entry.get("palette"))
                for key, var in self._color_vars.items():
                    var.set(palette[key])
                self.status.configure(text=t("theme_editor.loaded_saved", slot=t("theme_editor.slot_label", index=slot_id.rsplit("_", 1)[-1])))
            else:
                self._name_var.set(t("theme_editor.default_name", index=slot_id.rsplit("_", 1)[-1]))
                self._load_from_base_selection(initial=True)
                self.status.configure(text=t("theme_editor.loaded_base"))
        finally:
            self._suppress_preview_refresh = False
        if refresh_preview:
            self._refresh_preview_panel()

    def _refresh_slot_buttons(self) -> None:
        g = globals()
        selected = self._slot_var.get()
        for slot_id, button in self._slot_buttons.items():
            is_selected = slot_id == selected
            button.configure(
                bg=g["SIDEBAR_HOVER"] if is_selected else g["SURFACE"],
                fg=g["TEXT"] if is_selected else g["TEXT_SOFT"],
                highlightbackground=g["ACCENT_2"] if is_selected else g["BORDER"],
                highlightcolor=g["ACCENT_2"] if is_selected else g["BORDER"],
                highlightthickness=2 if is_selected else 1,
            )

    def _load_from_base_selection(self, *, initial: bool = False) -> None:
        display = self._base_theme_combo.get()
        theme_id = theme_module.DEFAULT_THEME
        for candidate in self._base_theme_ids:
            if theme_module.THEMES[candidate]["NAME"] == display:
                theme_id = candidate
                break
        palette = get_theme(theme_id)
        batch = initial or self._suppress_preview_refresh
        if not batch:
            self._suppress_preview_refresh = True
        try:
            for key, var in self._color_vars.items():
                var.set(palette[key])
        finally:
            if not batch:
                self._suppress_preview_refresh = False
        if not initial and not self._name_var.get().strip():
            self._name_var.set(t("theme_editor.default_name", index=self._slot_var.get().rsplit("_", 1)[-1]))
        if not batch:
            self._refresh_preview_panel()

    def _reset_slot(self) -> None:
        if self._preview_active:
            self._revert_preview()
            theme_module.THEMES.pop(PREVIEW_THEME_ID, None)
            if self._pre_preview_editor is not None:
                self._restore_editor_state(self._pre_preview_editor)
                self._pre_preview_editor = None
                self.status.configure(text=t("theme_editor.reset_preview_reverted"))
                return
            self._pre_preview_editor = None
        slot_id = self._slot_var.get()
        if slot_id in CUSTOM_THEME_IDS:
            self._reload_slot_colors(slot_id)
        else:
            self._load_from_base_selection()
        self.status.configure(text=t("theme_editor.reset_done"))

    def _build_preview_widgets(self) -> None:
        panel = self.preview_panel
        if panel is None:
            return
        card = self._theme_widgets.get("preview_card")
        if isinstance(card, tk.Frame):
            card.grid_remove()
        try:
            panel.pack_forget()
            for child in panel.winfo_children():
                child.destroy()
            palette = self._current_palette()
            header = tk.Frame(panel, bg=palette["SURFACE"], height=34)
            header.pack(fill="x")
            header.pack_propagate(False)
            tk.Label(header, text=t("theme_editor.preview.header"), bg=palette["SURFACE"], fg=palette["TEXT"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=10, pady=6)
            content = tk.Frame(panel, bg=palette["BG"])
            content.pack(fill="both", expand=True)
            sidebar = tk.Frame(content, bg=palette["SIDEBAR"], width=72)
            sidebar.pack(side="left", fill="y")
            sidebar.pack_propagate(False)
            tk.Label(sidebar, text=t("theme_editor.preview.sidebar"), bg=palette["SIDEBAR"], fg=palette["SIDEBAR_TEXT"], font=("Segoe UI", 8), wraplength=60, justify="left").pack(padx=8, pady=10)
            main = tk.Frame(content, bg=palette["BG"])
            main.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            tk.Label(main, text=t("theme_editor.preview.body"), bg=palette["BG"], fg=palette["TEXT"], font=("Segoe UI", 10), anchor="w", justify="left").pack(fill="x")
            tk.Label(main, text=t("theme_editor.preview.link"), bg=palette["BG"], fg=palette["LINK"], font=("Segoe UI", 10, "underline"), anchor="w").pack(fill="x", pady=(6, 0))
            code = tk.Label(main, text="code sample", bg=palette["CODE_BG"], fg=palette["CODE_TEXT"], font=("Consolas", 9), anchor="w", padx=8, pady=6)
            code.pack(fill="x", pady=(8, 0))
            actions = tk.Frame(main, bg=palette["BG"])
            actions.pack(fill="x", pady=(10, 0))
            tk.Label(actions, text=t("theme_editor.preview.accent"), bg=palette["ACCENT"], fg=self.app._contrast_text(palette["ACCENT"]), font=("Segoe UI", 9), padx=10, pady=4).pack(side="left", padx=(0, 6))
            tk.Label(actions, text=t("theme_editor.preview.danger"), bg=palette["DANGER"], fg=self.app._contrast_text(palette["DANGER"]), font=("Segoe UI", 9), padx=10, pady=4).pack(side="left")
            panel.update_idletasks()
        finally:
            panel.pack(fill="both", expand=True)
            if isinstance(card, tk.Frame):
                card.grid(row=1, column=1, sticky="nsew")

    def _refresh_preview_panel(self) -> None:
        if self.preview_panel is None:
            return
        with self._pause_window_redraw():
            self._build_preview_widgets()

    def _preview(self) -> None:
        self._pre_preview_editor = self._capture_editor_state()
        if not self._preview_active:
            self._theme_before_preview = getattr(self.app, "_active_theme", theme_module.DEFAULT_THEME)
        theme_module.THEMES[PREVIEW_THEME_ID] = self._draft_theme_dict()
        with self._pause_window_redraw():
            self.app._apply_theme(PREVIEW_THEME_ID)
        self._preview_active = True
        self.status.configure(text=t("theme_editor.preview_applied"))

    def _revert_preview(self) -> None:
        if not self._preview_active:
            return
        revert = self._theme_before_preview
        if revert not in theme_module.THEMES:
            revert = self._theme_at_open if self._theme_at_open in theme_module.THEMES else theme_module.DEFAULT_THEME
        with self._pause_window_redraw():
            self.app._apply_theme(revert)
        self._preview_active = False

    def _save(self) -> None:
        if self.win is None:
            return
        slot_id = self._slot_var.get()
        if slot_id not in CUSTOM_THEME_IDS:
            return
        name = self._name_var.get().strip() or t("theme_editor.default_name", index=slot_id.rsplit("_", 1)[-1])
        palette = self._current_palette()
        if not hasattr(self.app, "_ask_confirmation_dialog"):
            return
        if not self.app._ask_confirmation_dialog(
            t("theme_editor.save_confirm", name=name, slot=t("theme_editor.slot_label", index=slot_id.rsplit("_", 1)[-1])),
            confirm_text=t("theme_editor.save"),
            parent=self.win,
        ):
            return

        entries = [entry for entry in normalize_custom_themes(self.app.config.custom_themes) if str(entry["id"]) != slot_id]
        entries.append({"id": slot_id, "name": name, "palette": palette})
        self.app.config.custom_themes = normalize_custom_themes(entries)
        apply_custom_themes(self.app.config.custom_themes)
        self.app.config.theme = slot_id
        save_config(self.app.config)
        theme_module.THEMES.pop(PREVIEW_THEME_ID, None)
        self.app._apply_theme(slot_id)
        self._preview_active = False
        self._pre_preview_editor = None
        self._theme_before_preview = slot_id
        self.status.configure(text=t("theme_editor.saved", name=name))

    def _cancel(self) -> None:
        if self.win is None:
            return
        if self._pick_session is not None:
            self._pick_session.cancel()
            self._pick_session = None
        self._revert_preview()
        theme_module.THEMES.pop(PREVIEW_THEME_ID, None)
        self.app._theme_editor_open = False
        self.app._theme_editor_window = None
        try:
            self.win.destroy()
        except tk.TclError:
            pass
