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
        plugins_w = min(720, max(360, work_width - 64))
        plugins_h = min(460, max(300, work_height - 96))
        plugins_x = self.work_left + max(0, (work_width - plugins_w) // 2)
        plugins_y = self.work_top + max(0, (work_height - plugins_h) // 2)
        win.geometry(f"{plugins_w}x{plugins_h}+{plugins_x}+{plugins_y}")
        win.minsize(min(420, plugins_w), min(320, plugins_h))
        win.configure(bg=g["BG"])
        win.resizable(True, True)

        footer = tk.Label(
            win,
            text=t("plugins.footer_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        footer.pack(fill="x", side="bottom", padx=22, pady=(8, 12))
        content_shell = tk.Frame(win, bg=g["BG"])
        content_shell.pack(fill="both", expand=True)

        subtitle = tk.Label(
            content_shell,
            text=t("plugins.subtitle"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        subtitle.pack(fill="x", padx=22, pady=(20, 14))

        grid = tk.Frame(content_shell, bg=g["BG"])
        grid.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        for column in range(6):
            grid.grid_columnconfigure(column, weight=1, uniform="plugin")
        for row in range(2):
            grid.grid_rowconfigure(row, weight=1, uniform="plugin")

        cards: list[dict[str, object]] = []

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
                bg=g["BG"],
                fg=g["MUTED"],
                font=("Segoe UI", 10),
                anchor="center",
            )
            empty.grid(row=0, column=0, columnspan=6, rowspan=2, sticky="nsew")

        for index, plugin in enumerate(plugins):
            row, column = divmod(index, 6)
            card = tk.Frame(grid, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"])
            card.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
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

        plugin_theme_widgets = {
            "window": win,
            "content_shell": content_shell,
            "subtitle": subtitle,
            "grid": grid,
            "footer": footer,
            "empty": empty,
            "cards": cards,
        }
        self._plugin_window_state = plugin_theme_widgets

        def close() -> None:
            self._plugins_open = False
            self._plugin_window_state = None
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
            state["subtitle"].configure(bg=globals()["BG"], fg=globals()["MUTED"])
            state["grid"].configure(bg=globals()["BG"])
            state["footer"].configure(bg=globals()["BG"], fg=globals()["MUTED"])
            empty = state.get("empty")
            if empty is not None:
                empty.configure(bg=globals()["BG"], fg=globals()["MUTED"])
            for card_state in state["cards"]:
                card = card_state["card"]
                card.configure(bg=globals()["SURFACE"], highlightbackground=globals()["BORDER"])
                card_state["icon"].configure(bg=globals()["SURFACE"], fg=globals()["TEXT"])
                card_state["name"].configure(bg=globals()["SURFACE"], fg=globals()["TEXT_SOFT"])
                card_state["hint"].configure(bg=globals()["SURFACE"], fg=globals()["MUTED"])
        except tk.TclError:
            self._plugin_window_state = None
