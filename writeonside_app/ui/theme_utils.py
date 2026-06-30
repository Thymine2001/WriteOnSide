from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from .. import theme as theme_module
from ..platform import redraw_window, set_window_redraw
from ..theme import *  # noqa: F401,F403  – initial palette values; updated by _set_theme_globals


class ThemeMixin:
    def _register_themed_widget(self, widget: tk.Misc, option_map: dict[str, str]) -> None:
        registry = getattr(self, "_themed_widgets", None)
        if registry is None:
            registry = []
            self._themed_widgets = registry
        registry.append((widget, option_map))

    def _apply_registered_theme_colors(self, palette: dict[str, str]) -> None:
        for widget, option_map in getattr(self, "_themed_widgets", []):
            updates = {
                option: palette[color_key]
                for option, color_key in option_map.items()
                if color_key in palette
            }
            if not updates:
                continue
            try:
                widget.configure(**updates)
            except tk.TclError:
                pass
            for attribute, color_key in option_map.items():
                if attribute.startswith("_") and color_key in palette:
                    setattr(widget, attribute, palette[color_key])
    @staticmethod
    def _contrast_text(color: str) -> str:
        value = color.lstrip("#")
        if len(value) != 6:
            return "white"
        channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
        return "#111318" if luminance > 0.36 else "white"

    def _set_theme_globals(self, name: str) -> dict[str, str]:
        palette_obj = theme_module.current.set(name)
        new_palette = palette_obj.as_dict()
        self._active_theme = name if name in theme_module.THEMES else theme_module.DEFAULT_THEME
        self._apply_registered_theme_colors(new_palette)
        return new_palette

    def _apply_typography(self) -> None:
        if not hasattr(self, "root"):
            return
        family = self.config.font_family or "Segoe UI"
        size_delta = self.config.font_size - 10
        protected_families = {"Segoe MDL2 Assets", "Segoe UI Emoji", "Consolas"}

        def update_widget(widget: tk.Misc) -> None:
            widget_id = str(widget)
            try:
                font_value = widget.cget("font")
            except (tk.TclError, TypeError):
                font_value = ""
            if font_value:
                baseline = self._font_baselines.get(widget_id)
                if baseline is None:
                    try:
                        baseline = tkfont.Font(font=font_value).actual()
                    except tk.TclError:
                        baseline = None
                    if baseline:
                        self._font_baselines[widget_id] = baseline
                if baseline:
                    base_family = str(baseline.get("family", "Segoe UI"))
                    target_family = base_family if base_family in protected_families else family
                    target_size = max(7, abs(int(baseline.get("size", 10))) + size_delta)
                    styles = []
                    if str(baseline.get("weight", "normal")) == "bold":
                        styles.append("bold")
                    if str(baseline.get("slant", "roman")) == "italic":
                        styles.append("italic")
                    if int(baseline.get("underline", 0)):
                        styles.append("underline")
                    if int(baseline.get("overstrike", 0)):
                        styles.append("overstrike")
                    try:
                        widget.configure(font=(target_family, target_size, *styles))
                    except tk.TclError:
                        pass
            try:
                children = widget.winfo_children()
            except tk.TclError:
                children = []
            for child in children:
                if isinstance(child, tk.Toplevel):
                    continue  # Toplevels (dialogs) are either in roots or should be excluded
                update_widget(child)

        roots: list[tk.Misc] = [self.root]
        for name in ("explorer", "nav"):
            window = getattr(self, name, None)
            if window is not None:
                roots.append(window)
        for root in roots:
            update_widget(root)

        style = ttk.Style()
        style.configure("Explorer.Treeview", font=(family, max(8, self.config.font_size - 1)))
        if hasattr(self, "text"):
            self.text.configure(font=(family, self.config.font_size + 3))
            self._configure_editor_markdown_tags()
            self._schedule_live_render()
        if hasattr(self, "_apply_split_note_typography"):
            self._apply_split_note_typography()
        if hasattr(self, "read_text") and self.current_note_path:
            self._render_read_content()
        if hasattr(self, "file_tree"):
            self._on_file_tree_resize()
        self.root.update_idletasks()

    def _recolor_widget_tree(
        self,
        widget: tk.Misc,
        old_palette: dict[str, str],
        new_palette: dict[str, str],
        sidebar: bool = False,
    ) -> None:
        sidebar = sidebar or (hasattr(self, "explorer") and widget is self.explorer)
        is_swatch = bool(getattr(widget, "_theme_swatch", False))
        general_order = (
            "BG", "SURFACE", "SURFACE_2", "BORDER", "TEXT", "TEXT_SOFT", "MUTED",
            "ACCENT", "ACCENT_2", "DANGER", "CODE_BG", "CODE_TEXT", "LINK",
            "IMAGE_LINK", "QUOTE", "FIND_MATCH", "OUTLINE_CURRENT", "DISABLED",
            "SIDEBAR", "SIDEBAR_SURFACE", "SIDEBAR_BORDER", "SIDEBAR_TEXT",
            "SIDEBAR_MUTED", "SIDEBAR_HOVER",
        )
        sidebar_order = (
            "SIDEBAR", "SIDEBAR_SURFACE", "SIDEBAR_BORDER", "SIDEBAR_TEXT",
            "SIDEBAR_MUTED", "SIDEBAR_HOVER", "BORDER", "TEXT", "TEXT_SOFT",
            "MUTED", "ACCENT", "ACCENT_2", "DANGER", "BG", "SURFACE", "SURFACE_2",
        )
        key_order = sidebar_order if sidebar else general_order

        def replacement(value) -> str | None:
            if not isinstance(value, str):
                return None
            value = value.lower()
            for key in key_order:
                if old_palette.get(key, "").lower() == value:
                    return new_palette[key]
            return None

        if not is_swatch:
            for option in (
                "background", "foreground", "activebackground", "activeforeground",
                "insertbackground", "selectbackground", "selectforeground", "troughcolor",
                "highlightbackground", "highlightcolor", "disabledforeground",
                "readonlybackground",
            ):
                try:
                    new_value = replacement(widget.cget(option))
                    if new_value:
                        widget.configure(**{option: new_value})
                except (tk.TclError, TypeError):
                    pass
            for attribute in ("_normal_bg", "_normal_fg"):
                new_value = replacement(getattr(widget, attribute, None))
                if new_value:
                    setattr(widget, attribute, new_value)

        try:
            children = widget.winfo_children()
        except tk.TclError:
            children = []
        for child in children:
            # Toplevels are themed as independent roots in _apply_theme. Walking
            # them here would recolor every dialog/explorer widget twice.
            if isinstance(child, tk.Toplevel):
                continue
            self._recolor_widget_tree(child, old_palette, new_palette, sidebar)

    def _apply_top_chrome_theme(self, palette: dict[str, str]) -> None:
        pairs = (
            ("header", {"bg": "SURFACE"}),
            ("title_group", {"bg": "SURFACE"}),
            ("app_title_label", {"bg": "SURFACE", "fg": "TEXT"}),
            ("note_title", {"bg": "SURFACE", "fg": "MUTED"}),
            ("menu_btn", {"bg": "SURFACE", "fg": "MUTED", "_normal_bg": "SURFACE", "_normal_fg": "MUTED"}),
            ("close_btn", {"bg": "SURFACE", "fg": "MUTED", "_normal_bg": "SURFACE", "_normal_fg": "MUTED"}),
            ("plugins_btn", {"bg": "SURFACE", "fg": "MUTED", "_normal_bg": "SURFACE", "_normal_fg": "MUTED"}),
            ("toolbar", {"bg": "SURFACE_2"}),
            ("toolbar_top", {"bg": "SURFACE_2"}),
            ("toolbar_bottom", {"bg": "SURFACE_2"}),
            ("toolbar_sep", {"bg": "BORDER"}),
        )
        for name, option_map in pairs:
            widget = getattr(self, name, None)
            if widget is None:
                continue
            updates = {
                option: palette[color_key]
                for option, color_key in option_map.items()
                if not option.startswith("_") and color_key in palette
            }
            try:
                if updates:
                    widget.configure(**updates)
            except tk.TclError:
                pass
            for option, color_key in option_map.items():
                if option.startswith("_") and color_key in palette:
                    setattr(widget, option, palette[color_key])
        for btn in getattr(self, "_md_tool_buttons", []):
            try:
                btn.configure(bg=palette["SURFACE_2"], fg=palette["MUTED"])
                btn._normal_bg = palette["SURFACE_2"]
                btn._normal_fg = palette["MUTED"]
            except tk.TclError:
                pass
        update_frontmatter = getattr(self, "_update_frontmatter_button_state", None)
        if update_frontmatter is not None:
            update_frontmatter()

    def _suspend_theme_redraw(self, roots: list[tk.Misc]) -> list[int]:
        window_handle = getattr(self, "_window_handle", None)
        if window_handle is None:
            return []
        handles: list[int] = []
        for window in roots:
            try:
                handle = int(window_handle(window))
            except (TypeError, ValueError, tk.TclError):
                continue
            if handle and set_window_redraw(handle, False):
                handles.append(handle)
        return handles

    @staticmethod
    def _resume_theme_redraw(handles: list[int]) -> None:
        # Resume all neighbouring top-levels before invalidating any of them,
        # so Windows cannot compose a frame containing mixed theme colors.
        for handle in handles:
            set_window_redraw(handle, True)
        for handle in handles:
            redraw_window(handle)

    def _apply_theme(self, name: str, *, rerender_read: bool = True, flush: bool = True) -> None:
        if name == getattr(self, "_active_theme", None) and rerender_read and flush:
            return
        old_palette = {key: globals()[key] for key in theme_module.PALETTE_KEYS}
        new_palette = self._set_theme_globals(name)
        if not hasattr(self, "root"):
            return

        roots: list[tk.Misc] = [self.root]
        for window_name in ("explorer", "nav"):
            window = getattr(self, window_name, None)
            if window is not None:
                roots.append(window)
        try:
            roots.extend(child for child in self.root.winfo_children() if isinstance(child, tk.Toplevel))
        except tk.TclError:
            pass

        redraw_handles = self._suspend_theme_redraw(roots)
        if redraw_handles:
            # Scheduling the release first also guarantees redraw is restored if
            # a later widget has already been destroyed and raises unexpectedly.
            self.root.after_idle(lambda handles=redraw_handles: self._resume_theme_redraw(handles))
        self._apply_top_chrome_theme(new_palette)

        seen: set[str] = set()
        for widget in roots:
            try:
                widget_id = str(widget)
            except tk.TclError:
                continue
            if widget_id in seen:
                continue
            seen.add(widget_id)
            self._recolor_widget_tree(widget, old_palette, new_palette, widget is getattr(self, "explorer", None))

        self.root.configure(bg=new_palette["BG"])
        if hasattr(self, "explorer"):
            self._apply_explorer_theme()
        if hasattr(self, "nav"):
            self.nav.configure(bg=new_palette["ACCENT"])
            if hasattr(self, "nav_canvas"):
                self.nav_canvas.configure(bg=new_palette["ACCENT"])
            self._refresh_nav_bar_visual()
        if hasattr(self, "text"):
            self.text.configure(
                bg=new_palette["BG"],
                fg=new_palette["MUTED"] if self._showing_placeholder else new_palette["TEXT"],
                insertbackground=new_palette["ACCENT"],
                selectbackground=new_palette["ACCENT"],
                selectforeground=self._contrast_text(new_palette["ACCENT"]),
            )
            self._configure_editor_markdown_tags()
            self.text.tag_configure("find_match", background=new_palette["FIND_MATCH"], foreground=new_palette["TEXT"])
            self.text.tag_configure("find_current", background=new_palette["ACCENT"], foreground=self._contrast_text(new_palette["ACCENT"]))
            self.text.tag_configure("outline_current", background=new_palette["OUTLINE_CURRENT"], foreground=new_palette["TEXT"])
        if hasattr(self, "read_text"):
            self.read_text.configure(bg=new_palette["BG"], fg=new_palette["TEXT"])
            if rerender_read:
                self._render_read_content()
            self.read_text.tag_configure("find_match", background=new_palette["FIND_MATCH"], foreground=new_palette["TEXT"])
            self.read_text.tag_configure("find_current", background=new_palette["ACCENT"], foreground=self._contrast_text(new_palette["ACCENT"]))
            self.read_text.tag_configure("outline_current", background=new_palette["OUTLINE_CURRENT"], foreground=new_palette["TEXT"])
        if hasattr(self, "note_split"):
            self.note_split.configure(bg=new_palette["BORDER"])
        if hasattr(self, "_refresh_split_note_panes"):
            self._refresh_split_note_panes(rerender=rerender_read)
        if hasattr(self, "status_label"):
            self.status_label.configure(fg=new_palette["MUTED"])
        if hasattr(self, "view_toggle_btn"):
            self._update_view_buttons(relayout=False)
        if hasattr(self, "panel_resize_handle"):
            active_kind = getattr(self, "_width_resize_kind", None)
            self.panel_resize_handle.configure(
                bg=globals()["ACCENT_2"] if active_kind == "panel" else globals()["BORDER"]
            )
            self.explorer_resize_handle.configure(
                bg=globals()["ACCENT_2"] if active_kind == "explorer" else globals()["SIDEBAR_BORDER"]
            )
        if hasattr(self, "line_number_canvas"):
            self._schedule_editor_structure_refresh()
        if hasattr(self, "_refresh_plugin_window_theme"):
            self._refresh_plugin_window_theme()
        if hasattr(self, "_refresh_pedigree_plugin_theme"):
            self._refresh_pedigree_plugin_theme()
        try:
            from ..builtin_plugins.sticky_notes import refresh_sticky_notes_theme

            refresh_sticky_notes_theme(self)
        except Exception:
            pass
        if flush:
            self.root.update_idletasks()

    def _apply_header_alignment(self) -> None:
        if not hasattr(self, "title_group"):
            return
        for widget in (self.menu_btn, self.close_btn, self.plugins_btn, self.title_group):
            widget.pack_forget()
        if self.config.app_position == "left":
            self.app_title_label.config(anchor="e")
            if hasattr(self, "note_title"):
                self.note_title.config(anchor="e")
            self.close_btn.pack(side="left", padx=(8, 2))
            self.plugins_btn.pack(side="left", padx=2)
            self.menu_btn.pack(side="right", padx=(4, 8))
            self.title_group.pack(side="left", fill="x", expand=True)
        else:
            self.app_title_label.config(anchor="w")
            if hasattr(self, "note_title"):
                self.note_title.config(anchor="w")
            self.menu_btn.pack(side="left", padx=(8, 4))
            self.close_btn.pack(side="right", padx=(2, 8))
            self.plugins_btn.pack(side="right", padx=2)
            self.title_group.pack(side="left", fill="x", expand=True)
