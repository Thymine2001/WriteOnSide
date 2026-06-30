from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from ..attachment_index import (
    AttachmentInfo,
    format_file_size,
    matches_filter,
    suffix_category,
)
from ..i18n import t
from ..note_index import is_hidden_relative
from ..platform import redraw_window, reveal_in_file_explorer, set_window_redraw
from ..theme import *  # noqa: F401,F403


def run(app) -> None:
    AttachmentOrganizerWindow(app).open()


def _plugin_button(app, parent: tk.Widget, text: str, command, *, danger: bool = False) -> tk.Button:
    g = globals()
    contrast = app._contrast_text(g["ACCENT"]) if hasattr(app, "_contrast_text") else g["TEXT"]
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=g["DANGER"] if danger else g["BORDER"],
        fg=g["TEXT"],
        activebackground=g["ACCENT"],
        activeforeground=contrast,
        relief="flat",
        padx=12,
        pady=6,
        cursor="hand2",
    )


class AttachmentOrganizerWindow:
    FILTER_KEYS: tuple[str, ...] = ("all", "images", "text", "pdf", "audio", "video", "archives", "other")

    def __init__(self, app) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self.attachments_root: Path | None = None
        self.items: list[AttachmentInfo] = []
        self.filtered_items: list[AttachmentInfo] = []
        self.scanning = False
        self._iid_to_path: dict[str, Path] = {}
        self._filter_key = tk.StringVar(value="all")
        self._search_var = tk.StringVar()
        self._unreferenced_var = tk.BooleanVar(value=False)
        self._theme_widgets: dict[str, object] = {}
        self._filter_buttons: dict[str, tk.Label] = {}

    def open(self) -> None:
        app = self.app
        if getattr(app, "_attachment_organizer_open", False):
            existing = getattr(app, "_attachment_organizer_window", None)
            try:
                if existing is not None and existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return
            except tk.TclError:
                pass
            app._attachment_organizer_open = False

        parent = getattr(app, "_plugin_parent_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = app.root
        except tk.TclError:
            parent = app.root

        g = globals()
        win = tk.Toplevel(parent)
        self.win = win
        app._attachment_organizer_open = True
        app._attachment_organizer_window = win
        win.withdraw()
        win.title(t("attachment_organizer.window_title"))

        work_width = max(420, app.work_right - app.work_left)
        work_height = max(360, app.work_bottom - app.work_top)
        width = min(920, max(560, work_width - 48))
        height = min(780, max(560, work_height - 48))
        x = app.work_left + max(0, (work_width - width) // 2)
        y = app.work_top + max(0, (work_height - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.minsize(min(560, width), min(520, height))
        win.configure(bg=g["BG"])
        try:
            win.transient(parent)
        except tk.TclError:
            pass
        win.resizable(True, True)

        redraw_handle = self._window_handle(win)
        if redraw_handle is not None:
            set_window_redraw(redraw_handle, False)

        footer = tk.Frame(win, bg=g["BG"])
        footer.pack(fill="x", side="bottom", padx=22, pady=(0, 12))
        status = tk.Label(
            footer,
            text=t("attachment_organizer.footer_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        status.pack(fill="x")

        action_bar = tk.Frame(win, bg=g["BG"])
        action_bar.pack(fill="x", side="bottom", padx=22, pady=(0, 8))
        select_unreferenced_btn = _plugin_button(
            app,
            action_bar,
            t("attachment_organizer.select_unreferenced"),
            self.select_unreferenced,
        )
        select_unreferenced_btn.pack(side="left", padx=(0, 8))
        reveal_btn = _plugin_button(app, action_bar, t("attachment_organizer.reveal"), self.reveal_selected)
        reveal_btn.pack(side="left")
        delete_btn = _plugin_button(
            app,
            action_bar,
            t("attachment_organizer.delete_selected"),
            self.delete_selected,
            danger=True,
        )
        delete_btn.pack(side="right")

        body = tk.Frame(win, bg=g["BG"])
        body.pack(fill="both", expand=True, padx=22, pady=(18, 8))

        hero = tk.Frame(body, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"], padx=18, pady=14)
        hero.pack(fill="x", pady=(0, 12))
        tk.Label(hero, text="🗂", bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI Emoji", 28), width=3).pack(
            side="left", padx=(0, 12)
        )
        hero_text = tk.Frame(hero, bg=g["SURFACE"])
        hero_text.pack(side="left", fill="x", expand=True)
        tk.Label(
            hero_text,
            text=t("attachment_organizer.title"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        ).pack(fill="x")
        subtitle = tk.Label(
            hero_text,
            text=t("attachment_organizer.footer_hint"),
            bg=g["SURFACE"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        subtitle.pack(fill="x", pady=(4, 0))

        filter_card = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=14,
            pady=12,
        )
        filter_card.pack(fill="x", pady=(0, 12))
        tk.Label(
            filter_card,
            text=t("attachment_organizer.section.filters"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        filter_row = tk.Frame(filter_card, bg=g["SURFACE"])
        filter_row.pack(fill="x", pady=(0, 8))
        tk.Label(
            filter_row,
            text=t("attachment_organizer.filter"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))
        chip_grid = tk.Frame(filter_row, bg=g["SURFACE"])
        chip_grid.pack(fill="x")
        for column in range(4):
            chip_grid.grid_columnconfigure(column, weight=1, uniform="filter_chip")
        labels = self._filter_labels()
        for index, key in enumerate(self.FILTER_KEYS):
            button = tk.Label(
                chip_grid,
                text=labels[key],
                bg=g["SURFACE"],
                fg=g["TEXT_SOFT"],
                font=("Segoe UI", 9),
                cursor="hand2",
                pady=6,
                padx=4,
                anchor="center",
                highlightthickness=1,
                highlightbackground=g["BORDER"],
            )
            row, column = divmod(index, 4)
            padx = (0, 4) if column % 4 != 3 else (0, 0)
            button.grid(row=row, column=column, sticky="ew", padx=padx, pady=(0, 4))
            button.bind("<Button-1>", lambda _event, value=key: self._set_filter(value))
            self._filter_buttons[key] = button
        self._refresh_filter_chips()

        search_row = tk.Frame(filter_card, bg=g["SURFACE"])
        search_row.pack(fill="x", pady=(0, 8))
        tk.Label(
            search_row,
            text=t("attachment_organizer.search"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10),
            width=10,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        search_entry = tk.Entry(
            search_row,
            textvariable=self._search_var,
            bg=g["SURFACE_2"],
            fg=g["TEXT"],
            insertbackground=g["TEXT"],
            relief="flat",
            font=("Segoe UI", 10),
            highlightthickness=1,
            highlightbackground=g["BORDER"],
        )
        search_entry.grid(row=0, column=1, sticky="ew", ipady=5)
        search_row.grid_columnconfigure(1, weight=1)

        options_row = tk.Frame(filter_card, bg=g["SURFACE"])
        options_row.pack(fill="x")
        unreferenced_check = tk.Checkbutton(
            options_row,
            text=t("attachment_organizer.unreferenced_only"),
            variable=self._unreferenced_var,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            activebackground=g["SURFACE"],
            activeforeground=g["TEXT"],
            selectcolor=g["SURFACE_2"],
            font=("Segoe UI", 10),
            anchor="w",
        )
        unreferenced_check.pack(side="left")
        refresh_btn = _plugin_button(app, options_row, t("attachment_organizer.refresh"), self.start_scan)
        refresh_btn.pack(side="right")

        files_card = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=10,
            pady=10,
        )
        files_card.pack(fill="both", expand=True)
        tk.Label(
            files_card,
            text=t("attachment_organizer.section.files"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        tree_shell = tk.Frame(files_card, bg=g["SURFACE"])
        tree_shell.pack(fill="both", expand=True)
        tree_shell.grid_rowconfigure(0, weight=1)
        tree_shell.grid_columnconfigure(0, weight=1)

        self._style_attachment_tree(app)
        tree = ttk.Treeview(
            tree_shell,
            columns=("type", "size", "status", "refs"),
            show="tree headings",
            selectmode="extended",
            style="AttachmentOrganizer.Treeview",
        )
        tree.heading("#0", text=t("attachment_organizer.column.name"), anchor="w")
        tree.heading("type", text=t("attachment_organizer.column.type"), anchor="w")
        tree.heading("size", text=t("attachment_organizer.column.size"), anchor="e")
        tree.heading("status", text=t("attachment_organizer.column.status"), anchor="w")
        tree.heading("refs", text=t("attachment_organizer.column.refs"), anchor="e")
        tree.column("#0", width=280, minwidth=180, stretch=True)
        tree.column("type", width=96, minwidth=72, stretch=False)
        tree.column("size", width=84, minwidth=64, stretch=False)
        tree.column("status", width=112, minwidth=88, stretch=False)
        tree.column("refs", width=56, minwidth=44, stretch=False)
        tree.grid(row=0, column=0, sticky="nsew")
        tree.tag_configure("folder", foreground=g["TEXT_SOFT"])
        tree.tag_configure("unreferenced", foreground=g["DANGER"])
        tree.tag_configure("referenced", foreground=g["TEXT"])
        tree.bind("<Double-Button-1>", self._open_selected_file)
        tree.bind("<<TreeviewSelect>>", lambda _event: self._update_summary())
        self.tree = tree

        scroll_track = tk.Frame(tree_shell, bg=g["BG"], width=12, cursor="sb_v_double_arrow")
        scroll_track.grid(row=0, column=1, rowspan=2, sticky="ns", padx=(4, 0))
        scroll_track.pack_propagate(False)
        scroll_thumb = tk.Frame(scroll_track, bg=g["BORDER"], width=5, cursor="sb_v_double_arrow")
        drag_state = {"y": 0.0, "first": 0.0}

        h_scroll_track = tk.Frame(tree_shell, bg=g["BG"], height=12, cursor="sb_h_double_arrow")
        h_scroll_track.grid(row=1, column=0, sticky="ew")
        h_scroll_track.pack_propagate(False)
        h_scroll_thumb = tk.Frame(h_scroll_track, bg=g["BORDER"], height=5, cursor="sb_h_double_arrow")
        h_drag_state = {"x": 0.0, "first": 0.0}

        def update_h_scroll_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                h_scroll_thumb.place_forget()
                return
            h_scroll_thumb.place(relx=start, rely=0.5, relwidth=max(0.08, end - start), height=5, anchor="w")

        def h_scroll_to_pointer(event) -> None:
            width = max(1, h_scroll_track.winfo_width())
            tree.xview_moveto(max(0.0, min(1.0, event.x / width)))

        def start_h_thumb_drag(event) -> None:
            first, _last = tree.xview()
            h_drag_state["x"] = event.x_root
            h_drag_state["first"] = first
            h_scroll_thumb.configure(bg=globals()["ACCENT"])

        def drag_h_thumb(event) -> None:
            width = max(1, h_scroll_track.winfo_width())
            delta = (event.x_root - h_drag_state["x"]) / width
            tree.xview_moveto(max(0.0, min(1.0, h_drag_state["first"] + delta)))

        def end_h_thumb_drag(_event) -> None:
            h_scroll_thumb.configure(bg=globals()["BORDER"])

        def update_scroll_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                scroll_thumb.place_forget()
                return
            scroll_thumb.place(relx=0.5, rely=start, relheight=max(0.08, end - start), width=5, anchor="n")

        def scroll_to_pointer(event) -> None:
            height = max(1, scroll_track.winfo_height())
            tree.yview_moveto(max(0.0, min(1.0, event.y / height)))

        def start_thumb_drag(event) -> None:
            first, _last = tree.yview()
            drag_state["y"] = event.y_root
            drag_state["first"] = first
            scroll_thumb.configure(bg=globals()["ACCENT"])

        def drag_thumb(event) -> None:
            height = max(1, scroll_track.winfo_height())
            delta = (event.y_root - drag_state["y"]) / height
            tree.yview_moveto(max(0.0, min(1.0, drag_state["first"] + delta)))

        def end_thumb_drag(_event) -> None:
            scroll_thumb.configure(bg=globals()["BORDER"])

        tree.configure(yscrollcommand=update_scroll_thumb, xscrollcommand=update_h_scroll_thumb)
        scroll_track.bind("<Button-1>", scroll_to_pointer)
        scroll_thumb.bind("<ButtonPress-1>", start_thumb_drag)
        scroll_thumb.bind("<B1-Motion>", drag_thumb)
        scroll_thumb.bind("<ButtonRelease-1>", end_thumb_drag)
        scroll_thumb.bind("<Enter>", lambda _event: scroll_thumb.configure(bg=globals()["ACCENT_2"]))
        scroll_thumb.bind("<Leave>", lambda _event: scroll_thumb.configure(bg=globals()["BORDER"]))
        h_scroll_track.bind("<Button-1>", h_scroll_to_pointer)
        h_scroll_thumb.bind("<ButtonPress-1>", start_h_thumb_drag)
        h_scroll_thumb.bind("<B1-Motion>", drag_h_thumb)
        h_scroll_thumb.bind("<ButtonRelease-1>", end_h_thumb_drag)
        h_scroll_thumb.bind("<Enter>", lambda _event: h_scroll_thumb.configure(bg=globals()["ACCENT_2"]))
        h_scroll_thumb.bind("<Leave>", lambda _event: h_scroll_thumb.configure(bg=globals()["BORDER"]))

        self._theme_widgets = {
            "win": win,
            "footer": footer,
            "action_bar": action_bar,
            "status": status,
            "body": body,
            "hero": hero,
            "hero_text": hero_text,
            "subtitle": subtitle,
            "filter_card": filter_card,
            "files_card": files_card,
            "search_entry": search_entry,
            "unreferenced_check": unreferenced_check,
            "refresh_btn": refresh_btn,
            "select_unreferenced_btn": select_unreferenced_btn,
            "reveal_btn": reveal_btn,
            "delete_btn": delete_btn,
            "scroll_track": scroll_track,
            "scroll_thumb": scroll_thumb,
            "h_scroll_track": h_scroll_track,
            "h_scroll_thumb": h_scroll_thumb,
            "tree": tree,
        }
        self.status = status
        self.subtitle = subtitle
        self.select_unreferenced_btn = select_unreferenced_btn
        self.reveal_btn = reveal_btn
        self.delete_btn = delete_btn

        release_state_done = {"value": False}

        def release_plugin_state() -> None:
            if release_state_done["value"]:
                return
            release_state_done["value"] = True
            self.scanning = False
            app._attachment_organizer_open = False
            if getattr(app, "_attachment_organizer_window", None) is win:
                try:
                    delattr(app, "_attachment_organizer_window")
                except AttributeError:
                    pass
            if getattr(app, "_refresh_attachment_organizer_theme", None) is refresh_theme:
                try:
                    delattr(app, "_refresh_attachment_organizer_theme")
                except AttributeError:
                    pass

        def close() -> None:
            release_plugin_state()
            try:
                win.destroy()
            except tk.TclError:
                pass

        def on_window_destroy(event) -> None:
            if event.widget is win:
                release_plugin_state()

        def refresh_theme() -> None:
            if self.win is None:
                return
            try:
                if not self.win.winfo_exists():
                    return
            except tk.TclError:
                return
            _g = globals()
            self._style_attachment_tree(app)
            for key, widget in self._theme_widgets.items():
                if key in {
                    "tree",
                    "refresh_btn",
                    "select_unreferenced_btn",
                    "reveal_btn",
                    "delete_btn",
                }:
                    continue
                try:
                    if isinstance(widget, tk.Frame):
                        widget.configure(
                            bg=_g["BG"] if widget in {body, action_bar} else _g["SURFACE"]
                        )
                    elif isinstance(widget, tk.Label):
                        parent_bg = widget.master.cget("bg") if widget.master is not None else _g["BG"]
                        widget.configure(bg=parent_bg, fg=_g["MUTED"] if widget is subtitle or widget is status else _g["TEXT"])
                except tk.TclError:
                    pass
            try:
                self.status.configure(fg=_g["MUTED"])
                self.subtitle.configure(fg=_g["MUTED"])
                self.tree.tag_configure("folder", foreground=_g["TEXT_SOFT"])
                self.tree.tag_configure("unreferenced", foreground=_g["DANGER"])
                self.tree.tag_configure("referenced", foreground=_g["TEXT"])
                scroll_track.configure(bg=_g["BG"])
                scroll_thumb.configure(bg=_g["BORDER"])
                h_scroll_track.configure(bg=_g["BG"])
                h_scroll_thumb.configure(bg=_g["BORDER"])
                self._refresh_filter_chips()
            except tk.TclError:
                pass

        app._refresh_attachment_organizer_theme = refresh_theme

        def on_win_configure(_event=None) -> None:
            try:
                status.configure(wraplength=max(220, win.winfo_width() - 44))
                subtitle.configure(wraplength=max(260, win.winfo_width() - 120))
            except tk.TclError:
                pass

        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _event: close())
        win.bind("<Destroy>", on_window_destroy, add="+")
        win.bind("<Configure>", on_win_configure, add="+")

        self._filter_key.trace_add("write", lambda *_args: self.apply_filters())
        self._search_var.trace_add("write", lambda *_args: self.apply_filters())
        self._unreferenced_var.trace_add("write", lambda *_args: self.apply_filters())

        refresh_theme()
        self._finalize_open(redraw_handle)
        self._load_index(force=False)

    def _filter_labels(self) -> dict[str, str]:
        return {key: t(f"attachment_organizer.filter.{key}") for key in self.FILTER_KEYS}

    def _refresh_filter_chips(self) -> None:
        g = globals()
        selected = self._selected_filter_key()
        labels = self._filter_labels()
        for key, button in self._filter_buttons.items():
            is_selected = key == selected
            button.configure(
                text=labels[key],
                bg=g["SIDEBAR_HOVER"] if is_selected else g["SURFACE"],
                fg=g["TEXT"] if is_selected else g["TEXT_SOFT"],
                highlightbackground=g["ACCENT_2"] if is_selected else g["BORDER"],
                highlightcolor=g["ACCENT_2"] if is_selected else g["BORDER"],
                highlightthickness=2 if is_selected else 1,
            )

    def _set_filter(self, key: str) -> None:
        if key not in self.FILTER_KEYS:
            return
        self._filter_key.set(key)
        self._refresh_filter_chips()

    def _style_attachment_tree(self, app) -> None:
        g = globals()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        family = getattr(app.config, "font_family", None) or "Segoe UI"
        size = max(9, int(getattr(app.config, "font_size", 10)) - 1)
        style.configure(
            "AttachmentOrganizer.Treeview",
            background=g["SURFACE"],
            foreground=g["TEXT"],
            fieldbackground=g["SURFACE"],
            borderwidth=0,
            relief="flat",
            font=(family, size),
            rowheight=max(28, 32 + (int(getattr(app.config, "font_size", 10)) - 10) * 2),
            padding=(6, 5),
        )
        style.configure(
            "AttachmentOrganizer.Treeview.Heading",
            background=g["SURFACE_2"],
            foreground=g["TEXT"],
            relief="flat",
            font=(family, size),
            padding=(6, 6),
        )
        style.map(
            "AttachmentOrganizer.Treeview",
            background=[("selected", g["SURFACE_2"])],
            foreground=[("selected", g["TEXT"])],
        )
        try:
            style.layout(
                "AttachmentOrganizer.Treeview.Item",
                [
                    (
                        "Treeitem.padding",
                        {
                            "sticky": "nswe",
                            "children": [
                                ("Treeitem.image", {"side": "left", "sticky": ""}),
                                ("Treeitem.text", {"side": "left", "sticky": "we"}),
                            ],
                        },
                    ),
                ],
            )
        except tk.TclError:
            pass

    def _window_handle(self, window: tk.Misc) -> int | None:
        try:
            return self.app._window_handle(window)
        except (AttributeError, tk.TclError, ValueError):
            return None

    def _finalize_open(self, redraw_handle: int | None) -> None:
        if self.win is None:
            return
        self.win.update_idletasks()
        if redraw_handle is not None:
            set_window_redraw(redraw_handle, True)
            redraw_window(redraw_handle)
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

    def _selected_filter_key(self) -> str:
        key = self._filter_key.get()
        return key if key in self.FILTER_KEYS else "all"

    def _filters_active(self) -> bool:
        return (
            self._selected_filter_key() != "all"
            or bool(self._search_var.get().strip())
            or bool(self._unreferenced_var.get())
        )

    def _load_index(self, *, force: bool) -> None:
        if self.win is None:
            return
        app = self.app
        snapshot = None
        if hasattr(app, "_attachment_index_display_snapshot"):
            snapshot = app._attachment_index_display_snapshot()
        if snapshot is not None and not force:
            root, items, is_current = snapshot
            self._scan_complete(root, items, updating=not is_current)
            if is_current and not getattr(app, "_attachment_index_scanning", False):
                return
        elif force or snapshot is None:
            self._set_scanning_ui(True)
        if hasattr(app, "_request_attachment_index"):
            app._request_attachment_index(self._on_app_index_updated, force=force)
        elif force or snapshot is None:
            self._scan_failed(RuntimeError("Attachment index unavailable"))

    def start_scan(self) -> None:
        if self.scanning or self.win is None:
            return
        self._load_index(force=True)

    def _set_scanning_ui(self, scanning: bool) -> None:
        self.scanning = scanning
        if self.win is None:
            return
        if scanning:
            self.status.configure(text=t("attachment_organizer.scanning"), fg=globals()["MUTED"])
        self.select_unreferenced_btn.configure(state=tk.DISABLED if scanning else tk.NORMAL)
        self.delete_btn.configure(state=tk.DISABLED)
        self.reveal_btn.configure(state=tk.DISABLED if scanning else tk.NORMAL)

    def _on_app_index_updated(
        self,
        root: Path | None,
        items: list[AttachmentInfo],
        error: Exception | None,
    ) -> None:
        if self.win is None:
            return
        if error is not None:
            self._scan_failed(error)
            return
        if root is None:
            return
        self._scan_complete(root, items, updating=False)

    def _scan_failed(self, exc: Exception) -> None:
        self.scanning = False
        if self.win is None:
            return
        self.status.configure(text=t("attachment_organizer.scan_failed", exc=exc), fg=globals()["DANGER"])
        self.select_unreferenced_btn.configure(state=tk.NORMAL)
        self.reveal_btn.configure(state=tk.NORMAL)

    def _scan_complete(self, root: Path, items: list[AttachmentInfo], *, updating: bool = False) -> None:
        self.scanning = updating
        if self.win is None:
            return
        self.attachments_root = root
        self.items = items
        try:
            workspace = self.app._workspace_dir().resolve()
            rel_root = root.relative_to(workspace).as_posix()
        except ValueError:
            rel_root = str(root)
        self.subtitle.configure(
            text=t("attachment_organizer.subtitle", folder=rel_root, count=len(items)),
            wraplength=max(320, self.win.winfo_width() - 120),
        )
        self.apply_filters()
        self.select_unreferenced_btn.configure(state=tk.NORMAL)
        self.reveal_btn.configure(state=tk.NORMAL)
        if updating:
            self.status.configure(text=t("attachment_organizer.updating"), fg=globals()["MUTED"])
        else:
            self.status.configure(text=t("attachment_organizer.footer_hint"), fg=globals()["MUTED"])

    def apply_filters(self) -> None:
        if self.win is None:
            return
        type_key = self._selected_filter_key()
        query = self._search_var.get()
        unreferenced_only = bool(self._unreferenced_var.get())
        self.filtered_items = [
            item
            for item in self.items
            if matches_filter(
                item,
                type_filter=type_key,
                query=query,
                unreferenced_only=unreferenced_only,
            )
        ]
        self._rebuild_tree()
        self._update_summary()

    def _collect_folder_paths(self, file_items: list[AttachmentInfo]) -> set[Path]:
        root = self.attachments_root
        if root is None:
            return set()
        resolved_root = root.resolve()
        folders = {resolved_root}
        if not self._filters_active():
            try:
                for path in root.rglob("*"):
                    if path.is_dir() and not is_hidden_relative(path, root):
                        folders.add(path.resolve())
            except OSError:
                pass
        for item in file_items:
            current = resolved_root
            for part in item.relative.parts[:-1]:
                current = (current / part).resolve()
                folders.add(current)
        return folders

    def _rebuild_tree(self) -> None:
        if self.win is None:
            return
        self.tree.delete(*self.tree.get_children())
        self._iid_to_path.clear()
        if self.attachments_root is None:
            return

        file_items = self.filtered_items if self._filters_active() else self.items
        folders = self._collect_folder_paths(file_items)
        resolved_root = self.attachments_root.resolve()
        folder_iids: dict[Path, str] = {}

        root_iid = str(resolved_root)
        self.tree.insert("", tk.END, iid=root_iid, text=self.attachments_root.name, open=True, tags=("folder",))
        folder_iids[resolved_root] = root_iid

        for folder in sorted(folders, key=lambda path: (len(path.parts), path.as_posix().casefold())):
            if folder == resolved_root:
                continue
            parent_iid = folder_iids.get(folder.parent.resolve())
            if parent_iid is None:
                continue
            folder_iid = str(folder)
            if self.tree.exists(folder_iid):
                continue
            self.tree.insert(
                parent_iid,
                tk.END,
                iid=folder_iid,
                text=folder.name,
                open=True,
                tags=("folder",),
            )
            folder_iids[folder.resolve()] = folder_iid

        labels = self._filter_labels()
        for item in sorted(file_items, key=lambda entry: entry.relative.as_posix().casefold()):
            parent_iid = folder_iids.get(item.path.parent.resolve(), root_iid)
            file_iid = str(item.path.resolve())
            status = (
                t("attachment_organizer.status.referenced")
                if item.referenced
                else t("attachment_organizer.status.unreferenced")
            )
            tag = "referenced" if item.referenced else "unreferenced"
            category = suffix_category(item.suffix)
            type_label = labels.get(category, labels["other"])
            self.tree.insert(
                parent_iid,
                tk.END,
                iid=file_iid,
                text=item.path.name,
                values=(type_label, format_file_size(item.size), status, str(item.reference_count)),
                tags=(tag,),
            )
            self._iid_to_path[file_iid] = item.path

    def _update_summary(self) -> None:
        if self.win is None:
            return
        total = len(self.items)
        visible = len(self.filtered_items)
        unreferenced = sum(1 for item in self.items if not item.referenced)
        visible_unreferenced = sum(1 for item in self.filtered_items if not item.referenced)
        selected = len(self._selected_file_paths())
        self.status.configure(
            text=t(
                "attachment_organizer.summary",
                total=total,
                visible=visible,
                unreferenced=unreferenced,
                visible_unreferenced=visible_unreferenced,
                selected=selected,
            ),
            fg=globals()["MUTED"],
        )
        self.delete_btn.configure(state=tk.NORMAL if selected else tk.DISABLED)

    def _selected_file_paths(self) -> list[Path]:
        if self.win is None:
            return []
        paths: list[Path] = []
        for iid in self.tree.selection():
            path = self._iid_to_path.get(iid)
            if path is not None:
                paths.append(path)
        return paths

    def select_unreferenced(self) -> None:
        if self.win is None:
            return
        targets = [str(item.path.resolve()) for item in self.filtered_items if not item.referenced]
        if not targets:
            return
        self.tree.selection_set(targets)
        self.tree.focus(targets[0])
        self.tree.see(targets[0])
        self._update_summary()

    def reveal_selected(self) -> None:
        paths = self._selected_file_paths()
        if not paths:
            return
        reveal_in_file_explorer(paths[0])

    def _open_selected_file(self, _event=None) -> None:
        paths = self._selected_file_paths()
        if not paths:
            return
        if hasattr(self.app, "_open_external_file"):
            self.app._open_external_file(paths[0], choose_app=False)

    def delete_selected(self) -> None:
        paths = self._selected_file_paths()
        if not paths:
            return
        if not hasattr(self.app, "_ask_confirmation_dialog"):
            return
        if not self.app._ask_confirmation_dialog(
            t("attachment_organizer.delete_confirm", count=len(paths)),
            confirm_text=t("attachment_organizer.delete_selected"),
            danger=True,
            parent=self.win,
        ):
            return
        deleted = 0
        errors: list[str] = []
        deleted_paths = {path.resolve() for path in paths}
        for path in paths:
            try:
                path.unlink()
                deleted += 1
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")
        self.items = [item for item in self.items if item.path.resolve() not in deleted_paths]
        self.apply_filters()
        if errors:
            self.status.configure(
                text=t("attachment_organizer.delete_partial", deleted=deleted, failed=len(errors)),
                fg=globals()["DANGER"],
            )
        else:
            self.status.configure(
                text=t("attachment_organizer.deleted", count=deleted),
                fg=globals()["TEXT"],
            )
