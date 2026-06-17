from __future__ import annotations

import tkinter as tk

from ..i18n import SUPPORTED_LANGUAGES, set_language, t


class I18nMixin:
    _status_message_key: str | None = None
    _status_message_kwargs: dict[str, object] | None = None

    def _init_i18n(self) -> None:
        set_language(self.config.language)
        self._i18n_tooltips: dict[tk.Widget, str] = {}

    def _track_tooltip(self, widget: tk.Widget, key: str) -> None:
        widget._i18n_tooltip_key = key  # type: ignore[attr-defined]
        widget._tooltip_text = t(key)
        self._i18n_tooltips[widget] = key

    def _set_status_key(self, key: str, **kwargs: object) -> None:
        self._status_message_key = key
        self._status_message_kwargs = dict(kwargs)
        self._set_status(t(key, **kwargs))

    def _refresh_status_bar(self) -> None:
        if self._status_message_key:
            kwargs = self._status_message_kwargs or {}
            self._set_status(t(self._status_message_key, **kwargs))

    def _apply_language(self) -> None:
        set_language(self.config.language)
        self._refresh_header_tooltips()
        self._refresh_explorer_labels()
        self._refresh_find_tooltips()
        self._update_view_buttons()
        self._update_hotkey_hints()
        self._refresh_status_bar()
        self._rebuild_tray_menu()
        if hasattr(self, "_read_copy_btn") and self._read_copy_btn.winfo_exists():
            self._read_copy_btn.configure(text=t("editor.copy"))

    def _refresh_header_tooltips(self) -> None:
        if hasattr(self, "menu_btn"):
            self._track_tooltip(self.menu_btn, "tooltip.toggle_files")
        if hasattr(self, "close_btn"):
            self._track_tooltip(self.close_btn, "tooltip.close")
        if hasattr(self, "settings_btn"):
            self._track_tooltip(self.settings_btn, "tooltip.settings")
        if hasattr(self, "outline_btn"):
            self._track_tooltip(self.outline_btn, "cmd.outline")
        if hasattr(self, "backlinks_btn"):
            self._track_tooltip(self.backlinks_btn, "cmd.backlinks")
        if hasattr(self, "find_btn"):
            self._track_tooltip(self.find_btn, "tooltip.find_replace")
        if hasattr(self, "save_now_btn"):
            self._track_tooltip(self.save_now_btn, "cmd.save_note")
        if hasattr(self, "new_btn"):
            self._track_tooltip(self.new_btn, "cmd.new_note")
        if hasattr(self, "open_file_btn"):
            self._track_tooltip(self.open_file_btn, "cmd.open_file")
        if hasattr(self, "more_format_btn"):
            self._track_tooltip(self.more_format_btn, "tooltip.more_formatting")
        for command_id, button in getattr(self, "_format_buttons", {}).items():
            self._track_tooltip(button, f"cmd.{command_id}")

    def _refresh_explorer_labels(self) -> None:
        if hasattr(self, "explorer_title"):
            self.explorer_title.configure(text=t("explorer.files"))
        if hasattr(self, "explorer_search_placeholder"):
            self.explorer_search_placeholder.configure(text=t("explorer.search_notes"))
        if hasattr(self, "tag_title"):
            self.tag_title.configure(text=t("explorer.tags"))
        if hasattr(self, "tag_scope_label"):
            scope = getattr(self, "_explorer_scope", None)
            root = self._workspace_dir() if hasattr(self, "_workspace_dir") else None
            if scope is None or (root and scope == root):
                self.tag_scope_label.configure(text=t("explorer.all_notes"))
        if hasattr(self, "tag_search_placeholder"):
            self.tag_search_placeholder.configure(text=t("explorer.filter_tags"))
        if hasattr(self, "explorer_new_btn"):
            self._track_tooltip(self.explorer_new_btn, "tooltip.new_note")
        if hasattr(self, "explorer_refresh_btn"):
            self._track_tooltip(self.explorer_refresh_btn, "tooltip.refresh_files")
        if hasattr(self, "tag_clear_btn"):
            self._track_tooltip(self.tag_clear_btn, "tooltip.clear_tag_filters")

    def _refresh_find_tooltips(self) -> None:
        mapping = getattr(self, "_find_tooltip_buttons", None)
        if not mapping:
            return
        for key, button in mapping.items():
            self._track_tooltip(button, key)


    def _rebuild_tray_menu(self) -> None:
        tray = getattr(self, "tray", None)
        if tray is None:
            return
        try:
            import pystray

            menu = pystray.Menu(
                pystray.MenuItem(t("tray.toggle"), lambda: self._post_ui(self.toggle_panel)),
                pystray.MenuItem(t("tray.new_note"), lambda: self._post_ui(self._create_new_note_from_tray)),
                pystray.MenuItem(t("tray.settings"), lambda: self._post_ui(self._open_settings)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t("tray.quit"), lambda: self._post_ui(self._quit)),
            )
            tray.menu = menu
        except Exception:
            pass

    @staticmethod
    def _language_choices() -> list[tuple[str, str]]:
        return [(code, t(f"lang.{code}")) for code in SUPPORTED_LANGUAGES]
