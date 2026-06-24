from __future__ import annotations

import importlib
import tkinter as tk

from ..i18n import t
from ..platform import show_window_in_taskbar
from ..plugins import enabled_plugins
from ..theme import *  # noqa: F401,F403


class PluginsMixin:
    def _run_plugin_entrypoint(self, entrypoint: str) -> None:
        module_name, _, function_name = entrypoint.partition(":")
        if not module_name or not function_name:
            return
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        parent = None
        state = getattr(self, "_plugin_window_state", None)
        if state:
            parent = state.get("window")
        try:
            if parent is not None and parent.winfo_exists():
                self._plugin_parent_window = parent
        except tk.TclError:
            pass
        function(self)

    def _open_plugins(self) -> None:
        if getattr(self, "_plugins_open", False):
            return
        self._plugins_open = True
        g = globals()
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.title(t("plugins.window_title"))

        work_width = max(320, self.work_right - self.work_left)
        work_height = max(320, self.work_bottom - self.work_top)
        plugins_w = min(760, max(320, work_width - 48))
        plugins_h = min(520, max(300, work_height - 72))
        plugins_x = self.work_left + max(0, (work_width - plugins_w) // 2)
        plugins_y = self.work_top + max(0, (work_height - plugins_h) // 2)
        win.geometry(f"{plugins_w}x{plugins_h}+{plugins_x}+{plugins_y}")
        win.minsize(min(420, plugins_w), min(320, plugins_h))
        win.configure(bg=g["BG"])
        win.transient(self.root)
        win.resizable(True, True)

        content_shell = tk.Frame(win, bg=g["BG"])
        content_shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(content_shell, bg=g["BG"], highlightthickness=0, borderwidth=0)
        scroll_track = tk.Frame(content_shell, bg=g["BG"], width=12, cursor="sb_v_double_arrow")
        scroll_thumb = tk.Frame(scroll_track, bg=g["BORDER"], width=5, cursor="sb_v_double_arrow")
        content = tk.Frame(canvas, bg=g["BG"])
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.pack(side="left", fill="both", expand=True)
        scroll_track.pack(side="right", fill="y", padx=(0, 5), pady=10)
        scroll_track.pack_propagate(False)

        def update_scroll_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                scroll_thumb.place_forget()
                return
            scroll_thumb.place(relx=0.5, rely=start, relheight=max(0.08, end - start), width=5, anchor="n")

        def scroll_to_pointer(event) -> None:
            height = max(1, scroll_track.winfo_height())
            canvas.yview_moveto(max(0.0, min(1.0, event.y / height)))

        drag_state = {"y": 0, "first": 0.0}

        def start_thumb_drag(event) -> None:
            first, _last = canvas.yview()
            drag_state["y"] = event.y_root
            drag_state["first"] = first
            scroll_thumb.config(bg=globals()["ACCENT"])

        def drag_thumb(event) -> None:
            height = max(1, scroll_track.winfo_height())
            delta = (event.y_root - drag_state["y"]) / height
            canvas.yview_moveto(max(0.0, min(1.0, drag_state["first"] + delta)))

        def end_thumb_drag(_event) -> None:
            scroll_thumb.config(bg=globals()["BORDER"])

        canvas.configure(yscrollcommand=update_scroll_thumb)
        scroll_track.bind("<Button-1>", scroll_to_pointer)
        scroll_thumb.bind("<ButtonPress-1>", start_thumb_drag)
        scroll_thumb.bind("<B1-Motion>", drag_thumb)
        scroll_thumb.bind("<ButtonRelease-1>", end_thumb_drag)
        scroll_thumb.bind("<Enter>", lambda _e: scroll_thumb.config(bg=globals()["ACCENT_2"]))
        scroll_thumb.bind("<Leave>", lambda _e: scroll_thumb.config(bg=globals()["BORDER"]))

        def update_scroll_region(_event=None) -> None:
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.itemconfigure(content_window, width=canvas.winfo_width())
                first, last = canvas.yview()
                update_scroll_thumb(str(first), str(last))
            except tk.TclError:
                pass

        def wheel(event):
            if win.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return None

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_scroll_region)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        footer = tk.Frame(win, bg=g["BG"])
        footer.pack(fill="x", side="bottom")
        footer_msg = tk.Label(
            footer,
            text=t("plugins.footer_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        footer_msg.pack(fill="x", padx=22, pady=(8, 12))
        win.bind(
            "<Configure>",
            lambda _event: footer_msg.configure(wraplength=max(220, win.winfo_width() - 44)),
            add="+",
        )

        title = tk.Label(content, text=t("plugins.title"), bg=g["BG"], fg=g["TEXT"], font=("Segoe UI", 15, "bold"))
        title.pack(pady=(18, 8))
        subtitle = tk.Label(
            content,
            text=t("plugins.subtitle"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        subtitle.pack(fill="x", padx=32, pady=(0, 14))

        body = tk.Frame(content, bg=g["BG"])
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        grid_shell = tk.Frame(
            body,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            padx=8,
            pady=8,
        )
        grid_shell.pack(fill="both", expand=True, padx=4, pady=(0, 12))
        grid = tk.Frame(grid_shell, bg=g["SURFACE"])
        grid.pack(fill="both", expand=True)

        cards: list[dict[str, object]] = []
        layout_state = {"columns": 0}

        def clear_grid_weights() -> None:
            for column in range(6):
                grid.grid_columnconfigure(column, weight=0, uniform="")
            for row in range(12):
                grid.grid_rowconfigure(row, weight=0, uniform="")

        def layout_plugin_cards(columns: int) -> None:
            columns = max(1, min(6, columns))
            if layout_state["columns"] != columns:
                layout_state["columns"] = columns
                clear_grid_weights()
                for column in range(columns):
                    grid.grid_columnconfigure(column, weight=1, uniform="plugin")
                rows = max(1, (len(cards) + columns - 1) // columns)
                for row in range(rows):
                    grid.grid_rowconfigure(row, weight=1, uniform="plugin")
            else:
                rows = max(1, (len(cards) + columns - 1) // columns)
            if empty is not None:
                empty.grid_configure(columnspan=columns, rowspan=rows)
            wraplength = max(86, min(160, grid.winfo_width() // columns - 28))
            for index, card_state in enumerate(cards):
                row, column = divmod(index, columns)
                card_state["card"].grid_configure(row=row, column=column, sticky="nsew", padx=5, pady=5)
                card_state["name"].configure(wraplength=wraplength)

        def on_grid_configure(event) -> None:
            width = max(1, int(event.width))
            layout_plugin_cards(max(1, min(6, width // 128)))

        def set_card_background(card_state: dict[str, object], active: bool = False) -> None:
            background = globals()["SURFACE_2"] if active else globals()["SURFACE"]
            for widget in card_state["widgets"]:
                try:
                    widget.configure(bg=background)
                except tk.TclError:
                    pass
            card_state["card"].configure(bg=background)

        plugins = enabled_plugins(self.config)
        empty = None
        if not plugins:
            empty = tk.Label(
                grid,
                text=t("plugins.empty"),
                bg=g["SURFACE"],
                fg=g["MUTED"],
                font=("Segoe UI", 10),
                anchor="center",
            )
            empty.grid(row=0, column=0, columnspan=1, rowspan=1, sticky="nsew")

        for index, plugin in enumerate(plugins):
            card = tk.Frame(grid, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"])
            card.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            card.grid_propagate(False)
            icon_label = tk.Label(card, text=plugin.icon, bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI Emoji", 22))
            icon_label.pack(pady=(14, 4))
            name_label = tk.Label(
                card,
                text=t(plugin.name_key),
                bg=g["SURFACE"],
                fg=g["TEXT_SOFT"],
                font=("Segoe UI", 9),
                wraplength=86,
                justify="center",
            )
            name_label.pack(fill="x", padx=7)
            hint_label = tk.Label(
                card,
                text=t("plugins.open") if plugin.entrypoint else t("plugins.placeholder.coming_soon"),
                bg=g["SURFACE"],
                fg=g["MUTED"],
                font=("Segoe UI", 8),
            )
            hint_label.pack(pady=(3, 8))
            card_state = {
                "card": card,
                "widgets": (icon_label, name_label, hint_label),
                "icon": icon_label,
                "name": name_label,
                "hint": hint_label,
            }
            cards.append(card_state)
            for widget in (card, icon_label, name_label, hint_label):
                widget.bind("<Enter>", lambda _event, state=card_state: set_card_background(state, True))
                widget.bind("<Leave>", lambda _event, state=card_state: set_card_background(state, False))
                if plugin.entrypoint:
                    widget.configure(cursor="hand2")
                    widget.bind(
                        "<Button-1>",
                        lambda _event, entrypoint=plugin.entrypoint: self._run_plugin_entrypoint(entrypoint),
                    )

        grid.bind("<Configure>", on_grid_configure)
        layout_plugin_cards(max(1, min(6, plugins_w // 128)))

        plugin_theme_widgets = {
            "window": win,
            "content_shell": content_shell,
            "canvas": canvas,
            "scroll_track": scroll_track,
            "scroll_thumb": scroll_thumb,
            "content": content,
            "footer": footer,
            "footer_msg": footer_msg,
            "title": title,
            "subtitle": subtitle,
            "body": body,
            "grid_shell": grid_shell,
            "grid": grid,
            "empty": empty,
            "cards": cards,
            "wheel": wheel,
        }
        self._plugin_window_state = plugin_theme_widgets

        def close() -> None:
            self._plugins_open = False
            self._plugin_window_state = None
            if getattr(self, "_plugin_parent_window", None) is win:
                try:
                    delattr(self, "_plugin_parent_window")
                except AttributeError:
                    pass
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            try:
                win.destroy()
            except tk.TclError:
                pass

        def show_taskbar_entry() -> None:
            try:
                win.update_idletasks()
                handle = self._window_handle(win) if hasattr(self, "_window_handle") else int(win.winfo_id())
                show_window_in_taskbar(handle)
            except (tk.TclError, OSError, ValueError, TypeError):
                pass

        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _event: close())
        self._refresh_plugin_window_theme()
        win.update_idletasks()
        win.deiconify()
        show_taskbar_entry()
        win.lift()
        win.focus_force()

    def _refresh_plugin_window_theme(self) -> None:
        state = getattr(self, "_plugin_window_state", None)
        if not state:
            return
        try:
            state["window"].configure(bg=globals()["BG"])
            state["content_shell"].configure(bg=globals()["BG"])
            state["canvas"].configure(bg=globals()["BG"])
            state["scroll_track"].configure(bg=globals()["BG"])
            state["scroll_thumb"].configure(bg=globals()["BORDER"])
            state["content"].configure(bg=globals()["BG"])
            state["footer"].configure(bg=globals()["BG"])
            state["footer_msg"].configure(bg=globals()["BG"], fg=globals()["MUTED"])
            state["title"].configure(bg=globals()["BG"], fg=globals()["TEXT"])
            state["subtitle"].configure(bg=globals()["BG"], fg=globals()["MUTED"])
            state["body"].configure(bg=globals()["BG"])
            state["grid_shell"].configure(bg=globals()["SURFACE"], highlightbackground=globals()["BORDER"])
            state["grid"].configure(bg=globals()["SURFACE"])
            empty = state.get("empty")
            if empty is not None:
                empty.configure(bg=globals()["SURFACE"], fg=globals()["MUTED"])
            for card_state in state["cards"]:
                card = card_state["card"]
                card.configure(bg=globals()["SURFACE"], highlightbackground=globals()["BORDER"])
                card_state["icon"].configure(bg=globals()["SURFACE"], fg=globals()["TEXT"])
                card_state["name"].configure(bg=globals()["SURFACE"], fg=globals()["TEXT_SOFT"])
                card_state["hint"].configure(bg=globals()["SURFACE"], fg=globals()["MUTED"])
        except tk.TclError:
            self._plugin_window_state = None
