from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import messagebox, ttk
from tkinterdnd2 import COPY, DND_FILES

from PIL import Image, ImageDraw, ImageTk

from ..config import APP_NAME, save_config
from ..dragdrop import compact_paths, format_paths_for_drag, local_path_from_drop, split_drop_data
from ..frontmatter import ensure_front_matter
from ..i18n import t
from ..note_index import NoteIndexState, build_note_index, filter_workspace_files
from ..storage import safe_note_name
from ..text_files import is_editable_text_path, is_markdown_note
from ..platform import reveal_in_file_explorer


class ExplorerMixin:
    # ── Explorer build ───────────────────────────────────────────────────────

    def _build_explorer(self) -> None:
        g = globals()
        self.explorer_header = tk.Frame(self.explorer_frame, bg=g["SIDEBAR"], height=44)
        self.explorer_header.pack(fill="x")
        self.explorer_header.pack_propagate(False)
        self.explorer_title = tk.Label(
            self.explorer_header,
            text=t("explorer.files"),
            bg=g["SIDEBAR"],
            fg=g["SIDEBAR_TEXT"],
            font=("Segoe UI", 10, "bold"),
        )
        self.explorer_title.pack(side="left", padx=12)
        self.explorer_new_btn = self._small_action(self.explorer_header, "+", self._create_new_note, "New note")
        self.explorer_new_btn.pack(side="right", padx=(2, 8))
        self.explorer_refresh_btn = self._small_action(self.explorer_header, "↻", self._refresh_explorer, "Refresh files")
        self.explorer_refresh_btn.pack(side="right", padx=2)

        self.explorer_search_outer = tk.Frame(
            self.explorer_frame,
            bg=g["SIDEBAR_BORDER"],
            highlightthickness=1,
            highlightbackground=g["SIDEBAR_BORDER"],
        )
        self.explorer_search_outer.pack(fill="x", padx=10, pady=(2, 9))
        self.explorer_search_wrap = tk.Frame(self.explorer_search_outer, bg=g["SIDEBAR_SURFACE"])
        self.explorer_search_wrap.pack(fill="x", padx=1, pady=1)
        self.explorer_search_icon = tk.Label(
            self.explorer_search_wrap,
            text="",
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_MUTED"],
            font=("Segoe MDL2 Assets", 9),
            width=2,
        )
        self.explorer_search_icon.pack(side="left", padx=(3, 0))
        self.search_var = tk.StringVar()
        self.explorer_search = tk.Entry(
            self.explorer_search_wrap,
            textvariable=self.search_var,
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_TEXT"],
            insertbackground=g["SIDEBAR_TEXT"],
            selectbackground=g["ACCENT"],
            selectforeground=self._contrast_text(g["ACCENT"]),
            relief="flat",
            font=("Segoe UI", 9),
            borderwidth=0,
            highlightthickness=0,
        )
        self.explorer_search.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self.explorer_search_placeholder = tk.Label(
            self.explorer_search_wrap,
            text=t("explorer.search_notes"),
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            cursor="xterm",
        )
        self.explorer_search_placeholder.place(x=31, rely=0.5, anchor="w")
        self.explorer_search_placeholder.bind("<Button-1>", lambda _e: self.explorer_search.focus_set())

        def update_search_state(*_args) -> None:
            if self.search_var.get():
                self.explorer_search_placeholder.place_forget()
            else:
                self.explorer_search_placeholder.place(x=31, rely=0.5, anchor="w")
            self._schedule_explorer_refresh()

        def search_focus(active: bool) -> None:
            color = globals()["ACCENT"] if active else globals()["SIDEBAR_BORDER"]
            self.explorer_search_outer.configure(bg=color, highlightbackground=color)

        self.search_var.trace_add("write", update_search_state)
        self.explorer_search.bind("<FocusIn>", lambda _e: search_focus(True))
        self.explorer_search.bind("<FocusOut>", lambda _e: search_focus(False))

        self.explorer_divider = tk.Frame(self.explorer_frame, bg=g["SIDEBAR_BORDER"], height=1)
        self.explorer_divider.pack(fill="x", padx=10, pady=(0, 4))

        self.explorer_split = tk.PanedWindow(
            self.explorer_frame,
            orient=tk.VERTICAL,
            bg=g["SIDEBAR"],
            sashwidth=1,
            sashpad=0,
            sashrelief="flat",
            borderwidth=0,
            relief="flat",
            showhandle=False,
            opaqueresize=True,
        )
        self.explorer_split.pack(fill="both", expand=True)
        self.explorer_tree_wrap = tk.Frame(self.explorer_split, bg=g["SIDEBAR"])
        self._style_explorer_tree()
        self.file_tree = ttk.Treeview(
            self.explorer_tree_wrap,
            columns=("format",),
            show="tree",
            selectmode="extended",
            style="Explorer.Treeview",
        )
        self.file_tree.column("#0", width=180, minwidth=100, stretch=True)
        self.file_tree.column("format", width=42, minwidth=34, stretch=False, anchor="e")
        self._build_explorer_chevrons()
        self.file_tree.pack(fill="both", expand=True)
        self.file_tree.bind("<<TreeviewOpen>>", self._on_tree_expand)
        self.file_tree.bind("<<TreeviewClose>>", self._on_tree_close)
        self.file_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.file_tree.bind("<Button-1>", self._on_tree_click, add="+")
        self.file_tree.bind("<Button-1>", lambda _e: self.file_tree.focus_set(), add="+")
        self.file_tree.bind("<Double-Button-1>", self._on_tree_double_click)
        self.file_tree.bind("<Button-3>", self._on_tree_context)
        self.file_tree.bind("<Control-c>", self._on_explorer_copy_key, add="+")
        self.file_tree.bind("<Control-x>", self._on_explorer_cut_key, add="+")
        self.file_tree.bind("<Control-v>", self._on_explorer_paste_key, add="+")
        self.file_tree.bind("<Configure>", self._on_file_tree_resize)
        self._explorer_clipboard_paths: list[Path] = []
        self._explorer_clipboard_mode: str | None = None
        self.file_tree.bind("<Shift-MouseWheel>", lambda _e: "break")
        self.file_tree.drop_target_register(DND_FILES)
        self.file_tree.dnd_bind("<<Drop>>", self._on_explorer_drop)
        self.file_tree.drag_source_register(1, DND_FILES)
        self.file_tree.dnd_bind("<<DragInitCmd>>", self._on_explorer_drag_init)
        self.file_tree.tag_configure("folder", foreground=g["SIDEBAR_TEXT"])
        self.file_tree.tag_configure("note", foreground=g["SIDEBAR_TEXT"])
        self.file_tree.tag_configure("attachment", foreground=g["SIDEBAR_MUTED"])
        self.explorer_split.add(self.explorer_tree_wrap, minsize=140, stretch="always")

        self.tag_panel = tk.Frame(self.explorer_split, bg=g["SIDEBAR"])
        self.tag_drag_handle = tk.Frame(self.tag_panel, bg=g["SIDEBAR"], height=10, cursor="sb_v_double_arrow")
        self.tag_drag_handle.pack_propagate(False)
        self.tag_drag_grip = tk.Frame(self.tag_drag_handle, bg=g["SIDEBAR_BORDER"], height=2, width=40)
        self.tag_drag_grip.place(relx=0.5, rely=0.5, anchor="center")
        for target in (self.tag_drag_handle, self.tag_drag_grip):
            target.bind("<ButtonPress-1>", self._start_explorer_sash_drag)
            target.bind("<B1-Motion>", self._drag_explorer_sash)
            target.bind("<ButtonRelease-1>", self._finish_explorer_sash_drag)
        self.tag_header = tk.Frame(self.tag_panel, bg=g["SIDEBAR"], height=34)
        self.tag_header.pack_propagate(False)
        self.tag_title = tk.Label(
            self.tag_header,
            text=t("explorer.tags"),
            bg=g["SIDEBAR"],
            fg=g["SIDEBAR_TEXT"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.tag_title.pack(side="left", fill="y")
        self.tag_scope_label = tk.Label(
            self.tag_header,
            text=t("explorer.all_notes"),
            bg=g["SIDEBAR"],
            fg=g["SIDEBAR_MUTED"],
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.tag_scope_label.pack(side="left", fill="y", padx=(7, 0))
        self.tag_clear_btn = self._small_action(self.tag_header, "×", self._clear_tag_filters, "Clear tag filters")
        self.tag_clear_btn.pack(side="right")

        self.tag_cloud = tk.Text(
            self.tag_panel,
            wrap=tk.NONE,
            bg=g["SIDEBAR"],
            fg=g["SIDEBAR_TEXT"],
            insertbackground=g["SIDEBAR_TEXT"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 9),
            cursor="arrow",
            padx=5,
            pady=2,
            height=1,
            takefocus=False,
            tabs=("24", "210", "235"),
        )
        self.tag_cloud.bind("<Key>", lambda _e: "break")
        self.tag_cloud.bind("<Configure>", lambda _e: self._update_tag_cloud_tabs())

        self.tag_search_outer = tk.Frame(
            self.tag_panel,
            bg=g["SIDEBAR_BORDER"],
            highlightthickness=1,
            highlightbackground=g["SIDEBAR_BORDER"],
        )
        self.tag_search_wrap = tk.Frame(self.tag_search_outer, bg=g["SIDEBAR_SURFACE"])
        self.tag_search_wrap.pack(fill="x", padx=1, pady=1)
        self.tag_search_icon = tk.Label(
            self.tag_search_wrap,
            text="",
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_MUTED"],
            font=("Segoe MDL2 Assets", 9),
            width=2,
        )
        self.tag_search_icon.pack(side="left", padx=(3, 0))
        self.tag_search_var = tk.StringVar()
        self.tag_search = tk.Entry(
            self.tag_search_wrap,
            textvariable=self.tag_search_var,
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_TEXT"],
            insertbackground=g["SIDEBAR_TEXT"],
            selectbackground=g["ACCENT"],
            selectforeground=self._contrast_text(g["ACCENT"]),
            relief="flat",
            font=("Segoe UI", 9),
            borderwidth=0,
            highlightthickness=0,
        )
        self.tag_search_clear = tk.Label(
            self.tag_search_wrap,
            text="\u00d7",
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_MUTED"],
            font=("Segoe UI", 10),
            cursor="hand2",
            width=2,
        )
        self.tag_search_clear.bind("<Button-1>", lambda _e: self.tag_search_var.set(""))
        self.tag_search_clear.bind(
            "<Enter>",
            lambda _e: self.tag_search_clear.configure(fg=globals()["SIDEBAR_TEXT"]),
        )
        self.tag_search_clear.bind(
            "<Leave>",
            lambda _e: self.tag_search_clear.configure(fg=globals()["SIDEBAR_MUTED"]),
        )
        self.tag_search.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        self.tag_search_placeholder = tk.Label(
            self.tag_search_wrap,
            text=t("explorer.filter_tags"),
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            cursor="xterm",
        )
        self.tag_search_placeholder.place(x=31, rely=0.5, anchor="w")
        self.tag_search_placeholder.bind("<Button-1>", lambda _e: self.tag_search.focus_set())

        def update_tag_search(*_args) -> None:
            if self.tag_search_var.get():
                self.tag_search_placeholder.place_forget()
                if not self.tag_search_clear.winfo_ismapped():
                    self.tag_search_clear.pack(side="right", before=self.tag_search, padx=(0, 2))
            else:
                self.tag_search_placeholder.place(x=31, rely=0.5, anchor="w")
                self.tag_search_clear.pack_forget()
            self._render_tag_cloud()

        def tag_search_focus(active: bool) -> None:
            color = globals()["ACCENT"] if active else globals()["SIDEBAR_BORDER"]
            self.tag_search_outer.configure(bg=color, highlightbackground=color)

        self.tag_search_var.trace_add("write", update_tag_search)
        self.tag_search.bind("<FocusIn>", lambda _e: tag_search_focus(True))
        self.tag_search.bind("<FocusOut>", lambda _e: tag_search_focus(False))
        # Grid layout: tag_cloud (row 2) expands; search box (row 3) always gets its space
        self.tag_panel.grid_columnconfigure(0, weight=1)
        self.tag_panel.grid_rowconfigure(2, weight=1)
        self.tag_drag_handle.grid(row=0, column=0, sticky="ew")
        self.tag_header.grid(row=1, column=0, sticky="ew", padx=(10, 6))
        self.tag_cloud.grid(row=2, column=0, sticky="nsew", padx=(5, 3))
        self.tag_search_outer.grid(row=3, column=0, sticky="ew", padx=9, pady=(5, 9))
        self.explorer_split.add(self.tag_panel, minsize=130, stretch="never")
        self.root.after_idle(self._set_initial_explorer_split)
        self._apply_explorer_theme()

    def _apply_explorer_theme(self) -> None:
        if not hasattr(self, "explorer_frame"):
            return
        g = globals()
        self.explorer.configure(bg=g["SIDEBAR"])
        self.explorer_frame.configure(bg=g["SIDEBAR"])
        for widget in (
            getattr(self, "explorer_header", None),
            getattr(self, "explorer_tree_wrap", None),
            getattr(self, "tag_panel", None),
            getattr(self, "tag_header", None),
            getattr(self, "tag_drag_handle", None),
        ):
            if widget is not None:
                widget.configure(bg=g["SIDEBAR"])
        if hasattr(self, "explorer_title"):
            self.explorer_title.configure(bg=g["SIDEBAR"], fg=g["SIDEBAR_TEXT"])
        for button in (
            getattr(self, "explorer_new_btn", None),
            getattr(self, "explorer_refresh_btn", None),
            getattr(self, "tag_clear_btn", None),
        ):
            if button is not None:
                button.configure(bg=g["SIDEBAR"], fg=g["SIDEBAR_MUTED"])
                button._normal_bg = g["SIDEBAR"]
                button._normal_fg = g["SIDEBAR_MUTED"]
        for divider in (getattr(self, "explorer_divider", None),):
            if divider is not None:
                divider.configure(bg=g["SIDEBAR_BORDER"])
        if hasattr(self, "explorer_search_outer"):
            self.explorer_search_outer.configure(
                bg=g["SIDEBAR_BORDER"],
                highlightbackground=g["SIDEBAR_BORDER"],
                highlightcolor=g["ACCENT"],
            )
            self.explorer_search_wrap.configure(bg=g["SIDEBAR_SURFACE"])
            self.explorer_search_icon.configure(bg=g["SIDEBAR_SURFACE"], fg=g["SIDEBAR_MUTED"])
            self.explorer_search.configure(
                bg=g["SIDEBAR_SURFACE"],
                fg=g["SIDEBAR_TEXT"],
                insertbackground=g["SIDEBAR_TEXT"],
                selectbackground=g["ACCENT"],
                selectforeground=self._contrast_text(g["ACCENT"]),
            )
            self.explorer_search_placeholder.configure(bg=g["SIDEBAR_SURFACE"], fg=g["SIDEBAR_MUTED"])
        if hasattr(self, "explorer_split"):
            self.explorer_split.configure(bg=g["SIDEBAR"])
        if hasattr(self, "tag_drag_grip"):
            self.tag_drag_grip.configure(bg=g["SIDEBAR_BORDER"])
        if hasattr(self, "tag_title"):
            self.tag_title.configure(bg=g["SIDEBAR"], fg=g["SIDEBAR_TEXT"])
            self.tag_scope_label.configure(bg=g["SIDEBAR"], fg=g["SIDEBAR_MUTED"])
            self.tag_cloud.configure(
                bg=g["SIDEBAR"],
                fg=g["SIDEBAR_TEXT"],
                insertbackground=g["SIDEBAR_TEXT"],
                selectbackground=g["ACCENT"],
                selectforeground=self._contrast_text(g["ACCENT"]),
            )
        if hasattr(self, "tag_search_outer"):
            self.tag_search_outer.configure(
                bg=g["SIDEBAR_BORDER"],
                highlightbackground=g["SIDEBAR_BORDER"],
                highlightcolor=g["ACCENT"],
            )
            self.tag_search_wrap.configure(bg=g["SIDEBAR_SURFACE"])
            self.tag_search_icon.configure(bg=g["SIDEBAR_SURFACE"], fg=g["SIDEBAR_MUTED"])
            self.tag_search.configure(
                bg=g["SIDEBAR_SURFACE"],
                fg=g["SIDEBAR_TEXT"],
                insertbackground=g["SIDEBAR_TEXT"],
                selectbackground=g["ACCENT"],
                selectforeground=self._contrast_text(g["ACCENT"]),
            )
            self.tag_search_placeholder.configure(bg=g["SIDEBAR_SURFACE"], fg=g["SIDEBAR_MUTED"])
            self.tag_search_clear.configure(bg=g["SIDEBAR_SURFACE"], fg=g["SIDEBAR_MUTED"])
        if hasattr(self, "file_tree"):
            # Item tags override the Treeview style — without this, switching
            # to a light theme leaves the old white text on a light sidebar
            self.file_tree.tag_configure("folder", foreground=g["SIDEBAR_TEXT"])
            self.file_tree.tag_configure("note", foreground=g["SIDEBAR_TEXT"])
            self.file_tree.tag_configure("attachment", foreground=g["SIDEBAR_MUTED"])
            self._build_explorer_chevrons()
            self._refresh_tree_item_images()
            self._style_explorer_tree()
        if hasattr(self, "tag_cloud") and hasattr(self, "_tag_counts"):
            self._render_tag_cloud()

    def _refresh_tree_item_images(self) -> None:
        if not hasattr(self, "file_tree"):
            return

        def visit(parent: str) -> None:
            for item in self.file_tree.get_children(parent):
                if item == "|empty-filter|" or self._is_dummy_id(item):
                    continue
                path = Path(item)
                if path.is_dir():
                    opened = bool(self.file_tree.item(item, "open"))
                    self.file_tree.item(
                        item,
                        image=self._explorer_chevron_open if opened else self._explorer_chevron_closed,
                    )
                else:
                    self.file_tree.item(item, image=self._explorer_chevron_blank)
                visit(item)

        visit("")

    def _build_explorer_chevrons(self) -> None:
        if not hasattr(self, "file_tree"):
            return
        scale = 4
        size = 12
        color = globals()["SIDEBAR_MUTED"]

        def make_chevron(opened: bool) -> ImageTk.PhotoImage:
            img = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            if opened:
                points = [(2.5, 4.0), (6.0, 7.5), (9.5, 4.0)]
            else:
                points = [(4.0, 2.5), (7.5, 6.0), (4.0, 9.5)]
            draw.line(
                [(round(x * scale), round(y * scale)) for x, y in points],
                fill=color,
                width=scale,
                joint="curve",
            )
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)

        blank = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self._explorer_chevron_closed = make_chevron(False)
        self._explorer_chevron_open = make_chevron(True)
        self._explorer_chevron_blank = ImageTk.PhotoImage(blank)

    def _style_explorer_tree(self) -> None:
        g = globals()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        # Use the configured typography — hardcoding the font here would undo
        # the user's font size every time the theme changes
        family = self.config.font_family or "Segoe UI"
        size = max(8, self.config.font_size - 1)
        style.configure(
            "Explorer.Treeview",
            background=g["SIDEBAR"],
            foreground=g["SIDEBAR_TEXT"],
            fieldbackground=g["SIDEBAR"],
            borderwidth=0,
            relief="flat",
            bordercolor=g["SIDEBAR"],
            lightcolor=g["SIDEBAR"],
            darkcolor=g["SIDEBAR"],
            font=(family, size),
            rowheight=max(24, 28 + (self.config.font_size - 10) * 2),
            padding=(4, 2),
        )
        style.map(
            "Explorer.Treeview",
            background=[("selected", g["SIDEBAR_HOVER"])],
            foreground=[("selected", g["SIDEBAR_TEXT"])],
        )
        try:
            style.layout(
                "Explorer.Treeview.Item",
                [
                    (
                        "Treeitem.padding",
                        {
                            "sticky": "nswe",
                            "children": [
                                ("Treeitem.image", {"side": "left", "sticky": ""}),
                                ("Treeitem.text", {"side": "left", "sticky": ""}),
                            ],
                        },
                    ),
                ],
            )
        except tk.TclError:
            pass

    # ── Sash drag ────────────────────────────────────────────────────────────

    def _set_initial_explorer_split(self) -> None:
        if not hasattr(self, "explorer_split"):
            return
        try:
            height = self.explorer_split.winfo_height()
            if height > 320:
                self.explorer_split.sash_place(0, 0, max(170, int(height * 0.64)))
        except tk.TclError:
            pass

    def _clamped_sash_y(self, y: int) -> int:
        height = max(1, self.explorer_split.winfo_height())
        return max(140, min(height - 130, y))

    def _start_explorer_sash_drag(self, event) -> str:
        # Drag moves only a thin indicator line; the sash is applied on release.
        # Live sash_place caused the whole tag panel to relayout each frame (flicker).
        self._pending_explorer_sash_y = event.y_root - self.explorer_split.winfo_rooty()
        self.tag_drag_grip.configure(bg=globals()["ACCENT"])
        if getattr(self, "_sash_indicator", None) is None:
            self._sash_indicator = tk.Frame(self.explorer_split, height=2)
        self._sash_indicator.configure(bg=globals()["ACCENT"])
        self._sash_indicator.place(x=0, relwidth=1.0, y=self._clamped_sash_y(self._pending_explorer_sash_y))
        self._sash_indicator.lift()
        return "break"

    def _drag_explorer_sash(self, event) -> str:
        self._pending_explorer_sash_y = event.y_root - self.explorer_split.winfo_rooty()
        if getattr(self, "_sash_indicator", None) is not None:
            self._sash_indicator.place_configure(y=self._clamped_sash_y(self._pending_explorer_sash_y))
        return "break"

    def _finish_explorer_sash_drag(self, event) -> str:
        self._pending_explorer_sash_y = event.y_root - self.explorer_split.winfo_rooty()
        if getattr(self, "_sash_indicator", None) is not None:
            self._sash_indicator.place_forget()
        target = self._clamped_sash_y(self._pending_explorer_sash_y)
        try:
            self.explorer_split.sash_place(0, 0, target)
        except tk.TclError:
            pass
        self._pending_explorer_sash_y = None
        self.tag_drag_grip.configure(bg=globals()["SIDEBAR_BORDER"])
        return "break"

    # ── Schedule refresh ─────────────────────────────────────────────────────

    def _schedule_explorer_refresh(self) -> None:
        if self._explorer_refresh_after is not None:
            try:
                self.root.after_cancel(self._explorer_refresh_after)
            except tk.TclError:
                pass
        self._explorer_refresh_after = self.root.after(90, lambda: self._refresh_explorer(rebuild_index=False))

    # ── Tag cloud ────────────────────────────────────────────────────────────

    def _tag_scope_root(self) -> Path:
        root = self._workspace_dir().resolve()
        scope = self._explorer_scope
        if scope is None:
            return root
        try:
            resolved = scope.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            self._explorer_scope = None
            return root
        return resolved if resolved.is_dir() else root

    def _first_level_scope(self, path: Path) -> Path:
        root = self._workspace_dir().resolve()
        try:
            relative = path.resolve().relative_to(root)
        except (OSError, ValueError):
            return root
        return root / relative.parts[0] if relative.parts else root

    def _rebuild_tag_index(self, scope: Path | None = None) -> None:
        scope = (scope or self._tag_scope_root()).resolve()
        previous = None
        cached_scope = getattr(self, "_note_index_scope", None)
        if (
            self._note_metadata
            and getattr(self, "_note_index_mtimes", None)
            and cached_scope is not None
            and cached_scope.resolve() == scope
        ):
            previous = NoteIndexState(
                metadata=self._note_metadata,
                tag_counts=self._tag_counts,
                mtimes=self._note_index_mtimes,
            )
        index_state = build_note_index(scope, previous)
        self._note_metadata = index_state.metadata
        self._tag_counts = index_state.tag_counts
        self._note_index_mtimes = index_state.mtimes
        self._note_index_scope = scope
        self._selected_tags.intersection_update(self._tag_counts)
        if hasattr(self, "tag_scope_label"):
            root = self._workspace_dir().resolve()
            self.tag_scope_label.configure(text=t("explorer.all_notes") if scope == root else scope.name)

    def _render_tag_cloud(self) -> None:
        if not hasattr(self, "tag_cloud"):
            return
        g = globals()
        query = self.tag_search_var.get().strip().casefold() if hasattr(self, "tag_search_var") else ""
        tags = [
            (tag, count)
            for tag, count in sorted(self._tag_counts.items(), key=lambda item: (-item[1], item[0].casefold()))
            if not query or query in tag.casefold()
        ]
        self.tag_cloud.configure(state=tk.NORMAL)
        self.tag_cloud.delete("1.0", tk.END)
        if not tags:
            message = t("explorer.no_matching_tags") if query else t("explorer.no_tags_in_folder")
            self.tag_cloud.insert(tk.END, message, "tag_empty")
            self.tag_cloud.tag_configure("tag_empty", foreground=g["SIDEBAR_MUTED"], spacing1=9, lmargin1=9)
        cloud_family = self.config.font_family or "Segoe UI"
        cloud_size = max(8, self.config.font_size - 1)
        for index, (tag, count) in enumerate(tags):
            row_tag = f"tag_item_{index}"
            marker_tag = f"tag_marker_{index}"
            label_tag = f"tag_label_{index}"
            count_tag = f"tag_count_{index}"
            selected = tag in self._selected_tags
            marker = "\u258e" if selected else " "
            self.tag_cloud.insert(tk.END, marker, (row_tag, marker_tag))
            self.tag_cloud.insert(tk.END, f"\t{tag}", (row_tag, label_tag))
            self.tag_cloud.insert(tk.END, f"\t{count}\n", (row_tag, count_tag))
            self.tag_cloud.tag_configure(
                row_tag,
                background=g["SIDEBAR_SURFACE"] if selected else g["SIDEBAR"],
                lmargin1=7,
                lmargin2=7,
                rmargin=7,
                spacing1=5,
                spacing3=5,
            )
            self.tag_cloud.tag_configure(
                marker_tag,
                foreground=g["ACCENT_2"] if selected else g["SIDEBAR"],
                font=("Segoe UI Symbol", cloud_size + 1),
            )
            self.tag_cloud.tag_configure(
                label_tag,
                foreground=g["SIDEBAR_TEXT"],
                font=(cloud_family, cloud_size),
            )
            self.tag_cloud.tag_configure(
                count_tag,
                foreground=g["SIDEBAR_MUTED"],
                font=(cloud_family, max(8, cloud_size - 1)),
            )
            self.tag_cloud.tag_bind(
                row_tag,
                "<Enter>",
                lambda _e, item=row_tag, active=selected: self._set_tag_row_hover(item, True, active),
            )
            self.tag_cloud.tag_bind(
                row_tag,
                "<Leave>",
                lambda _e, item=row_tag, active=selected: self._set_tag_row_hover(item, False, active),
            )
            self.tag_cloud.tag_bind(row_tag, "<Button-1>", lambda _e, value=tag: self._toggle_tag_filter(value))
        self.tag_cloud.configure(state=tk.DISABLED)
        if hasattr(self, "tag_title"):
            selected_count = len(self._selected_tags)
            self.tag_title.configure(text="Tags")
            self.tag_scope_label.configure(
                text=t("explorer.selected_tags", count=selected_count) if selected_count else self._tag_scope_text()
            )
            self.tag_clear_btn.configure(
                fg=g["ACCENT_2"] if selected_count else g["SIDEBAR_MUTED"],
            )
            self.tag_clear_btn._normal_fg = g["ACCENT_2"] if selected_count else g["SIDEBAR_MUTED"]

    def _tag_scope_text(self) -> str:
        scope = self._tag_scope_root().resolve()
        root = self._workspace_dir().resolve()
        return "All notes" if scope == root else scope.name

    def _update_tag_cloud_tabs(self) -> None:
        if not hasattr(self, "tag_cloud"):
            return
        width = max(150, self.tag_cloud.winfo_width())
        self.tag_cloud.configure(tabs=(22, max(105, width - 42)))

    def _set_tag_row_hover(self, tag_id: str, hovered: bool, selected: bool) -> None:
        g = globals()
        self.tag_cloud.configure(cursor="hand2" if hovered else "arrow")
        if selected:
            background = g["SIDEBAR_HOVER"] if hovered else g["SIDEBAR_SURFACE"]
        else:
            background = g["SIDEBAR_SURFACE"] if hovered else g["SIDEBAR"]
        self.tag_cloud.tag_configure(tag_id, background=background)

    def _toggle_tag_filter(self, tag: str) -> str:
        if tag in self._selected_tags:
            self._selected_tags.remove(tag)
        else:
            self._selected_tags.add(tag)
        self._render_tag_cloud()
        self._queue_cached_explorer_refresh()
        return "break"

    def _clear_tag_filters(self) -> None:
        if not self._selected_tags:
            return
        self._selected_tags.clear()
        self._render_tag_cloud()
        self._queue_cached_explorer_refresh()

    def _queue_cached_explorer_refresh(self) -> None:
        if self._explorer_refresh_after is not None:
            try:
                self.root.after_cancel(self._explorer_refresh_after)
            except tk.TclError:
                pass
        self._explorer_refresh_after = self.root.after(1, lambda: self._refresh_explorer(rebuild_index=False))

    def _schedule_tag_refresh(self) -> None:
        if self._tag_refresh_after is not None:
            try:
                self.root.after_cancel(self._tag_refresh_after)
            except tk.TclError:
                pass
        self._tag_refresh_after = self.root.after(180, self._refresh_tag_panel)

    def _refresh_tag_panel(self) -> None:
        self._tag_refresh_after = None
        self._rebuild_tag_index()
        self._render_tag_cloud()
        if self._selected_tags or (hasattr(self, "search_var") and self.search_var.get().strip()):
            self._refresh_explorer(rebuild_index=False)

    # ── Workspace ────────────────────────────────────────────────────────────

    def _workspace_dir(self) -> Path:
        from ..config import AppConfig
        directory = Path(self.config.notes_directory or self.config.obsidian_vault or AppConfig().notes_directory).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _is_in_workspace(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self._workspace_dir().resolve())
            return True
        except ValueError:
            return False

    # ── Refresh explorer ─────────────────────────────────────────────────────

    def _refresh_explorer(self, rebuild_index: bool = True) -> None:
        if not hasattr(self, "file_tree"):
            return
        self._explorer_refresh_after = None
        self._ignore_tree_events = True
        try:
            for item in self.file_tree.get_children(""):
                self.file_tree.delete(item)
            self._tree_loaded_dirs.clear()
            root = self._workspace_dir().resolve()
            scope = self._tag_scope_root()
            if rebuild_index or not self._note_metadata:
                self._rebuild_tag_index(scope)
            self._render_tag_cloud()
            root_id = str(root)
            self.file_tree.insert(
                "",
                tk.END,
                iid=root_id,
                text=self._tree_dir_label(root.name or str(root), True, root),
                image=self._explorer_chevron_open,
                open=True,
                tags=("folder",),
                values=("",),
            )
            query = self.search_var.get().strip().casefold() if hasattr(self, "search_var") else ""
            if query or self._selected_tags:
                self._load_filtered_results(root_id, root, scope, query)
            else:
                self._load_dir_children(root_id, root, force=True)
            self._highlight_current_note()
            self.root.after_idle(self._fit_file_tree_width)
        finally:
            self._ignore_tree_events = False

    def _list_dir_entries(self, directory: Path) -> tuple[list[Path], list[Path]]:
        dirs, files = [], []
        try:
            for entry in directory.iterdir():
                if entry.name.startswith(".") or entry.name.casefold().endswith(".bak"):
                    continue
                if entry.is_dir():
                    dirs.append(entry)
                elif entry.is_file():
                    files.append(entry)
        except OSError:
            return [], []
        return sorted(dirs, key=lambda p: p.name.lower()), sorted(files, key=lambda p: p.name.lower())

    def _on_file_tree_resize(self, _event=None) -> None:
        if getattr(self, "_width_resize_kind", None) is not None:
            return
        if self._tree_resize_after is not None:
            try:
                self.root.after_cancel(self._tree_resize_after)
            except tk.TclError:
                pass
        self._tree_resize_after = self.root.after(45, self._fit_file_tree_width)

    def _explorer_tree_font(self) -> tkfont.Font:
        family = self.config.font_family
        size = max(8, self.config.font_size - 1)
        cache_key = (family, size)
        cached = getattr(self, "_explorer_tree_font_cache", None)
        if cached and cached[0] == cache_key:
            return cached[1]
        font = tkfont.Font(font=(family, size))
        self._explorer_tree_font_cache = (cache_key, font)
        return font

    def _fit_file_tree_width(self) -> None:
        self._tree_resize_after = None
        if not hasattr(self, "file_tree"):
            return
        width = max(150, self.file_tree.winfo_width())
        format_font = self._explorer_tree_font()
        format_labels: list[str] = []

        def collect_formats(parent: str) -> None:
            for item in self.file_tree.get_children(parent):
                values = self.file_tree.item(item, "values")
                if values and values[0]:
                    format_labels.append(str(values[0]))
                collect_formats(item)

        collect_formats("")
        longest_format = max((format_font.measure(value) for value in format_labels), default=28)
        format_width = min(max(44, longest_format + 16), max(44, width - 112))
        self.file_tree.column("format", width=format_width, minwidth=format_width, stretch=False)
        self.file_tree.column("#0", width=max(100, width - format_width - 2), minwidth=80, stretch=False)
        try:
            self.file_tree.xview_moveto(0)
        except tk.TclError:
            pass
        self._refresh_file_tree_labels()

    def _refresh_file_tree_labels(self) -> None:
        if not hasattr(self, "file_tree"):
            return

        def visit(parent: str) -> None:
            for item in self.file_tree.get_children(parent):
                if item != "|empty-filter|" and not self._is_dummy_id(item):
                    path = Path(item)
                    if path.is_file():
                        self.file_tree.item(item, text=self._file_tree_label(path))
                    elif path.is_dir():
                        self.file_tree.item(
                            item,
                            text=self._tree_dir_label(path.name or str(path), bool(self.file_tree.item(item, "open")), path),
                        )
                visit(item)

        visit("")

    def _file_tree_label(self, path: Path) -> str:
        suffix_text = "".join(path.suffixes)
        name = path.name[:-len(suffix_text)] if suffix_text else path.name
        return self._truncate_tree_label(name, path)

    def _truncate_tree_label(self, name: str, path: Path) -> str:
        if not hasattr(self, "file_tree"):
            return name
        try:
            root = self._workspace_dir().resolve()
            depth = max(0, len(path.resolve().relative_to(root).parts) - 1)
        except (OSError, ValueError):
            depth = 0
        tree_width = int(self.file_tree.column("#0", "width"))
        available = max(34, tree_width - 24 - depth * 20)
        font = self._explorer_tree_font()
        if font.measure(name) <= available:
            return name
        ellipsis = "..."
        available -= font.measure(ellipsis)
        if available <= 0:
            return ellipsis
        low, high = 0, len(name)
        while low < high:
            middle = (low + high + 1) // 2
            if font.measure(name[:middle]) <= available:
                low = middle
            else:
                high = middle - 1
        return name[:low].rstrip() + ellipsis

    def _file_format_label(self, path: Path) -> str:
        suffixes = [suffix.lstrip(".") for suffix in path.suffixes if suffix]
        return ".".join(suffixes).upper()

    def _load_filtered_results(self, root_id: str, root: Path, scope: Path, query: str) -> None:
        matches = filter_workspace_files(scope, query, self._selected_tags, self._note_metadata)
        inserted_dirs = {root.resolve(): root_id}

        def ensure_directory(path: Path) -> str:
            path = path.resolve()
            existing = inserted_dirs.get(path)
            if existing:
                return existing
            parent_id = ensure_directory(path.parent)
            iid = str(path)
            if not self.file_tree.exists(iid):
                self.file_tree.insert(
                    parent_id,
                    tk.END,
                    iid=iid,
                    text=self._tree_dir_label(path.name, True, path),
                    image=self._explorer_chevron_open,
                    open=True,
                    tags=("folder",),
                    values=("",),
                )
            inserted_dirs[path] = iid
            return iid

        for path in sorted(matches, key=lambda item: str(item.relative_to(root)).casefold()):
            parent_id = ensure_directory(path.parent)
            iid = str(path)
            if not self.file_tree.exists(iid):
                self.file_tree.insert(
                    parent_id,
                    tk.END,
                    iid=iid,
                    text=self._file_tree_label(path),
                    image=self._explorer_chevron_blank,
                    tags=("note",),
                    values=(self._file_format_label(path),),
                )
        if not matches:
            self.file_tree.insert(root_id, tk.END, iid="|empty-filter|", text=t("explorer.no_matching_files"))

    def _tree_dir_label(self, name: str, opened: bool = False, path: Path | None = None) -> str:
        return self._truncate_tree_label(name, path) if path is not None else name

    def _update_tree_dir_label(self, item: str, opened: bool) -> None:
        try:
            path = Path(item)
            if path.is_dir():
                self.file_tree.item(
                    item,
                    text=self._tree_dir_label(path.name or str(path), opened, path),
                    image=self._explorer_chevron_open if opened else self._explorer_chevron_closed,
                )
        except (OSError, tk.TclError):
            pass

    def _dummy_id(self, directory: Path) -> str:
        return str(directory) + "|dummy"

    def _is_dummy_id(self, iid: str) -> bool:
        return str(iid).endswith("|dummy")

    def _load_dir_children(self, parent_id: str, directory: Path, force: bool = False) -> None:
        directory = directory.resolve()
        directory_id = str(directory)
        if directory_id in self._tree_loaded_dirs and not force:
            return
        for child in self.file_tree.get_children(parent_id):
            if self._is_dummy_id(child):
                self.file_tree.delete(child)
        dirs, files = self._list_dir_entries(directory)
        for item in dirs[:300]:
            iid = str(item.resolve())
            if not self.file_tree.exists(iid):
                self.file_tree.insert(
                    parent_id,
                    tk.END,
                    iid=iid,
                    text=self._tree_dir_label(item.name, False, item),
                    image=self._explorer_chevron_closed,
                    open=False,
                    tags=("folder",),
                    values=("",),
                )
                self.file_tree.insert(iid, tk.END, iid=self._dummy_id(item.resolve()), text="")
        for item in files[:300]:
            iid = str(item.resolve())
            if not self.file_tree.exists(iid):
                item_tag = "note" if item.suffix.lower() == ".md" else "attachment"
                self.file_tree.insert(
                    parent_id,
                    tk.END,
                    iid=iid,
                    text=self._file_tree_label(item),
                    image=self._explorer_chevron_blank,
                    tags=(item_tag,),
                    values=(self._file_format_label(item),),
                )
        self._tree_loaded_dirs.add(directory_id)

    # ── Tree event handlers ──────────────────────────────────────────────────

    def _on_tree_expand(self, _event) -> None:
        item = self.file_tree.focus()
        if item and not self._is_dummy_id(item):
            path = Path(item)
            if path.is_dir():
                self._load_dir_children(item, path)
                self._update_tree_dir_label(item, True)

    def _on_tree_close(self, _event) -> None:
        item = self.file_tree.focus()
        if item and not self._is_dummy_id(item):
            self._update_tree_dir_label(item, False)

    def _on_tree_click(self, event):
        item = self.file_tree.identify_row(event.y)
        if not item or item == "|empty-filter|" or self._is_dummy_id(item):
            return None
        path = Path(item)
        if not path.is_dir():
            return None
        if event.state & 0x4 or event.state & 0x1:
            return None
        self.file_tree.selection_set(item)
        self.file_tree.focus(item)
        opened = bool(self.file_tree.item(item, "open"))
        if not opened:
            self._load_dir_children(item, path)
        self.file_tree.item(item, open=not opened)
        self._update_tree_dir_label(item, not opened)
        return "break"

    def _on_tree_select(self, _event) -> None:
        if self._ignore_tree_events:
            return
        selected = self.file_tree.selection()
        if not selected:
            return
        if len(selected) > 1:
            return
        if selected[0] == "|empty-filter|" or self._is_dummy_id(selected[0]):
            return
        path = Path(selected[0])
        if path.is_dir():
            scope = self._first_level_scope(path)
            if scope != self._tag_scope_root():
                self._explorer_scope = scope
                self._rebuild_tag_index(scope)
                self._render_tag_cloud()
                if self._selected_tags or self.search_var.get().strip():
                    self.root.after_idle(lambda: self._refresh_explorer(rebuild_index=False))
            return
        if not path.is_file():
            return
        if is_markdown_note(path):
            self.root.after_idle(lambda p=path: self._open_note_from_tree(p))
        elif is_editable_text_path(path):
            self.root.after_idle(lambda p=path: self._open_text_file_from_tree(p))
        else:
            self.root.after_idle(lambda p=path: self._preview_explorer_file(p))

    def _on_tree_double_click(self, event) -> None:
        item = self.file_tree.identify_row(event.y)
        if not item or self._is_dummy_id(item):
            return
        path = Path(item)
        if path.is_dir():
            return "break"
        elif path.is_file():
            if is_markdown_note(path):
                self._open_note_from_tree(path)
            elif is_editable_text_path(path):
                self._open_text_file_from_tree(path)
            else:
                self._open_external_file(path)

    # ── Explorer clipboard & file actions ────────────────────────────────────

    def _explorer_selected_paths(self) -> list[Path]:
        root = self._workspace_dir().resolve()
        paths: list[Path] = []
        for item in self.file_tree.selection():
            if item == "|empty-filter|" or self._is_dummy_id(item):
                continue
            path = Path(item)
            if not path.exists() or not self._is_in_workspace(path):
                continue
            if path.resolve() == root:
                continue
            paths.append(path)
        return compact_paths(paths)

    def _on_explorer_drag_init(self, event):
        paths = self._explorer_selected_paths()
        if not paths:
            item = self.file_tree.identify_row(event.y)
            if item and item != "|empty-filter|" and not self._is_dummy_id(item):
                path = Path(item)
                if path.exists() and self._is_in_workspace(path) and path.resolve() != self._workspace_dir().resolve():
                    paths = [path]
        data = format_paths_for_drag(paths)
        if not data:
            return "break"
        return (COPY, DND_FILES, data)

    def _explorer_paste_destination(self, item: str | None = None) -> Path:
        if item and item != "|empty-filter|" and not self._is_dummy_id(item):
            path = Path(item)
            if path.is_dir():
                return path
            if path.is_file():
                return path.parent
        return self._workspace_dir()

    def _path_is_descendant(self, ancestor: Path, descendant: Path) -> bool:
        try:
            descendant.resolve().relative_to(ancestor.resolve())
            return True
        except ValueError:
            return False

    def _copy_paths_to_clipboard(self, paths: list[Path]) -> None:
        if not paths:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(str(path.resolve()) for path in paths))
        if len(paths) == 1:
            self._set_status_key("status.path_copied")
        else:
            self._set_status_key("status.paths_copied", count=len(paths))

    def _copy_path_to_clipboard(self, path: Path) -> None:
        self._copy_paths_to_clipboard([path])

    def _explorer_reveal(self, path: Path) -> None:
        try:
            reveal_in_file_explorer(path)
        except OSError as exc:
            self._set_error(t("error.reveal_failed", exc=exc))

    def _explorer_reveal_selection(self, paths: list[Path]) -> None:
        for path in paths:
            self._explorer_reveal(path)

    def _explorer_set_clipboard(self, paths: list[Path], mode: str) -> None:
        self._explorer_clipboard_paths = [path.resolve() for path in paths]
        self._explorer_clipboard_mode = mode
        if mode == "cut":
            self._set_status_key("status.explorer_cut", count=len(paths))
        else:
            self._set_status_key("status.explorer_copied", count=len(paths))

    def _explorer_cut(self) -> None:
        paths = self._explorer_selected_paths()
        if paths:
            self._explorer_set_clipboard(paths, "cut")

    def _explorer_copy(self) -> None:
        paths = self._explorer_selected_paths()
        if paths:
            self._explorer_set_clipboard(paths, "copy")

    def _note_paths_after_relocate(self, mapping: dict[Path, Path]) -> None:
        for old_path, new_path in mapping.items():
            if self.current_note_path and self.current_note_path.resolve() == old_path.resolve():
                self.current_note_path = new_path
                self.config.current_note_path = str(new_path) if is_markdown_note(new_path) else ""
                self._update_note_title()
            if getattr(self, "preview_path", None) and self.preview_path.resolve() == old_path.resolve():
                self.preview_path = new_path

    def _move_into_explorer(self, source: Path, destination: Path) -> Path:
        import shutil

        source = source.resolve()
        destination = destination.resolve()
        if source == destination:
            return source
        if source.parent == destination:
            return source
        if source.is_dir():
            if source == destination or self._path_is_descendant(source, destination):
                raise OSError("A folder cannot be moved into itself.")
        target = destination / source.name
        if target.exists():
            raise OSError(f"{source.name} already exists in this folder.")
        shutil.move(str(source), str(target))
        return target

    def _explorer_paste(self, item: str | None = None) -> None:
        if not self._explorer_clipboard_paths or not self._explorer_clipboard_mode:
            return
        destination = self._explorer_paste_destination(item)
        if not self._is_in_workspace(destination):
            self._set_error(t("error.explorer_paste_failed", exc=t("error.explorer_outside_workspace")))
            return
        relocated: dict[Path, Path] = {}
        pasted = 0
        errors: list[str] = []
        mode = self._explorer_clipboard_mode
        sources = list(self._explorer_clipboard_paths)
        for source in sources:
            if not source.exists():
                continue
            try:
                if mode == "cut":
                    target = self._move_into_explorer(source, destination)
                else:
                    target = self._copy_into_explorer(source, destination)
                relocated[source.resolve()] = target.resolve()
                pasted += 1
            except OSError as exc:
                errors.append(str(exc))
        if relocated:
            self._note_paths_after_relocate(relocated)
        if mode == "cut" and pasted:
            self._explorer_clipboard_paths = []
            self._explorer_clipboard_mode = None
        if pasted:
            self._refresh_explorer()
            self._schedule_wiki_index_refresh()
            self._set_status_key("status.explorer_pasted", count=pasted)
        elif errors:
            self._set_error(t("error.explorer_paste_failed", exc=errors[0]))

    def _delete_explorer_item(self, path: Path) -> None:
        import shutil

        if path.is_dir():
            if not messagebox.askyesno(APP_NAME, t("dialog.delete_folder", name=path.name)):
                return
            try:
                shutil.rmtree(path)
            except OSError as exc:
                self._set_error(t("error.delete_failed", exc=exc))
                return
        else:
            self._delete_note(path)
            return
        self._after_explorer_tree_delete(path)
        self._refresh_explorer()
        self._schedule_wiki_index_refresh()

    def _after_explorer_tree_delete(self, path: Path) -> None:
        if self.current_note_path:
            try:
                self.current_note_path.resolve().relative_to(path.resolve())
                self.current_note_path = None
                self._load_initial_note()
            except ValueError:
                pass
        if getattr(self, "preview_path", None):
            try:
                self.preview_path.resolve().relative_to(path.resolve())
                self._close_file_preview(restore_note=True)
            except ValueError:
                pass

    def _delete_explorer_selection(self) -> None:
        paths = self._explorer_selected_paths()
        if not paths:
            return
        if len(paths) == 1:
            self._delete_explorer_item(paths[0])
            return
        if not messagebox.askyesno(APP_NAME, t("dialog.delete_items", count=len(paths))):
            return
        deleted = 0
        for path in paths:
            try:
                if path.is_dir():
                    import shutil

                    shutil.rmtree(path)
                else:
                    path.unlink()
                self._after_explorer_tree_delete(path)
                deleted += 1
            except OSError as exc:
                self._set_error(t("error.delete_failed", exc=exc))
                break
        if deleted:
            if self.current_note_path and not self.current_note_path.exists():
                self.current_note_path = None
                self._load_initial_note()
            self._refresh_explorer()
            self._schedule_wiki_index_refresh()

    def _on_explorer_copy_key(self, _event) -> str | None:
        if self.file_tree.focus_get() is not self.file_tree:
            return None
        self._explorer_copy()
        return "break"

    def _on_explorer_cut_key(self, _event) -> str | None:
        if self.file_tree.focus_get() is not self.file_tree:
            return None
        self._explorer_cut()
        return "break"

    def _on_explorer_paste_key(self, _event) -> str | None:
        if self.file_tree.focus_get() is not self.file_tree:
            return None
        item = self.file_tree.focus() or (self.file_tree.selection()[0] if self.file_tree.selection() else None)
        self._explorer_paste(item)
        return "break"

    def _on_tree_context(self, event) -> None:
        g = globals()
        item = self.file_tree.identify_row(event.y)
        if item and item != "|empty-filter|" and not self._is_dummy_id(item):
            if item not in self.file_tree.selection():
                self.file_tree.selection_set(item)
            self.file_tree.focus(item)
        paths = self._explorer_selected_paths()
        single_path = paths[0] if len(paths) == 1 else None
        has_selection = bool(paths)
        is_file = bool(single_path and single_path.is_file())
        can_rename = len(paths) == 1
        paste_state = tk.NORMAL if self._explorer_clipboard_paths else tk.DISABLED
        menu = tk.Menu(
            self.root,
            tearoff=False,
            bg=g["SIDEBAR_SURFACE"],
            fg=g["SIDEBAR_TEXT"],
            activebackground=g["SIDEBAR_HOVER"],
            activeforeground=g["TEXT"],
            font=("Segoe UI", 10),
        )
        menu.add_command(label=t("explorer.menu.new_note"), command=self._create_new_note)
        menu.add_separator()
        menu.add_command(
            label=t("explorer.menu.cut"),
            command=self._explorer_cut,
            state=tk.NORMAL if has_selection else tk.DISABLED,
        )
        menu.add_command(
            label=t("explorer.menu.copy"),
            command=self._explorer_copy,
            state=tk.NORMAL if has_selection else tk.DISABLED,
        )
        menu.add_command(
            label=t("explorer.menu.paste"),
            command=lambda: self._explorer_paste(item),
            state=paste_state,
        )
        menu.add_separator()
        menu.add_command(
            label=t("explorer.menu.copy_path"),
            command=lambda: self._copy_paths_to_clipboard(paths),
            state=tk.NORMAL if has_selection else tk.DISABLED,
        )
        menu.add_command(
            label=t("explorer.menu.reveal"),
            command=lambda: self._explorer_reveal_selection(paths),
            state=tk.NORMAL if has_selection else tk.DISABLED,
        )
        if has_selection:
            menu.add_separator()
            if is_file and single_path is not None:
                if is_editable_text_path(single_path) and not is_markdown_note(single_path):
                    menu.add_command(
                        label=t("explorer.menu.edit"),
                        command=lambda: self._open_text_file_from_tree(single_path),
                    )
                elif not is_markdown_note(single_path):
                    menu.add_command(
                        label=t("explorer.menu.preview"),
                        command=lambda: self._preview_explorer_file(single_path),
                    )
                menu.add_command(
                    label=t("explorer.menu.open_external"),
                    command=lambda: self._open_external_file(single_path),
                )
            if can_rename and single_path is not None:
                menu.add_command(
                    label=t("explorer.menu.rename"),
                    command=lambda: self._rename_note(single_path),
                )
            menu.add_command(
                label=t("explorer.menu.delete"),
                command=self._delete_explorer_selection,
            )
        menu.add_separator()
        menu.add_command(label=t("explorer.menu.refresh"), command=self._refresh_explorer)
        menu.tk_popup(event.x_root, event.y_root)

    # ── Drop into explorer ───────────────────────────────────────────────────

    def _explorer_drop_directory(self) -> Path:
        local_y = self.file_tree.winfo_pointery() - self.file_tree.winfo_rooty()
        item = self.file_tree.identify_row(local_y)
        if not item or self._is_dummy_id(item):
            return self._workspace_dir()
        path = Path(item)
        return path if path.is_dir() else path.parent

    def _unique_copy_path(self, directory: Path, name: str) -> Path:
        target = directory / name
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        for number in range(1, 10000):
            candidate = directory / f"{stem} ({number}){suffix}"
            if not candidate.exists():
                return candidate
        raise OSError(f"Unable to create a unique copy of {name}.")

    def _copy_into_explorer(self, source: Path, destination: Path) -> Path:
        import shutil
        source = source.resolve()
        destination = destination.resolve()
        if source.parent == destination:
            raise OSError(f"{source.name} is already in this folder.")
        if source.is_dir():
            try:
                destination.relative_to(source)
            except ValueError:
                pass
            else:
                raise OSError("A folder cannot be copied into itself.")
        target = self._unique_copy_path(destination, source.name)
        if source.is_dir():
            shutil.copytree(source, target)
            for note in target.rglob("*.md"):
                self._ensure_imported_note_template(note)
        else:
            shutil.copy2(source, target)
            if target.suffix.lower() == ".md":
                self._ensure_imported_note_template(target)
        return target

    def _ensure_imported_note_template(self, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            return
        updated, created = ensure_front_matter(content, path.stem)
        if not created:
            return
        try:
            path.write_text(updated, encoding="utf-8", newline="\n")
        except OSError:
            pass

    def _on_explorer_drop(self, event):
        destination = self._explorer_drop_directory()
        copied = 0
        errors: list[str] = []
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._set_error(t("error.drop_failed", exc=exc))
            return getattr(event, "action", None)
        for value in split_drop_data(self.file_tree, event.data):
            source = local_path_from_drop(value)
            if source is None or not source.exists():
                continue
            try:
                self._copy_into_explorer(source, destination)
                copied += 1
            except OSError as exc:
                errors.append(str(exc))
        if copied:
            self._refresh_explorer()
            self._schedule_wiki_index_refresh()
            self._set_status_key("status.copied_items", count=copied)
        elif errors:
            self._set_error(t("error.drop_failed", exc=errors[0]))
        else:
            self._set_error(t("error.no_local_files"))
        return getattr(event, "action", None)

    # ── Toggle explorer ──────────────────────────────────────────────────────

    def _toggle_explorer(self) -> None:
        self.explorer_visible = not self.explorer_visible
        self.config.explorer_open = self.explorer_visible
        if self.explorer_visible:
            self._refresh_explorer()
        if self.is_open:
            self._place_layout(True)
            if self.explorer_visible:
                self.explorer.lift()
                self.root.lift()
            self._raise_nav_bar()
            self._refresh_nav_bar_visual()
        else:
            self._position_nav_bar()
            self._raise_nav_bar()
            self._refresh_nav_bar_visual()
        save_config(self.config)
