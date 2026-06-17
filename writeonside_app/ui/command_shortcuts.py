from __future__ import annotations

import tkinter as tk

from ..hotkeys import format_hotkey_display
from ..i18n import command_tooltip, t
from ..shortcuts import hotkey_to_tk_sequence, normalize_command_shortcuts


class CommandShortcutsMixin:
    MARKDOWN_COMMANDS = {
        "toggle_mode", "frontmatter", "bold", "italic", "underline", "strike",
        "heading", "highlight", "color", "code", "quote", "link", "image",
        "table", "bullet", "ordered", "task", "divider",
    }
    def _command_actions(self):
        return {
            "open_file": self._open_file_dialog,
            "new_note": self._create_new_note,
            "save_note": lambda: self._save_note(True),
            "toggle_mode": self._toggle_view_mode,
            "outline": self._show_outline_popup,
            "backlinks": self._show_backlinks_popup,
            "find": lambda: self._open_find_panel(False),
            "replace": lambda: self._open_find_panel(True),
            "frontmatter": self._ensure_current_front_matter,
            "bold": lambda: self._wrap_selection("**", "**", "bold"),
            "italic": lambda: self._wrap_selection("*", "*", "italic"),
            "underline": lambda: self._wrap_selection("<u>", "</u>", "text"),
            "strike": lambda: self._wrap_selection("~~", "~~", "text"),
            "heading": lambda: self._show_heading_popup(self._format_buttons["heading"]),
            "highlight": lambda: self._wrap_selection("==", "==", "text"),
            "color": lambda: self._show_text_color_popup(self._format_buttons["color"]),
            "code": self._smart_code_format,
            "quote": lambda: self._line_prefix("> "),
            "link": lambda: self._wrap_selection("[", "](url)", "text"),
            "image": self._insert_image_file,
            "table": self._insert_markdown_table,
            "bullet": lambda: self._apply_list_format("bullet"),
            "ordered": lambda: self._apply_list_format("ordered"),
            "task": lambda: self._apply_list_format("task"),
            "divider": lambda: self._insert_text("\n---\n"),
        }

    def _shortcut_widgets(self) -> dict[str, tk.Widget]:
        widgets = {
            "open_file": self.open_file_btn,
            "new_note": self.new_btn,
            "save_note": self.save_now_btn,
            "toggle_mode": self.view_toggle_btn,
            "outline": self.outline_btn,
            "backlinks": self.backlinks_btn,
            "find": self.find_btn,
        }
        widgets.update(self._format_buttons)
        return widgets

    def _unregister_command_shortcuts(self) -> None:
        for sequence in getattr(self, "_bound_command_sequences", set()):
            try:
                self.root.unbind_all(sequence)
            except tk.TclError:
                pass
        self._bound_command_sequences = set()

    def _register_command_shortcuts(self) -> None:
        self._unregister_command_shortcuts()
        self.config.command_shortcuts = normalize_command_shortcuts(self.config.command_shortcuts)
        actions = self._command_actions()
        self._bound_command_sequences = set()
        for command_id, shortcut in self.config.command_shortcuts.items():
            action = actions.get(command_id)
            sequence = hotkey_to_tk_sequence(shortcut)
            if action is None or sequence is None or sequence in self._bound_command_sequences:
                continue

            def invoke(_event=None, callback=action, key=command_id):
                if self._settings_open:
                    return None
                if key in self.MARKDOWN_COMMANDS and not self._is_markdown_document():
                    return "break"
                callback()
                return "break"

            self.root.bind_all(sequence, invoke, add="+")
            self._bound_command_sequences.add(sequence)
        self._update_command_tooltips()

    def _update_command_tooltips(self) -> None:
        shortcuts = normalize_command_shortcuts(self.config.command_shortcuts)
        for command_id, widget in self._shortcut_widgets().items():
            shortcut = shortcuts.get(command_id, "")
            display = format_hotkey_display(shortcut) if shortcut else ""
            widget._tooltip_text = command_tooltip(command_id, display)
