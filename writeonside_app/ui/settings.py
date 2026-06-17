from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable
from tkinter import filedialog, messagebox
import tkinter as tk
import tkinter.font as tkfont

from .. import theme as theme_module
from ..config import APP_NAME, AppConfig, normalize_relative_folder, save_config
from ..i18n import SUPPORTED_LANGUAGES, command_label, normalize_language, set_language, t
from ..hotkeys import format_hotkey_display, normalize_hotkey, read_hotkey_clean, validate_hotkey
from ..layout_metrics import explorer_width_limits, panel_width_limits
from ..platform import is_startup_enabled, set_startup_enabled
from ..shortcuts import (
    COMMAND_SHORTCUTS,
    DEFAULT_COMMAND_SHORTCUTS,
    normalize_command_shortcuts,
    shortcut_conflicts,
)
from ..storage import BACKUP_DIR
from ..theme import *  # noqa: F401,F403


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
        }

        win = tk.Toplevel(self.root)
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
        win.lift(self.root)
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
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(content_window, width=canvas.winfo_width())
            first, last = canvas.yview()
            update_scroll_thumb(str(first), str(last))

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
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return None

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_scroll_region)
        canvas.bind_all("<MouseWheel>", wheel)

        footer = tk.Frame(win, bg=g["BG"])
        footer.pack(fill="x", side="bottom")
        msg = tk.Label(footer, text=t("settings.footer_hint"), bg=g["BG"], fg=g["MUTED"], font=("Segoe UI", 9), anchor="w")
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
                font=("Segoe UI", 10),
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
                font=("Segoe UI", 10),
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

        settings_title_label = tk.Label(content, text=t("settings.title"), bg=g["BG"], fg=g["TEXT"], font=("Segoe UI", 15, "bold"))
        settings_title_label.pack(pady=(18, 10))
        settings_body = tk.Frame(content, bg=g["BG"])
        settings_body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        settings_nav = tk.Frame(settings_body, bg=g["BG"])
        settings_nav.pack(fill="x", padx=4, pady=(0, 12))
        settings_pages = tk.Frame(settings_body, bg=g["BG"])
        settings_pages.pack(fill="both", expand=True)
        pages = {
            "general": tk.Frame(settings_pages, bg=g["BG"]),
            "appearance": tk.Frame(settings_pages, bg=g["BG"]),
            "layout": tk.Frame(settings_pages, bg=g["BG"]),
            "shortcuts": tk.Frame(settings_pages, bg=g["BG"]),
        }
        page_buttons: dict[str, tk.Label] = {}
        active_page = tk.StringVar(value="general")

        def refresh_page_nav() -> None:
            _g = globals()
            for key, button in page_buttons.items():
                selected = active_page.get() == key
                button.configure(
                    bg=_g["SIDEBAR_HOVER"] if selected else _g["BG"],
                    fg=_g["ACCENT"] if selected else _g["TEXT_SOFT"],
                    font=("Segoe UI", 10, "bold" if selected else "normal"),
                )

        def show_settings_page(name: str) -> None:
            if name not in pages:
                return
            active_page.set(name)
            for page in pages.values():
                page.pack_forget()
            pages[name].pack(fill="both", expand=True)
            refresh_page_nav()
            canvas.yview_moveto(0)
            win.after_idle(update_scroll_region)

        for key, label_text in (
            ("general", t("settings.page.general")),
            ("appearance", t("settings.page.appearance")),
            ("layout", t("settings.page.layout")),
            ("shortcuts", t("settings.page.shortcuts")),
        ):
            _g = globals()
            button = tk.Label(
                settings_nav,
                text=label_text,
                bg=_g["BG"],
                fg=_g["TEXT_SOFT"],
                font=("Segoe UI", 10),
                anchor="center",
                padx=14,
                pady=8,
                cursor="hand2",
            )
            button.pack(side="left", fill="x", expand=True, padx=2)
            button.bind("<Button-1>", lambda _e, value=key: show_settings_page(value))
            page_buttons[key] = button

        general_page = pages["general"]
        appearance_page = pages["appearance"]
        layout_page = pages["layout"]
        shortcuts_page = pages["shortcuts"]
        general_section_label = tk.Label(general_page, text=t("settings.section.general"), bg=g["BG"], fg=g["TEXT"], font=("Segoe UI", 13, "bold"), anchor="w")
        general_section_label.pack(fill="x", padx=18, pady=(2, 10))
        appearance_section_label = tk.Label(appearance_page, text=t("settings.section.appearance"), bg=g["BG"], fg=g["TEXT"], font=("Segoe UI", 13, "bold"), anchor="w")
        appearance_section_label.pack(fill="x", padx=18, pady=(2, 10))
        layout_section_label = tk.Label(layout_page, text=t("settings.section.layout"), bg=g["BG"], fg=g["TEXT"], font=("Segoe UI", 13, "bold"), anchor="w")
        layout_section_label.pack(fill="x", padx=18, pady=(2, 10))
        shortcuts_section_label = tk.Label(shortcuts_page, text=t("settings.section.shortcuts"), bg=g["BG"], fg=g["TEXT"], font=("Segoe UI", 13, "bold"), anchor="w")
        shortcuts_section_label.pack(fill="x", padx=18, pady=(2, 4))
        shortcuts_hint_label = tk.Label(
            shortcuts_page,
            text=t("settings.shortcuts_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        shortcuts_hint_label.pack(fill="x", padx=18, pady=(0, 8))
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
            state = {"open": False, "values": list(values)}
            shell = tk.Frame(parent, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"])
            shell.pack(fill="x")
            button = tk.Frame(shell, bg=g["SURFACE"], cursor="hand2", padx=10, pady=7)
            button.pack(fill="x")
            value_label = tk.Label(
                button,
                text=variable.get(),
                bg=g["SURFACE"],
                fg=g["TEXT"],
                font=("Segoe UI", 10),
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
                        value_label.configure(font=("Segoe UI", 10))

            def close_dropdown() -> None:
                if not state["open"]:
                    return
                state["open"] = False
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
                    font=("Segoe UI", 10),
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
            font=("Segoe UI", 10),
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
                font=("Segoe UI", 9),
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
                font=("Segoe UI", 9),
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
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=390,
            justify="left",
        )
        backups_label.pack(fill="x", padx=22, pady=(0, 6))
        record_btn_ref: list[tk.Button] = []
        hotkey_recording = False
        e_hotkey: tk.Entry

        def set_entry(entry: tk.Entry, value: str) -> None:
            entry.delete(0, tk.END)
            entry.insert(0, value)

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

        position_frame = tk.Frame(layout_page, bg=g["BG"])
        position_frame.pack(fill="x", padx=18, pady=6)
        position_label = tk.Label(position_frame, text=t("settings.app_position"), bg=g["BG"], fg=g["TEXT"], font=("Segoe UI", 10), width=16, anchor="w")
        position_label.pack(side="left")
        position_var = tk.StringVar(value=self.config.app_position)
        position_choices = tk.Frame(position_frame, bg=g["SURFACE"])
        position_choices.pack(side="left", fill="x", expand=True, padx=(4, 6))
        position_buttons: dict[str, tk.Label] = {}
        position_labels = {"left": t("position.left"), "right": t("position.right")}

        def select_position(value: str, preview: bool = True) -> None:
            if value not in {"left", "right"}:
                return
            _g = globals()
            position_var.set(value)
            for key, button in position_buttons.items():
                selected = key == value
                button.config(
                    text=position_labels[key],
                    bg=_g["SIDEBAR_HOVER"] if selected else _g["SURFACE"],
                    fg=_g["TEXT"] if selected else _g["TEXT_SOFT"],
                    font=("Segoe UI", 10, "bold" if selected else "normal"),
                    highlightbackground=_g["ACCENT_2"] if selected else _g["BORDER"],
                    highlightcolor=_g["ACCENT_2"] if selected else _g["BORDER"],
                    highlightthickness=2 if selected else 1,
                )
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

        for key, label_text in (("left", t("position.left")), ("right", t("position.right"))):
            _g = globals()
            button = tk.Label(
                position_choices,
                text=label_text,
                bg=_g["SURFACE"],
                fg=_g["TEXT_SOFT"],
                font=("Segoe UI", 10),
                cursor="hand2",
                pady=5,
                highlightthickness=1,
                highlightbackground=_g["BORDER"],
            )
            button.pack(side="left", fill="x", expand=True)
            button.bind("<Button-1>", lambda _e, value=key: select_position(value))
            position_buttons[key] = button
        select_position(position_var.get(), preview=False)

        theme_frame = tk.Frame(appearance_page, bg=g["BG"])
        theme_frame.pack(fill="x", padx=18, pady=6)
        theme_label = tk.Label(
            theme_frame,
            text=t("settings.color_theme"),
            bg=g["BG"],
            fg=g["TEXT"],
            font=("Segoe UI", 10),
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
                    font=("Segoe UI", 9, "bold" if selected else "normal"),
                )

        def select_theme(value: str) -> None:
            if value not in theme_module.THEMES:
                return
            theme_var.set(value)
            self._apply_theme(value)
            select_position(position_var.get())
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
                font=("Segoe UI", 9),
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
            font=("Segoe UI", 10),
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
        available_fonts = sorted(set(tkfont.families(self.root)), key=str.casefold)
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
            font=("Segoe UI", 12, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
        )
        size_value = tk.Label(
            size_frame,
            text=str(font_size_var.get()),
            bg=g["SURFACE_2"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            width=3,
            pady=6,
        )
        size_up = tk.Label(
            size_frame,
            text="+",
            bg=g["SURFACE_2"],
            fg=g["TEXT_SOFT"],
            font=("Segoe UI", 12, "bold"),
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
            font=("Segoe UI", 9),
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
            except ValueError:
                return
            work_width = max(1, self.work_right - self.work_left)
            panel_min, panel_max = panel_width_limits(work_width)
            explorer_min, explorer_max = explorer_width_limits(work_width)
            if not panel_min <= panel_width <= panel_max or not explorer_min <= explorer_width <= explorer_max:
                return
            if panel_width == self.panel_w and explorer_width == self.explorer_w:
                return
            self.panel_w = panel_width
            self.explorer_w = explorer_width
            self.config.width = panel_width
            self.config.explorer_width = explorer_width
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

        for width_entry in (e_width, e_explorer):
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
            font=("Segoe UI", 10),
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
            font=("Segoe UI", 9),
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

        def draw_alpha_slider(_event=None) -> None:
            _g = globals()
            alpha_scale.delete("all")
            width = max(40, alpha_scale.winfo_width())
            left, right, center_y = 11, width - 11, 15
            progress = (alpha_var.get() - 0.30) / 0.70
            progress = max(0.0, min(1.0, progress))
            thumb_x = left + (right - left) * progress
            alpha_scale.create_line(left, center_y, right, center_y, fill=_g["SURFACE_2"], width=7, capstyle=tk.ROUND)
            alpha_scale.create_line(left, center_y, thumb_x, center_y, fill=_g["ACCENT"], width=7, capstyle=tk.ROUND)
            alpha_scale.create_oval(
                thumb_x - 7, center_y - 7, thumb_x + 7, center_y + 7,
                fill=_g["SURFACE"], outline=_g["ACCENT_2"], width=3,
            )

        def set_alpha_from_x(x: int) -> None:
            width = max(40, alpha_scale.winfo_width())
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

        bools = tk.Frame(general_page, bg=g["BG"])
        bools.pack(fill="x", padx=18, pady=(8, 4))
        auto_save_var = tk.BooleanVar(value=self.config.auto_save)
        remember_var = tk.BooleanVar(value=self.config.remember_last_note)
        explorer_var = tk.BooleanVar(value=self.config.explorer_open)
        start_on_boot_var = tk.BooleanVar(value=self.config.start_on_boot)
        setting_toggles: list[tuple[str, tk.BooleanVar, tk.Frame, tk.Canvas, tk.Label]] = []

        def refresh_setting_toggles() -> None:
            _g = globals()
            for text_key, var, row_frame, switch, text_label in setting_toggles:
                selected = var.get()
                row_frame.configure(bg=_g["BG"])
                switch.configure(bg=_g["BG"])
                switch.delete("all")
                track = _g["ACCENT"] if selected else _g["BORDER"]
                knob = self._contrast_text(_g["ACCENT"]) if selected else _g["TEXT_SOFT"]
                switch.create_oval(2, 3, 16, 17, fill=track, outline=track)
                switch.create_rectangle(9, 3, 27, 17, fill=track, outline=track)
                switch.create_oval(20, 3, 34, 17, fill=track, outline=track)
                knob_x = 26 if selected else 10
                switch.create_oval(
                    knob_x - 6,
                    4,
                    knob_x + 6,
                    16,
                    fill=knob,
                    outline="",
                )
                text_label.configure(
                    text=t(text_key),
                    bg=_g["BG"],
                    fg=_g["TEXT"] if selected else _g["TEXT_SOFT"],
                    font=("Segoe UI", 9),
                )

        def add_setting_toggle(text_key: str, var: tk.BooleanVar) -> None:
            _g = globals()
            row_frame = tk.Frame(bools, bg=_g["BG"], cursor="hand2", padx=3, pady=5)
            row_frame.pack(fill="x", pady=1)
            switch = tk.Canvas(
                row_frame,
                bg=_g["BG"],
                width=36,
                height=20,
                cursor="hand2",
                highlightthickness=0,
                borderwidth=0,
            )
            switch.pack(side="left", padx=(0, 9))
            text_label = tk.Label(
                row_frame,
                text=t(text_key),
                bg=_g["BG"],
                fg=_g["TEXT"],
                font=("Segoe UI", 9),
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
            general_section_label.configure(text=t("settings.section.general"))
            appearance_section_label.configure(text=t("settings.section.appearance"))
            layout_section_label.configure(text=t("settings.section.layout"))
            shortcuts_section_label.configure(text=t("settings.section.shortcuts"))
            shortcuts_hint_label.configure(text=t("settings.shortcuts_hint"))
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
            select_position(position_var.get(), preview=False)
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
            if not 8 <= nav_width <= 32:
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
            workspace_changed = apply_workspace_only()
            previous_position = self.config.app_position
            previous_panel_width = self.panel_w
            previous_explorer_width = self.explorer_w
            self.config.hotkey = new_hotkey
            self.config.command_shortcuts = command_shortcuts
            self.config.obsidian_vault = ""
            self.config.width = panel_width
            self.config.explorer_width = explorer_width
            self.config.nav_width = nav_width
            self.config.alpha = alpha
            self._preview_alpha = None
            self.config.app_position = position_var.get() if position_var.get() in {"left", "right"} else "right"
            self.config.theme = theme_var.get() if theme_var.get() in theme_module.THEMES else theme_module.DEFAULT_THEME
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
            self.config.obsidian_vault = ""
            self.config.width = int(original["width"])
            self.config.explorer_width = int(original["explorer_width"])
            self.config.nav_width = int(original["nav_width"])
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
            choice = messagebox.askyesnocancel(APP_NAME, t("dialog.save_settings"), parent=win)
            if choice is None:
                return
            if choice:
                if not save_settings():
                    return
            else:
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
        update_scroll_region()

    def _browse_into(self, entry: tk.Entry, browse: Callable[[], str], after: Callable[[], None] | None = None) -> None:
        value = browse()
        if value:
            entry.delete(0, tk.END)
            entry.insert(0, value)
            if after:
                after()
