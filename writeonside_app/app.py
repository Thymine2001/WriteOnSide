from __future__ import annotations

import queue
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinterdnd2 import DND_FILES, DND_TEXT, TkinterDnD

from .config import APP_NAME, AppConfig, load_config, save_config
from .frontmatter import NoteMetadata
from .platform import SingleInstanceGuard, enable_per_monitor_dpi, is_startup_enabled
from .theme import *  # noqa: F401,F403

from .ui.theme_utils import ThemeMixin
from .ui.window import WindowMixin
from .ui.tray_manager import TrayMixin
from .ui.editor import EditorMixin
from .ui.image_viewer import ImageViewerMixin
from .ui.command_shortcuts import CommandShortcutsMixin
from .ui.editor_structure import EditorStructureMixin
from .ui.wikilinks_ui import WikiLinksMixin
from .ui.explorer import ExplorerMixin
from .ui.notes import NotesMixin
from .ui.settings import SettingsMixin
from .ui.i18n_ui import I18nMixin


class WriteOnSideApp(
    ThemeMixin,
    WindowMixin,
    TrayMixin,
    EditorMixin,
    ImageViewerMixin,
    CommandShortcutsMixin,
    EditorStructureMixin,
    WikiLinksMixin,
    ExplorerMixin,
    NotesMixin,
    SettingsMixin,
    I18nMixin,
):
    def __init__(self, instance_guard: SingleInstanceGuard | None = None) -> None:
        self.config = load_config()
        self.config.start_on_boot = is_startup_enabled()
        self._init_i18n()
        self._instance_guard = instance_guard
        self._instance_poll_after: str | None = None
        self._set_theme_globals(self.config.theme)
        self.config.auto_close_on_blur = False
        self.config.auto_close_on_escape = False
        self.is_open = False
        self.animating = False
        self._layout_animation_id = 0
        self.view_mode = self.config.view_mode
        self.current_note_path: Path | None = None
        self.preview_path: Path | None = None
        self._document_encoding = "utf-8"
        self._document_newline = "\n"
        self._preview_previous_mode: str | None = None
        self._preview_render_after: str | None = None
        self.explorer_visible = self.config.explorer_open
        self._showing_placeholder = False
        self._ignore_tree_events = False
        self._tree_loaded_dirs: set[str] = set()
        self._explorer_scope: Path | None = None
        self._selected_tags: set[str] = set()
        self._note_metadata: dict[str, NoteMetadata] = {}
        self._tag_counts: dict[str, int] = {}
        self._note_index_mtimes: dict[str, float] = {}
        self._note_index_scope: Path | None = None
        self._tag_refresh_after: str | None = None
        self._explorer_refresh_after: str | None = None
        self._tree_resize_after: str | None = None
        self._sash_indicator: tk.Frame | None = None
        self._pending_explorer_sash_y: int | None = None
        self._active_hotkey = None
        self._autosave_after = None
        self._live_render_after = None
        self._dirty = False
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._settings_open = False
        self._settings_width_sync: Callable[[int, int], None] | None = None
        self._preview_alpha: float | None = None
        self._quick_format_after: str | None = None
        self._read_copy_btn_hide_after: str | None = None
        self._read_copy_btn_block: dict | None = None
        self._active_icon_asset = ""
        self._icon_poll_after: str | None = None
        self._image_viewer_window: tk.Toplevel | None = None
        self._bound_command_sequences: set[str] = set()
        self._width_resize_kind: str | None = None
        self._width_refresh_after: str | None = None
        self._width_drag_after: str | None = None
        self._width_pending_x: int | None = None
        self._width_last_applied: tuple[str, int] | None = None
        self._width_drag_timer_active = False
        self._font_baselines: dict[str, dict[str, object]] = {}
        self._editor_color_tags: set[str] = set()
        self._active_theme: str = self.config.theme
        self._wiki_index_after = None
        self._wiki_completion = None
        self._backlinks_popup = None

        g = globals()
        enable_per_monitor_dpi()
        self.root = TkinterDnD.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config.alpha)
        self.root.configure(bg=g["BG"])
        self._set_window_icon()
        self.root.protocol("WM_DELETE_WINDOW", self.close_panel)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.panel_w = self.config.width
        self.explorer_w = self.config.explorer_width
        self.nav_w = self.config.nav_width
        self._refresh_panel_bounds()
        self.root.geometry(self._panel_geometry(self._closed_panel_x()))
        self.root.withdraw()

        self._build_ui()
        self._setup_nav_bar()
        self._setup_width_resize_handles()
        self._apply_no_taskbar_styles()
        self._apply_typography()
        self._load_initial_note()
        self._register_hotkey()
        self._setup_tray()
        self._poll_system_icon()
        self._poll_instance_activation()
        self._show_nav_bar()
        self._poll_ui_queue()

    def _build_ui(self) -> None:
        g = globals()
        header = tk.Frame(self.root, bg=g["SURFACE"], height=50)
        self.header = header
        header.pack(fill="x")
        header.pack_propagate(False)

        self.menu_btn = self._icon_label(header, "☰", self._toggle_explorer)
        self.menu_btn.pack(side="left", padx=(8, 4))
        self.close_btn = self._icon_label(header, "×", self.close_panel)
        self.close_btn.pack(side="right", padx=(2, 8))
        self.settings_btn = self._icon_label(header, "⚙", self._open_settings)

        title_group = tk.Frame(header, bg=g["SURFACE"], width=1)
        self.title_group = title_group
        title_group.pack(side="left", fill="x", expand=True)
        self.app_title_label = tk.Label(
            title_group,
            text=APP_NAME,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
            width=1,
        )
        self.app_title_label.pack(fill="x")
        self.note_title = tk.Label(
            title_group, text="", bg=g["SURFACE"], fg=g["MUTED"], font=("Segoe UI", 8), anchor="w", width=1
        )
        self.note_title.pack(fill="x")
        self._apply_header_alignment()

        self.toolbar = tk.Frame(self.root, bg=g["SURFACE_2"])
        self.toolbar.pack(fill="x")
        self.toolbar.bind("<Configure>", lambda _e: self._relayout_toolbar())

        self.toolbar_top = tk.Frame(self.toolbar, bg=g["SURFACE_2"])
        self.toolbar_top.pack(fill="x")
        self.toolbar_bottom = tk.Frame(self.toolbar, bg=g["SURFACE_2"])
        self.toolbar_bottom.pack(fill="x")

        self.view_toggle_btn = self._toolbar_btn(self.toolbar_top, "", self._toggle_view_mode)
        self.view_toggle_btn.pack(side="left", padx=(10, 2), pady=6)
        self.toolbar_sep = tk.Frame(self.toolbar_top, bg=g["BORDER"], width=1)
        self.toolbar_sep.pack(side="left", fill="y", padx=8, pady=7)

        self._format_actions = [
            ("frontmatter", "Y", self._ensure_current_front_matter),
            ("bold", "B", lambda: self._wrap_selection("**", "**", "bold")),
            ("italic", "I", lambda: self._wrap_selection("*", "*", "italic")),
            ("underline", "U", lambda: self._wrap_selection("<u>", "</u>", "text")),
            ("strike", "S", lambda: self._wrap_selection("~~", "~~", "text")),
            ("heading", "H", lambda: self._show_heading_popup(self._format_buttons["heading"])),
            ("highlight", "==", lambda: self._wrap_selection("==", "==", "text")),
            ("color", "A", lambda: self._show_text_color_popup(self._format_buttons["color"])),
            ("code", "<>", self._smart_code_format),
            ("quote", "“", lambda: self._line_prefix("> ")),
            ("link", "🔗", lambda: self._wrap_selection("[", "](url)", "text")),
            ("image", "▧", self._insert_image_file),
            ("table", "▦", self._insert_markdown_table),
            ("bullet", "•", lambda: self._apply_list_format("bullet")),
            ("ordered", "1.", lambda: self._apply_list_format("ordered")),
            ("task", "☑", lambda: self._apply_list_format("task")),
            ("divider", "—", lambda: self._insert_text("\n---\n")),
        ]
        self._format_buttons: dict[str, tk.Label] = {}
        self._md_tool_buttons = []
        for key, label, command in self._format_actions:
            btn = self._toolbar_btn(self.toolbar_bottom, label, command)
            if key == "underline":
                btn.configure(font=("Segoe UI", 10, "underline"))
            elif key == "italic":
                btn.configure(font=("Segoe UI", 10, "italic"))
            elif key == "link":
                btn.configure(font=("Segoe UI Emoji", 10))
            elif key == "color":
                btn.configure(font=("Segoe UI", 10, "bold"), fg=g["ACCENT"])
            btn.pack(side="left", padx=1, pady=(0, 6))
            btn._format_key = key
            self._format_buttons[key] = btn
            self._md_tool_buttons.append(btn)
        self.more_format_btn = self._toolbar_btn(
            self.toolbar_bottom,
            "•••",
            lambda: self._show_more_format_popup(self.more_format_btn),
        )

        self.outline_btn = self._toolbar_btn(self.toolbar_top, "☷", self._show_outline_popup)
        self.outline_btn.pack(side="right", padx=2, pady=6)
        self.find_btn = self._toolbar_btn(self.toolbar_top, "", lambda: self._open_find_panel(False))
        self.backlinks_btn = self._toolbar_btn(
            self.toolbar_top,
            "\u21c4",
            self._show_backlinks_popup,
        )
        self.backlinks_btn.pack(side="right", padx=2, pady=6)
        self.find_btn.configure(font=("Segoe MDL2 Assets", 11))
        self.find_btn.pack(side="right", padx=2, pady=6)
        self.save_now_btn = self._toolbar_btn(self.toolbar_top, "💾", lambda: self._save_note(True))
        self.save_now_btn.pack(side="right", padx=(2, 10), pady=6)
        self.new_btn = self._toolbar_btn(self.toolbar_top, "+", self._create_new_note)
        self.new_btn.pack(side="right", padx=2, pady=6)

        tk.Frame(self.root, bg=g["BORDER"], height=1).pack(fill="x")
        self._build_find_panel()

        self.main_body = tk.Frame(self.root, bg=g["BG"])
        self.main_body.pack(fill="both", expand=True)

        self.explorer = tk.Toplevel(self.root)
        self.explorer.overrideredirect(True)
        self.explorer.attributes("-topmost", True)
        self.explorer.attributes("-alpha", self.config.alpha)
        self.explorer.configure(bg=g["SIDEBAR"])
        self.explorer.withdraw()
        self.explorer_frame = tk.Frame(self.explorer, bg=g["SIDEBAR"], width=self.explorer_w)
        self.explorer_frame.pack(fill="both", expand=True)
        self.explorer_frame.pack_propagate(False)
        self._build_explorer()

        self.editor_container = tk.Frame(self.main_body, bg=g["BG"])
        self.content_frame = tk.Frame(self.editor_container, bg=g["BG"])
        self.content_frame.pack(fill="both", expand=True, padx=2)

        self.edit_frame = tk.Frame(self.content_frame, bg=g["BG"])
        self.read_frame = tk.Frame(self.content_frame, bg=g["BG"])
        self.edit_body = tk.Frame(self.edit_frame, bg=g["BG"])
        self.edit_body.pack(fill="both", expand=True)
        self.line_number_canvas = tk.Canvas(
            self.edit_body,
            bg=g["SURFACE"],
            width=52,
            highlightthickness=0,
            borderwidth=0,
            cursor="arrow",
        )
        self.line_number_canvas.pack(side="left", fill="y")
        self.text = tk.Text(
            self.edit_body,
            bg=g["BG"],
            fg=g["TEXT"],
            insertbackground=g["ACCENT"],
            selectbackground=g["ACCENT"],
            selectforeground=self._contrast_text(g["ACCENT"]),
            font=("Segoe UI", 13),
            relief="flat",
            padx=10,
            pady=14,
            wrap="word",
            undo=True,
            exportselection=False,
            spacing1=2,
            spacing3=4,
            borderwidth=0,
            width=1,
            height=1,
        )
        self.text.pack(side="left", fill="both", expand=True)
        self._attach_dark_scrollbar(self.edit_body, self.text)
        self.sticky_heading_frame = tk.Frame(self.edit_frame, bg=g["SURFACE_2"])

        self.read_text = tk.Text(
            self.read_frame,
            bg=g["BG"],
            fg=g["TEXT"],
            selectbackground=g["ACCENT"],
            selectforeground=self._contrast_text(g["ACCENT"]),
            relief="flat",
            padx=8,
            pady=14,
            wrap="char",
            spacing1=2,
            spacing3=4,
            borderwidth=0,
            cursor="arrow",
            width=1,
            height=1,
        )
        self.read_text.pack(side="left", fill="both", expand=True)
        self._attach_dark_scrollbar(self.read_frame, self.read_text)
        self.read_text.bind("<Configure>", self._on_read_view_configure)
        self.read_text.bind("<Key>", self._read_text_key_filter)
        self.read_text.bind("<Motion>", self._on_read_hover)
        self.read_text.bind("<Leave>", lambda _e: self._schedule_copy_btn_hide(300))
        self.read_text.bind("<MouseWheel>", lambda _e: self._hide_code_copy_btn(), add="+")
        self.read_text.bind("<Button-1>", self._on_read_image_click, add="+")
        self._setup_read_copy_btn()

        self.edit_frame.pack(fill="both", expand=True)
        if self.view_mode == "read":
            self.edit_frame.pack_forget()
            self.read_frame.pack(fill="both", expand=True)

        self.text.bind("<<Modified>>", self._on_text_modified)
        self.text.bind("<FocusIn>", lambda _e: self._clear_placeholder())
        self.text.bind("<FocusOut>", lambda _e: self._maybe_show_placeholder())
        self.text.bind("<Return>", self._on_editor_return)
        self.text.bind("<Control-v>", self._paste_from_clipboard)
        self.text.bind("<Control-V>", self._paste_from_clipboard)
        self.text.bind("<Escape>", lambda _e: self._on_escape())
        self.text.bind("<ButtonPress-1>", lambda _e: self._hide_quick_format(), add="+")
        self.text.bind("<ButtonRelease-1>", self._schedule_quick_format, add="+")
        self.text.bind("<KeyRelease>", self._schedule_quick_format, add="+")
        self.text.bind("<MouseWheel>", lambda _e: self._hide_quick_format(), add="+")
        self.text.drop_target_register(DND_FILES, DND_TEXT)
        self.text.dnd_bind("<<Drop>>", self._on_editor_drop)
        self._build_quick_format_toolbar()
        self._setup_editor_structure()
        self._setup_wikilinks()

        tk.Frame(self.root, bg=g["BORDER"], height=1).pack(fill="x")
        footer = tk.Frame(self.root, bg=g["SURFACE"], height=30)
        self.footer = footer
        footer.pack(fill="x")
        footer.pack_propagate(False)
        self.footer_settings_btn = self._footer_action(footer, "⚙", self._open_settings)
        self.footer_settings_btn.pack(side="right", padx=(2, 7), pady=2)
        self.save_indicator = tk.Label(footer, text="", bg=g["SURFACE"], fg=g["ACCENT_2"], font=("Segoe UI", 9, "bold"))
        self.save_indicator.pack(side="right", padx=(4, 2))
        self.status_label = tk.Label(footer, text="", bg=g["SURFACE"], fg=g["MUTED"], font=("Segoe UI", 9), anchor="w", width=1)
        self.status_label.pack(side="left", fill="x", expand=True, padx=(10, 4))

        self.editor_container.pack(side="left", fill="both", expand=True)
        self._update_view_buttons()
        self._relayout_toolbar()
        self._register_command_shortcuts()
        self._update_hotkey_hints()
        self._refresh_header_tooltips()

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _icon_label(self, parent: tk.Widget, text: str, command: Callable[[], None], tooltip: str = "") -> tk.Label:
        g = globals()
        label = tk.Label(parent, text=text, bg=g["SURFACE"], fg=g["MUTED"], font=("Segoe UI", 15), cursor="hand2", width=2, padx=2)
        label._tooltip_text = tooltip
        label.bind("<Button-1>", lambda _e: command())
        label.bind(
            "<Enter>",
            lambda _e: (
                label.config(bg=globals()["SURFACE_2"], fg=globals()["TEXT"]),
                self._show_tooltip(label, getattr(label, "_tooltip_text", tooltip)),
            ),
        )
        label.bind("<Leave>", lambda _e: (label.config(bg=globals()["SURFACE"], fg=globals()["MUTED"]), self._hide_tooltip()))
        return label

    def _footer_action(self, parent: tk.Widget, text: str, command: Callable[[], None], tooltip: str = "") -> tk.Label:
        g = globals()
        label = tk.Label(parent, text=text, bg=g["SURFACE"], fg=g["MUTED"], font=("Segoe UI Emoji", 11), cursor="hand2", width=2, padx=2)
        label._normal_bg = g["SURFACE"]
        label._normal_fg = g["MUTED"]
        label.bind("<Button-1>", lambda _e: command())
        label.bind("<Enter>", lambda _e: (label.config(bg=globals()["SURFACE_2"], fg=globals()["TEXT"]), self._show_tooltip(label, tooltip)))
        label.bind("<Leave>", lambda _e: (label.config(bg=globals()["SURFACE"], fg=globals()["MUTED"]), self._hide_tooltip()))
        return label

    def _small_action(self, parent: tk.Widget, text: str, command: Callable[[], None], tooltip: str = "") -> tk.Label:
        g = globals()
        label = tk.Label(parent, text=text, bg=g["SIDEBAR"], fg=g["SIDEBAR_MUTED"], font=("Segoe UI", 12, "bold"), cursor="hand2", width=2, padx=2)
        label._normal_bg = g["SIDEBAR"]
        label._normal_fg = g["SIDEBAR_MUTED"]
        label.bind("<Button-1>", lambda _e: command())
        label.bind("<Enter>", lambda _e: (label.config(bg=globals()["SIDEBAR_HOVER"], fg=globals()["SIDEBAR_TEXT"]), self._show_tooltip(label, tooltip)))
        label.bind("<Leave>", lambda _e: (label.config(bg=getattr(label, "_normal_bg", globals()["SIDEBAR"]), fg=getattr(label, "_normal_fg", globals()["SIDEBAR_MUTED"])), self._hide_tooltip()))
        return label

    def _toolbar_btn(self, parent: tk.Widget, text: str, command: Callable[[], None], tooltip: str = "") -> tk.Label:
        g = globals()
        btn = tk.Label(parent, text=text, bg=g["SURFACE_2"], fg=g["MUTED"], font=("Segoe UI", 10, "bold"), cursor="hand2", padx=7, pady=2, width=2)
        btn._normal_bg = g["SURFACE_2"]
        btn._normal_fg = g["MUTED"]
        btn._tooltip_text = tooltip
        btn.bind("<Button-1>", lambda _e: command())
        btn.bind("<Enter>", lambda _e: (btn.config(bg=globals()["BORDER"], fg=globals()["TEXT"]), self._show_tooltip(btn, getattr(btn, "_tooltip_text", tooltip))))
        btn.bind("<Leave>", lambda _e: (btn.config(bg=getattr(btn, "_normal_bg", globals()["SURFACE_2"]), fg=getattr(btn, "_normal_fg", globals()["MUTED"])), self._hide_tooltip()))
        return btn

    def _show_tooltip(self, widget: tk.Widget, text: str) -> None:
        self._hide_tooltip()
        if not text or self.animating:
            return
        g = globals()
        tip = tk.Toplevel(widget)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.configure(bg=g["CODE_BG"])
        label = tk.Label(tip, text=text, bg=g["CODE_BG"], fg=g["TEXT"], font=("Segoe UI", 9), padx=8, pady=4)
        label.pack()
        tip.update_idletasks()
        width = max(1, tip.winfo_reqwidth())
        height = max(1, tip.winfo_reqheight())
        x = widget.winfo_rootx() + (widget.winfo_width() - width) // 2
        y = widget.winfo_rooty() + widget.winfo_height() + 6
        if y + height > self.work_bottom - 4:
            y = widget.winfo_rooty() - height - 6
        x = max(self.work_left + 4, min(x, self.work_right - width - 4))
        y = max(self.work_top + 4, min(y, self.work_bottom - height - 4))
        tip.geometry(f"+{x}+{y}")
        self._tooltip = tip

    def _hide_tooltip(self) -> None:
        tip = getattr(self, "_tooltip", None)
        if tip is not None:
            try:
                tip.destroy()
            except tk.TclError:
                pass
            self._tooltip = None

    def _attach_dark_scrollbar(self, parent: tk.Widget, widget: tk.Text) -> tk.Frame:
        g = globals()
        track = tk.Frame(parent, bg=g["BG"], width=10, cursor="sb_v_double_arrow")
        thumb = tk.Frame(track, bg=g["BORDER"], width=4, cursor="sb_v_double_arrow")
        track.pack(side="right", fill="y", padx=(0, 3), pady=4)
        track.pack_propagate(False)

        def update_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                thumb.place_forget()
            else:
                thumb.place(relx=0.5, rely=start, relheight=max(0.06, end - start), width=4, anchor="n")
            if widget is getattr(self, "text", None):
                self._on_editor_scroll()

        def scroll_to_pointer(event) -> None:
            height = max(1, track.winfo_height())
            widget.yview_moveto(max(0.0, min(1.0, event.y / height)))

        drag_state = {"y": 0, "first": 0.0}

        def start_drag(event) -> None:
            first, _last = widget.yview()
            drag_state["y"] = event.y_root
            drag_state["first"] = first
            thumb.config(bg=globals()["ACCENT"])

        def drag(event) -> None:
            height = max(1, track.winfo_height())
            delta = (event.y_root - drag_state["y"]) / height
            widget.yview_moveto(max(0.0, min(1.0, drag_state["first"] + delta)))

        def end_drag(_event) -> None:
            thumb.config(bg=globals()["BORDER"])

        widget.configure(yscrollcommand=update_thumb)
        track.bind("<Button-1>", scroll_to_pointer)
        thumb.bind("<ButtonPress-1>", start_drag)
        thumb.bind("<B1-Motion>", drag)
        thumb.bind("<ButtonRelease-1>", end_drag)
        thumb.bind("<Enter>", lambda _e: thumb.config(bg=globals()["ACCENT_2"]))
        thumb.bind("<Leave>", lambda _e: thumb.config(bg=globals()["BORDER"]))
        return track

    def _relayout_toolbar(self, force: bool = False) -> None:
        if not hasattr(self, "view_toggle_btn"):
            return
        if self._width_resize_kind is not None and not force:
            return
        width = max(self.panel_w, self.toolbar.winfo_width())
        widgets = [
            self.view_toggle_btn,
            self.toolbar_sep,
            *self._md_tool_buttons,
            self.more_format_btn,
            self.outline_btn,
            self.backlinks_btn,
            self.find_btn,
            self.save_now_btn,
            self.new_btn,
        ]
        for widget in widgets:
            try:
                widget.pack_forget()
            except tk.TclError:
                pass
            try:
                widget.grid_forget()
            except tk.TclError:
                pass

        for frame in (self.toolbar_top, self.toolbar_bottom):
            for col in range(max(20, len(self._md_tool_buttons) + 5)):
                frame.grid_columnconfigure(col, weight=0, uniform="")

        top_buttons = [
            self.view_toggle_btn,
            self.outline_btn,
            self.backlinks_btn,
            self.find_btn,
            self.new_btn,
            self.save_now_btn,
        ]
        top_pad = 6 if width >= 360 else 4
        for col, btn in enumerate(top_buttons):
            btn.config(padx=top_pad)
            btn.grid(in_=self.toolbar_top, row=0, column=col, sticky="ew", padx=2, pady=6)
            self.toolbar_top.grid_columnconfigure(col, weight=1, uniform="toolbar_top")

        if self.view_mode == "edit" and self._is_markdown_document():
            if width >= 500:
                visible_count = 11
            elif width >= 440:
                visible_count = 9
            elif width >= 400:
                visible_count = 7
            elif width >= 360:
                visible_count = 5
            else:
                visible_count = 3
            visible_count = min(visible_count, len(self._md_tool_buttons))
            self._visible_format_keys = {
                getattr(button, "_format_key", "")
                for button in self._md_tool_buttons[:visible_count]
            }
            for col, btn in enumerate(self._md_tool_buttons[:visible_count]):
                btn.grid(in_=self.toolbar_bottom, row=0, column=col, sticky="ew", padx=2, pady=(0, 6))
                self.toolbar_bottom.grid_columnconfigure(col, weight=1, uniform="toolbar_bottom")
            self.more_format_btn.grid(
                in_=self.toolbar_bottom,
                row=0,
                column=visible_count,
                sticky="ew",
                padx=2,
                pady=(0, 6),
            )
            self.toolbar_bottom.grid_columnconfigure(visible_count, weight=1, uniform="toolbar_bottom")
        else:
            self._visible_format_keys = set()

    def _refresh_main_layout(self) -> None:
        if not hasattr(self, "toolbar"):
            return
        try:
            self.root.update_idletasks()
            self._relayout_toolbar(force=True)
            self.root.update_idletasks()
        except tk.TclError:
            pass

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()
