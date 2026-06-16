from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import colorchooser, messagebox

from ..config import APP_NAME, save_config
from ..frontmatter import ensure_front_matter, split_front_matter
from ..hotkeys import format_hotkey_display
from ..i18n import command_label, t
from ..editor_images import (
    EDITOR_IMAGE_ELIDE_TAG,
    EditorImageBlock,
    load_preview_photo,
    plan_editor_image_blocks,
)
from ..live_highlight import (
    MD_EDITOR_TAGS,
    apply_live_highlight_plan,
    plan_live_highlight,
)
from ..markdown import render_markdown
from ..preview import render_file_preview
from ..storage import safe_write_text  # Fix #7: moved from lazy import inside _save_note
from ..text_files import is_markdown_note
from ..theme import *  # noqa: F401,F403

# Fix #6: module-level constant — single source of truth for all MD tag name lists
_MD_EDITOR_TAGS: tuple[str, ...] = MD_EDITOR_TAGS


class EditorMixin:
    # ── Markdown tag configuration ──────────────────────────────────────────

    def _configure_editor_markdown_tags(self) -> None:
        family = self.config.font_family or "Segoe UI"
        delta = self.config.font_size - 10
        g = globals()
        self.text.tag_configure("md_h1", font=(family, 18 + delta, "bold"), foreground=g["TEXT"], spacing3=6)
        self.text.tag_configure("md_h2", font=(family, 16 + delta, "bold"), foreground=g["TEXT"], spacing3=5)
        self.text.tag_configure("md_h3", font=(family, 14 + delta, "bold"), foreground=g["TEXT"], spacing3=4)
        self.text.tag_configure("md_h4", font=(family, 13 + delta, "bold"), foreground=g["TEXT"], spacing3=3)
        self.text.tag_configure("md_h5", font=(family, 12 + delta, "bold"), foreground=g["TEXT_SOFT"], spacing3=3)
        self.text.tag_configure("md_h6", font=(family, 11 + delta, "bold"), foreground=g["MUTED"], spacing3=2)
        self.text.tag_configure("md_bold", font=(family, 13 + delta, "bold"), foreground=g["TEXT"])
        self.text.tag_configure("md_italic", font=(family, 13 + delta, "italic"), foreground=g["TEXT_SOFT"])
        self.text.tag_configure("md_underline", underline=True, foreground=g["TEXT"])
        self.text.tag_configure("md_strike", overstrike=True, foreground=g["TEXT_SOFT"])
        self.text.tag_configure("md_highlight", background=g["HIGHLIGHT_BG"], foreground=g["HIGHLIGHT_FG"])
        self.text.tag_configure("md_sup", font=(family, 10 + delta), offset=4, foreground=g["TEXT"])
        self.text.tag_configure("md_sub", font=(family, 10 + delta), offset=-3, foreground=g["TEXT"])
        self.text.tag_configure("md_code", font=("Consolas", 12 + delta), background=g["CODE_BG"], foreground=g["CODE_TEXT"])
        self.text.tag_configure("md_link", foreground=g["LINK"], underline=True)
        self.text.tag_configure("md_image", foreground=g["IMAGE_LINK"], underline=True)
        self.text.tag_configure("md_quote", foreground=g["QUOTE"], lmargin1=18, lmargin2=18)
        self.text.tag_configure("md_list", lmargin1=22, lmargin2=22)
        self.text.tag_configure("md_task", lmargin1=22, lmargin2=22)
        self.text.tag_configure("md_task_done", lmargin1=22, lmargin2=22, foreground=g["MUTED"], overstrike=True)
        self.text.tag_configure("md_table", font=("Consolas", 11 + delta), foreground=g["TEXT_SOFT"])
        self.text.tag_configure("md_hr", foreground=g["MUTED"])
        self.text.tag_configure("md_frontmatter",
            font=("Consolas", 10 + delta),
            foreground=g["MUTED"],
            background=g["SURFACE_2"],
            lmargin1=8,
            lmargin2=8,
        )
        self.text.tag_configure("md_obsidian_tag", foreground=g["ACCENT_2"])
        self.text.tag_configure("md_callout", background=g["SURFACE_2"], foreground=g["TEXT"])
        self.text.tag_configure("md_comment", foreground=g["DISABLED"], overstrike=True)
        self.text.tag_configure(EDITOR_IMAGE_ELIDE_TAG, elide=True)
        # Keep find/selection highlights above the content tags, otherwise
        # md_code / md_highlight backgrounds hide them
        for tag in ("find_match", "find_current", "outline_current", "sel"):
            try:
                self.text.tag_raise(tag)
            except tk.TclError:
                pass
        self._schedule_editor_structure_refresh()

    def _clear_editor_markdown_tags(self) -> None:
        self._clear_editor_image_previews()
        # Fix #6: use module-level constant instead of a duplicated inline tuple
        for tag in (*_MD_EDITOR_TAGS, *getattr(self, "_editor_color_tags", set())):
            self.text.tag_remove(tag, "1.0", tk.END)
        self._editor_color_tags.clear()

    def _is_markdown_document(self) -> bool:
        return bool(self.current_note_path and is_markdown_note(self.current_note_path))

    def _schedule_live_render(self) -> None:
        if self.view_mode != "edit":
            return
        if getattr(self, "_editor_image_preview_busy", False):
            return
        if self._live_render_after is not None:
            self.root.after_cancel(self._live_render_after)
        self._live_render_after = self.root.after(80, self._apply_live_render)

    def _apply_live_render(self) -> None:
        self._live_render_after = None
        if self.view_mode != "edit" or self._showing_placeholder:
            return
        if not self.current_note_path or not is_markdown_note(self.current_note_path):
            self._clear_editor_markdown_tags()
            self._schedule_editor_structure_refresh(reapply_folds=True)
            return
        self._configure_editor_markdown_tags()
        content = self.text.get("1.0", "end-1c")
        try:
            focus_line = int(str(self.text.index("insert")).split(".")[0])
        except (tk.TclError, ValueError):
            focus_line = None

        plan = plan_live_highlight(content, focus_line=focus_line)
        clear_range = plan.line_range if plan.partial else None
        apply_live_highlight_plan(
            self.text,
            plan,
            clear_tags=_MD_EDITOR_TAGS,
            clear_line_range=clear_range,
            validate_color=self._validate_editor_color,
            configure_color_tag=self._configure_editor_color_tag,
            editor_color_tags=self._editor_color_tags,
        )
        for tag in ("find_match", "find_current", "outline_current", "sel"):
            try:
                self.text.tag_raise(tag)
            except tk.TclError:
                pass
        self._apply_editor_image_previews(content)
        self._schedule_editor_structure_refresh(reapply_folds=True)

    def _schedule_editor_image_width_refresh(self) -> None:
        if self.view_mode != "edit" or self._editor_image_preview_busy:
            return
        if not self._editor_image_previews:
            return
        if self._editor_image_width_after is not None:
            try:
                self.root.after_cancel(self._editor_image_width_after)
            except tk.TclError:
                pass
        self._editor_image_width_after = self.root.after(250, self._refresh_editor_image_widths)

    def _refresh_editor_image_widths(self) -> None:
        self._editor_image_width_after = None
        if self.view_mode != "edit" or self._showing_placeholder:
            return
        try:
            max_width = max(180, self.text.winfo_width() - 48)
        except tk.TclError:
            return
        if max_width == self._editor_image_last_width:
            return
        self._editor_image_last_width = max_width
        self._apply_editor_image_previews()

    def _remove_editor_image_preview(self, key: str) -> None:
        preview = self._editor_image_previews.pop(key, None)
        if not preview:
            return
        window_index = preview.get("window_index")
        block = preview.get("block")
        if window_index:
            try:
                self.text.delete(window_index)
            except tk.TclError:
                pass
        if block is not None:
            try:
                md_end = self.text.index(f"{block.start} + {len(block.markdown)}c")
                self.text.tag_remove(EDITOR_IMAGE_ELIDE_TAG, block.start, md_end)
            except tk.TclError:
                pass

    def _clear_editor_image_previews(self) -> None:
        if not hasattr(self, "text"):
            return
        for key in list(getattr(self, "_editor_image_previews", {}).keys()):
            self._remove_editor_image_preview(key)
        self._editor_preview_photos = []
        self._editor_image_last_width = None
        self._editor_image_preview_state = None
        try:
            self.text.tag_remove(EDITOR_IMAGE_ELIDE_TAG, "1.0", tk.END)
        except tk.TclError:
            pass

    def _apply_editor_image_previews(self, content: str | None = None) -> None:
        if self.view_mode != "edit" or self._showing_placeholder:
            self._clear_editor_image_previews()
            return
        if not self.current_note_path or not is_markdown_note(self.current_note_path):
            self._clear_editor_image_previews()
            return
        if content is None:
            content = self.text.get("1.0", "end-1c")
        blocks = plan_editor_image_blocks(
            content,
            self.current_note_path,
            wiki_asset_resolver=self._wiki_asset_resolver,
        )
        self._editor_image_blocks = {block.key: block for block in blocks}
        self.text.update_idletasks()
        try:
            max_width = max(180, self.text.winfo_width() - 48)
        except tk.TclError:
            max_width = 180
        editing_keys = self._editor_image_editing_keys
        desired_keys = {block.key for block in blocks if block.key not in editing_keys}
        signature = tuple((block.key, block.markdown, str(block.image_path)) for block in blocks)
        preview_state = (signature, max_width, frozenset(editing_keys), frozenset(self._editor_image_previews.keys()))
        if preview_state == getattr(self, "_editor_image_preview_state", None):
            return
        self._editor_image_preview_busy = True
        try:
            for key in list(self._editor_image_previews.keys()):
                if key not in desired_keys:
                    self._remove_editor_image_preview(key)
            for block in blocks:
                if block.key not in desired_keys:
                    continue
                preview = self._editor_image_previews.get(block.key)
                if (
                    preview
                    and preview.get("markdown") == block.markdown
                    and preview.get("max_width") == max_width
                    and preview.get("image_path") == str(block.image_path)
                ):
                    continue
                if preview:
                    self._remove_editor_image_preview(block.key)
                self._insert_editor_image_preview(block, max_width)
            self._editor_image_last_width = max_width
            self._editor_image_preview_state = (
                signature,
                max_width,
                frozenset(editing_keys),
                frozenset(self._editor_image_previews.keys()),
            )
        finally:
            self._editor_image_preview_busy = False

    def _insert_editor_image_preview(self, block: EditorImageBlock, max_width: int) -> None:
        photo = load_preview_photo(block.image_path, max_width)
        if photo is None:
            return
        self._editor_preview_photos.append(photo)
        g = globals()
        outer = tk.Frame(
            self.text,
            bg=g["BG"],
            highlightthickness=2,
            highlightbackground=g["BG"],
        )
        image_label = tk.Label(outer, image=photo, bg=g["BG"], cursor="hand2", borderwidth=0)
        image_label.pack()
        toolbar = tk.Frame(
            outer,
            bg=g["SURFACE"],
            highlightthickness=1,
            highlightbackground=g["BORDER"],
        )
        edit_btn = tk.Label(
            toolbar,
            text="</>",
            bg=g["SURFACE"],
            fg=g["MUTED"],
            font=("Consolas", 10),
            cursor="hand2",
            padx=4,
            pady=1,
        )
        tip_label = tk.Label(
            toolbar,
            text=t("editor.edit_image"),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 9),
            padx=4,
            pady=1,
        )
        edit_btn.pack(side="left")
        tip_label.pack(side="left", padx=(0, 4))
        toolbar.place_forget()

        def show_toolbar(_event=None) -> None:
            outer.config(highlightbackground=g["ACCENT"])
            if not toolbar.winfo_ismapped():
                toolbar.place(relx=1.0, rely=0.0, anchor="ne", x=-4, y=4)

        def hide_toolbar(_event=None) -> None:
            outer.config(highlightbackground=g["BG"])
            if toolbar.winfo_ismapped():
                toolbar.place_forget()
            edit_btn.config(fg=g["MUTED"])

        def on_edit(_event=None) -> None:
            self._show_editor_image_source(block)

        outer.bind("<Enter>", show_toolbar, add="+")
        outer.bind("<Leave>", hide_toolbar, add="+")
        edit_btn.bind("<Enter>", lambda _e: edit_btn.config(fg=g["TEXT"]), add="+")
        edit_btn.bind("<Leave>", lambda _e: edit_btn.config(fg=g["MUTED"]), add="+")
        edit_btn.bind("<Button-1>", on_edit)
        image_label.bind("<Button-1>", on_edit)

        try:
            if self.text.compare(block.start, ">", tk.END):
                return
            self.text.window_create(block.start, window=outer, stretch=True)
            md_start = self.text.index(f"{block.start} + 1c")
            md_end = self.text.index(f"{md_start} + {len(block.markdown)}c")
            self.text.tag_add(EDITOR_IMAGE_ELIDE_TAG, md_start, md_end)
            self._editor_image_previews[block.key] = {
                "window_index": block.start,
                "block": block,
                "markdown": block.markdown,
                "max_width": max_width,
                "image_path": str(block.image_path),
            }
        except tk.TclError:
            outer.destroy()

    def _show_editor_image_source(self, block: EditorImageBlock) -> None:
        self._editor_image_editing_keys.add(block.key)
        self._remove_editor_image_preview(block.key)
        try:
            md_start = block.start
            md_end = self.text.index(f"{md_start} + {len(block.markdown)}c")
            self.text.tag_add(tk.SEL, md_start, md_end)
            self.text.mark_set(tk.INSERT, md_end)
            self.text.focus_set()
        except tk.TclError:
            pass

    def _on_editor_image_click_outside(self, _event) -> None:
        if not getattr(self, "_editor_image_editing_keys", None):
            return
        if not self._editor_image_editing_keys:
            return
        try:
            index = self.text.index("insert")
            insert_line = int(str(index).split(".")[0])
        except (tk.TclError, ValueError):
            return
        changed = False
        for key in list(self._editor_image_editing_keys):
            block = self._editor_image_blocks.get(key)
            if block is None or insert_line != block.line:
                self._editor_image_editing_keys.discard(key)
                changed = True
        if changed:
            self._apply_editor_image_previews()

    def _exit_editor_image_source_mode(self) -> bool:
        if not getattr(self, "_editor_image_editing_keys", None):
            return False
        if not self._editor_image_editing_keys:
            return False
        self._editor_image_editing_keys.clear()
        self._editor_image_preview_state = None
        if self.view_mode == "edit":
            self._apply_editor_image_previews()
        return True

    def _validate_editor_color(self, color: str) -> bool:
        try:
            self.text.winfo_rgb(color)
        except tk.TclError:
            return False
        return True

    def _configure_editor_color_tag(self, tag: str, color: str) -> None:
        family = self.config.font_family or "Segoe UI"
        self.text.tag_configure(
            tag,
            foreground=color,
            font=(family, self.config.font_size + 3),
        )

    # ── Autosave & save ─────────────────────────────────────────────────────

    def _schedule_autosave(self) -> None:
        if not self.config.auto_save:
            return
        if self._autosave_after is not None:
            self.root.after_cancel(self._autosave_after)
        self._autosave_after = self.root.after(self.config.auto_save_delay_ms, lambda: self._save_note(False))

    def _save_note(self, show_indicator: bool = False) -> None:
        if not self.current_note_path:
            return
        if not show_indicator and not self._dirty:
            return  # nothing changed — skip disk writes (keeps close animation smooth)
        content = self._get_editor_content()
        try:
            # Fix #7: safe_write_text is now imported at the top of the module
            safe_write_text(
                self.current_note_path,
                content,
                encoding=self._document_encoding,
                newline=self._document_newline,
                workspace_root=self._workspace_dir(),
            )
        except OSError as exc:
            self._set_error(t("error.save_failed", exc=exc))
            return
        self._dirty = False
        if self._autosave_after is not None:
            try:
                self.root.after_cancel(self._autosave_after)
            except tk.TclError:
                pass
            self._autosave_after = None
        self._set_status_key("status.saved")
        if show_indicator:
            self.save_indicator.config(text=t("status.saved"))
            self.root.after(1400, lambda: self.save_indicator.config(text=""))
        markdown_note = is_markdown_note(self.current_note_path)
        self.config.current_note_path = str(self.current_note_path) if markdown_note else ""
        save_config(self.config)
        if markdown_note:
            self._schedule_tag_refresh()
            self._schedule_wiki_index_refresh()

    # ── Editor content helpers ───────────────────────────────────────────────

    def _get_editor_content(self) -> str:
        if self._showing_placeholder:
            return ""
        return self.text.get("1.0", "end-1c")

    def _set_editor_content(self, content: str) -> None:
        self._showing_placeholder = False
        self._editor_image_editing_keys.clear()
        self._editor_image_preview_state = None
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text.edit_modified(False)
        self.text.config(fg=globals()["TEXT"])
        self._maybe_show_placeholder()
        self._apply_live_render()
        self._schedule_editor_structure_refresh(reapply_folds=True)

    def _on_text_modified(self, _event) -> None:
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        if self._showing_placeholder:
            return
        self._dirty = True
        self._set_status_key("status.unsaved")
        self._schedule_live_render()
        self._schedule_autosave()

    # ── Placeholder ──────────────────────────────────────────────────────────

    def _clear_placeholder(self) -> None:
        if self._showing_placeholder:
            self.text.delete("1.0", tk.END)
            self.text.config(fg=globals()["TEXT"])
            self._showing_placeholder = False

    def _maybe_show_placeholder(self) -> None:
        if self.view_mode != "edit":
            return
        if not self.text.get("1.0", "end-1c").strip():
            self.text.insert("1.0", self._placeholder_text)
            self.text.config(fg=globals()["MUTED"])
            self._showing_placeholder = True

    def _update_hotkey_hints(self) -> None:
        self._placeholder_text = (
            t("editor.placeholder_title")
            + "\n\n"
            + t("editor.placeholder_body")
            + "\n\n"
            + t("editor.placeholder_footer", hotkey=format_hotkey_display(self.config.hotkey))
        )
        if hasattr(self, "status_label"):
            self._set_status_key("status.ready")

    # ── Text selection helpers ────────────────────────────────────────────────

    def _selected_text(self, widget: tk.Text) -> str:
        try:
            return widget.get("sel.first", "sel.last")
        except tk.TclError:
            return ""

    def _selection_range(self, placeholder: str = "text") -> tuple[str, str, str]:
        try:
            if self.text.tag_ranges(tk.SEL):
                return self.text.index(tk.SEL_FIRST), self.text.index(tk.SEL_LAST), self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        cursor = self.text.index(tk.INSERT)
        return cursor, cursor, placeholder

    def _selected_line_range(self) -> tuple[str, str]:
        try:
            if self.text.tag_ranges(tk.SEL):
                start = self.text.index(f"{tk.SEL_FIRST} linestart")
                selection_end = self.text.index(tk.SEL_LAST)
                _end_line, end_column = selection_end.split(".")
                if end_column == "0" and self.text.compare(selection_end, ">", start):
                    end = self.text.index(f"{selection_end}-1c lineend")
                else:
                    end = self.text.index(f"{selection_end} lineend")
                return start, end
        except tk.TclError:
            pass
        line = self.text.index(tk.INSERT).split(".")[0]
        return f"{line}.0", f"{line}.end"

    # ── Formatting commands ───────────────────────────────────────────────────

    def _wrap_selection(self, before: str, after: str, placeholder: str = "text") -> None:
        if self.view_mode != "edit":
            return
        self._clear_placeholder()
        start, end, selected = self._selection_range(placeholder)
        self.text.delete(start, end)
        self.text.insert(start, before + selected + after)
        inner_start = f"{start}+{len(before)}c"
        inner_end = f"{start}+{len(before) + len(selected)}c"
        self.text.tag_add(tk.SEL, inner_start, inner_end)
        self.text.mark_set(tk.INSERT, inner_end)
        self.text.focus_set()

    def _line_prefix(self, prefix: str) -> None:
        if self.view_mode != "edit":
            return
        self._clear_placeholder()
        line = self.text.index(tk.INSERT).split(".")[0]
        line_start = f"{line}.0"
        content = self.text.get(line_start, f"{line}.end")
        if content.startswith(prefix):
            self.text.delete(line_start, f"{line}.0+{len(prefix)}c")
        else:
            self.text.insert(line_start, prefix)
        self.text.focus_set()

    def _insert_text(self, snippet: str) -> None:
        if self.view_mode != "edit":
            return
        self._clear_placeholder()
        self.text.insert(tk.INSERT, snippet)
        self.text.focus_set()

    def _set_heading(self, level: int) -> None:
        if self.view_mode != "edit":
            return
        self._clear_placeholder()
        start, end = self._selected_line_range()
        content = self.text.get(start, end)
        lines = content.splitlines()
        prefix = "#" * level + " " if level else ""
        updated = [prefix + re.sub(r"^#{1,6}\s+", "", line) for line in lines]
        self.text.delete(start, end)
        self.text.insert(start, "\n".join(updated))
        self.text.focus_set()

    def _apply_list_format(self, kind: str) -> None:
        if self.view_mode != "edit":
            return
        self._clear_placeholder()
        start, end = self._selected_line_range()
        lines = self.text.get(start, end).splitlines() or [""]
        prefix_pattern = re.compile(r"^\s*(?:[-*+]\s+\[[ xX]\]\s+|[-*+]\s+|\d+\.\s+)")
        cleaned = [prefix_pattern.sub("", line) for line in lines]
        if kind == "ordered":
            updated = [f"{index}. {line}" for index, line in enumerate(cleaned, start=1)]
        elif kind == "task":
            updated = [f"- [ ] {line}" for line in cleaned]
        else:
            updated = [f"- {line}" for line in cleaned]
        self.text.delete(start, end)
        self.text.insert(start, "\n".join(updated))
        self.text.focus_set()

    def _on_editor_return(self, _event=None) -> str | None:
        """Auto-close a code fence: pressing Enter at the end of a ``` line
        inserts the closing fence and puts the caret inside the block."""
        if self._accept_wiki_completion() == "break":
            return "break"
        if self._showing_placeholder or self.view_mode != "edit":
            return None
        insert_line = int(self.text.index(tk.INSERT).split(".")[0])
        line_text = self.text.get(f"{insert_line}.0", f"{insert_line}.end")
        if not re.fullmatch(r"\s*```[^`]*", line_text):
            return None
        if self.text.compare(tk.INSERT, "!=", f"{insert_line}.end"):
            return None  # caret mid-line — normal newline
        lines = self._get_editor_content().splitlines()
        fences_through = sum(1 for line in lines[:insert_line] if line.strip().startswith("```"))
        if fences_through % 2 == 0:
            return None  # this ``` closes a block — normal newline
        fences_below = sum(1 for line in lines[insert_line:] if line.strip().startswith("```"))
        if fences_below % 2 == 1:
            return None  # a matching closing fence already exists
        self.text.insert(tk.INSERT, "\n\n```")
        self.text.mark_set(tk.INSERT, f"{insert_line + 1}.0")
        self.text.see(tk.INSERT)
        return "break"

    def _smart_code_format(self) -> None:
        start, end, selected = self._selection_range("code")
        if "\n" not in selected:
            self._wrap_selection("`", "`", "code")
            return
        self._clear_placeholder()
        block = f"```\n{selected.strip()}\n```"
        self.text.delete(start, end)
        self.text.insert(start, block)
        self.text.mark_set(tk.INSERT, f"{start}+{len(block)}c")
        self.text.focus_set()

    def _insert_markdown_table(self) -> None:
        self._insert_text(
            "\n| Column 1 | Column 2 | Column 3 |\n"
            "| --- | --- | --- |\n"
            "| Cell | Cell | Cell |\n"
        )

    def _ensure_current_front_matter(self) -> None:
        if self.preview_path is not None:
            self._close_file_preview(restore_note=True)
        if self.view_mode != "edit":
            self._switch_to_edit()
        if not self.current_note_path:
            self._set_error(t("error.frontmatter_need_note"))
            return
        self._clear_placeholder()
        content = self._get_editor_content()
        header, body = split_front_matter(content)
        if header is None:
            content, _created = ensure_front_matter(content, self.current_note_path.stem)
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", content)
            self.text.edit_modified(False)
            self._dirty = True
            self._schedule_live_render()
            self._schedule_autosave()
            header, body = split_front_matter(content)
        span = max(1, len(content) - len(body))
        self.text.tag_remove(tk.SEL, "1.0", tk.END)
        self.text.tag_add(tk.SEL, "1.0", f"1.0+{span}c")
        self.text.mark_set(tk.INSERT, f"1.0+{span}c")
        self.text.see("1.0")
        self.text.focus_set()

    def _copy_selected_text(self) -> None:
        if self._selected_text(self.text):
            self.text.event_generate("<<Copy>>")

    def _clear_selected_markdown(self) -> None:
        selected = self._selected_text(self.text)
        if not selected:
            return
        try:
            start = self.text.index(tk.SEL_FIRST)
            end = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", selected)
        cleaned = re.sub(r"</?(?:u|sup|sub)>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"</?(?:span|font)\b[^>]*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"~~(.+?)~~", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"==(.+?)==", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"(?m)^(?:#{1,6}\s+|[-*+]\s+\[[ xX]\]\s+|[-*+]\s+|\d+\.\s+|>\s+)", "", cleaned)
        self.text.delete(start, end)
        self.text.insert(start, cleaned)
        cleaned_end = f"{start}+{len(cleaned)}c"
        self.text.tag_add(tk.SEL, start, cleaned_end)
        self.text.mark_set(tk.INSERT, cleaned_end)
        self.text.focus_set()

    # ── Heading / more-format popups ─────────────────────────────────────────

    def _show_heading_popup(self, anchor: tk.Widget) -> None:
        self._hide_tooltip()
        g = globals()
        menu = tk.Menu(
            self.root,
            tearoff=False,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            activebackground=g["ACCENT"],
            activeforeground=self._contrast_text(g["ACCENT"]),
            borderwidth=1,
            relief="solid",
            font=("Segoe UI", 11),
        )
        for level in range(1, 7):
            title = t("cmd.heading_primary") if level == 1 else t("cmd.heading_secondary")
            menu.add_command(
                label=f"H{level}  {title}",
                command=lambda value=level: self._finish_popup_format(lambda: self._set_heading(value)),
            )
        menu.add_separator()
        menu.add_command(
            label=f"T  {t('cmd.normal_text')}",
            command=lambda: self._finish_popup_format(lambda: self._set_heading(0)),
        )
        menu.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height() + 3)

    def _apply_text_color(self, color: str) -> None:
        self._wrap_selection(f'<span style="color: {color}">', "</span>", "text")

    def _show_text_color_popup(self, anchor: tk.Widget) -> None:
        self._hide_tooltip()
        g = globals()
        menu = tk.Menu(
            self.root,
            tearoff=False,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            activebackground=g["ACCENT"],
            activeforeground=self._contrast_text(g["ACCENT"]),
            borderwidth=1,
            relief="solid",
            font=("Segoe UI", 11),
        )
        for label, color in (
            ("Red", "#e05252"),
            ("Orange", "#d97706"),
            ("Yellow", "#c59a00"),
            ("Green", "#2f9e64"),
            ("Blue", "#3b82f6"),
            ("Purple", "#8b5cf6"),
            ("Pink", "#db4b91"),
            ("Muted", g["MUTED"]),
        ):
            menu.add_command(
                label=f"■  {label}",
                foreground=color,
                command=lambda value=color: self._finish_popup_format(lambda: self._apply_text_color(value)),
            )

        def choose_custom() -> None:
            _rgb, selected = colorchooser.askcolor(parent=self.root, title=t("dialog.text_color"))
            if selected:
                self._apply_text_color(selected)

        menu.add_separator()
        menu.add_command(label="Custom color...", command=lambda: self._finish_popup_format(choose_custom))
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 3
        try:
            selected_end = self.text.index(f"{tk.SEL_LAST}-1c")
            bounds = self.text.bbox(selected_end)
            if bounds:
                x = self.text.winfo_rootx() + bounds[0]
                y = self.text.winfo_rooty() + bounds[1] + bounds[3] + 6
        except tk.TclError:
            try:
                bounds = self.text.bbox(tk.INSERT)
                if bounds:
                    x = self.text.winfo_rootx() + bounds[0]
                    y = self.text.winfo_rooty() + bounds[1] + bounds[3] + 6
            except tk.TclError:
                pass
        menu.update_idletasks()
        menu_width = max(150, menu.winfo_reqwidth())
        menu_height = max(100, menu.winfo_reqheight())
        x = max(self.work_left + 4, min(x, self.work_right - menu_width - 4))
        if y + menu_height > self.work_bottom - 4:
            y = max(self.work_top + 4, y - menu_height - 22)
        menu.tk_popup(x, y)

    def _show_more_format_popup(self, anchor: tk.Widget) -> None:
        self._hide_tooltip()
        g = globals()
        menu = tk.Menu(
            self.root,
            tearoff=False,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            activebackground=g["ACCENT"],
            activeforeground=self._contrast_text(g["ACCENT"]),
            borderwidth=1,
            relief="solid",
            font=("Segoe UI", 11),
        )
        visible = getattr(self, "_visible_format_keys", set())
        quick_anchor = anchor is getattr(self, "quick_more_btn", None)
        quick_visible = {"bold", "italic", "underline", "strike", "heading", "highlight", "code", "link"} if quick_anchor else visible
        for key, glyph, command in self._format_actions:
            if key in quick_visible:
                continue
            if key == "heading":
                action = lambda target=anchor: self._show_heading_popup(target)
            else:
                action = command
            menu.add_command(
                label=f"{glyph}  {command_label(key)}",
                command=lambda callback=action: self._finish_popup_format(callback),
            )
        menu.add_separator()
        menu.add_command(
            label=f"x²  {t('cmd.superscript')}",
            command=lambda: self._finish_popup_format(lambda: self._wrap_selection("<sup>", "</sup>", "text")),
        )
        menu.add_command(
            label=f"x₂  {t('cmd.subscript')}",
            command=lambda: self._finish_popup_format(lambda: self._wrap_selection("<sub>", "</sub>", "text")),
        )
        menu.add_separator()
        menu.add_command(
            label=f"📎  {t('dialog.insert_attachment')}",
            command=lambda: self._finish_popup_format(self._insert_attachment_file),
        )
        menu.add_command(
            label=f"🖼  {t('cmd.paste_clipboard_image')}",
            command=lambda: self._finish_popup_format(self._insert_clipboard_image),
        )
        menu.add_command(
            label=f"⌫  {t('cmd.clear_formatting')}",
            command=lambda: self._finish_popup_format(self._clear_selected_markdown),
        )
        menu.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height() + 3)

    def _finish_popup_format(self, command: Callable[[], None]) -> None:
        command()
        self._hide_quick_format()

    # ── Quick-format floating toolbar ────────────────────────────────────────

    def _quick_format_button(
        self,
        parent: tk.Widget,
        text: str,
        tooltip: str,
        command: Callable[[], None],
        icon_font: bool = False,
        close_after: bool = True,
    ) -> tk.Label:
        g = globals()
        button = tk.Label(
            parent,
            text=text,
            bg=g["SURFACE"],
            fg=g["TEXT_SOFT"],
            font=("Segoe MDL2 Assets", 11) if icon_font else ("Segoe UI", 10, "bold"),
            cursor="hand2",
            width=2,
            padx=4,
            pady=5,
        )
        button._normal_bg = g["SURFACE"]
        button._normal_fg = g["TEXT_SOFT"]
        if close_after:
            button.bind("<Button-1>", lambda _e: self._run_quick_format_action(command))
        else:
            button.bind("<Button-1>", lambda _e: command())
        button.bind("<Enter>", lambda _e: (button.config(bg=globals()["ACCENT"], fg=self._contrast_text(globals()["ACCENT"])), self._show_tooltip(button, tooltip)))
        button.bind("<Leave>", lambda _e: (button.config(bg=globals()["SURFACE"], fg=globals()["TEXT_SOFT"]), self._hide_tooltip()))
        return button

    def _build_quick_format_toolbar(self) -> None:
        g = globals()
        toolbar = tk.Toplevel(self.root)
        toolbar.overrideredirect(True)
        toolbar.attributes("-topmost", True)
        toolbar.configure(bg=g["BORDER"])
        toolbar.withdraw()
        shell = tk.Frame(toolbar, bg=g["SURFACE"], padx=3, pady=3)
        shell.pack(padx=1, pady=1)
        actions = (
            ("", "Copy", self._copy_selected_text, True, True, "copy"),
            ("B", "Bold", lambda: self._wrap_selection("**", "**", "bold"), False, True, "bold"),
            ("I", "Italic", lambda: self._wrap_selection("*", "*", "italic"), False, True, "italic"),
            ("U", "Underline", lambda: self._wrap_selection("<u>", "</u>", "text"), False, True, "underline"),
            ("S", "Strikethrough", lambda: self._wrap_selection("~~", "~~", "text"), False, True, "strike"),
            ("H", "Heading", lambda: self._show_heading_popup(self.quick_heading_btn), False, False, "heading"),
            ("==", "Highlight", lambda: self._wrap_selection("==", "==", "text"), False, True, "highlight"),
            ("<>", "Inline code / code block", self._smart_code_format, False, True, "code"),
            ("🔗", "Link", lambda: self._wrap_selection("[", "](url)", "text"), False, True, "link"),
            ("•••", "More formatting", lambda: self._show_more_format_popup(self.quick_more_btn), False, False, "more"),
        )
        for index, (label, tooltip, command, icon_font, close_after, key) in enumerate(actions):
            if index in {1, 5, 9}:
                tk.Frame(shell, bg=g["BORDER"], width=1).pack(side="left", fill="y", padx=3, pady=3)
            button = self._quick_format_button(shell, label, tooltip, command, icon_font, close_after)
            if key == "underline":
                button.configure(font=("Segoe UI", 10, "underline"))
            elif key == "italic":
                button.configure(font=("Segoe UI", 10, "italic"))
            elif key == "link":
                button.configure(font=("Segoe UI Emoji", 10))
            button.pack(side="left")
            if key == "heading":
                self.quick_heading_btn = button
            elif key == "more":
                self.quick_more_btn = button
        toolbar.bind("<Escape>", lambda _e: self._hide_quick_format())
        self.quick_format_toolbar = toolbar

    def _run_quick_format_action(self, command: Callable[[], None]) -> None:
        command()
        self._hide_tooltip()
        self._hide_quick_format()

    def _schedule_quick_format(self, _event=None) -> None:
        if self._quick_format_after is not None:
            try:
                self.root.after_cancel(self._quick_format_after)
            except tk.TclError:
                pass
        self._quick_format_after = self.root.after(35, self._show_quick_format)

    def _show_quick_format(self) -> None:
        self._quick_format_after = None
        if not self._is_markdown_document():
            self._hide_quick_format()
            return
        if self.view_mode != "edit" or not self.is_open or not self._selected_text(self.text):
            self._hide_quick_format()
            return
        try:
            bounds = self.text.bbox(tk.SEL_FIRST)
        except tk.TclError:
            bounds = None
        if not bounds:
            self._hide_quick_format()
            return
        toolbar = self.quick_format_toolbar
        toolbar.update_idletasks()
        width = max(1, toolbar.winfo_reqwidth())
        height = max(1, toolbar.winfo_reqheight())
        x = self.text.winfo_rootx() + bounds[0]
        y = self.text.winfo_rooty() + bounds[1] - height - 8
        if y < self.work_top + 4:
            y = self.text.winfo_rooty() + bounds[1] + bounds[3] + 8
        x = max(self.work_left + 4, min(x, self.work_right - width - 4))
        y = max(self.work_top + 4, min(y, self.work_bottom - height - 4))
        toolbar.geometry(f"+{x}+{y}")
        toolbar.deiconify()
        toolbar.lift()

    def _hide_quick_format(self) -> None:
        if self._quick_format_after is not None:
            try:
                self.root.after_cancel(self._quick_format_after)
            except tk.TclError:
                pass
            self._quick_format_after = None
        toolbar = getattr(self, "quick_format_toolbar", None)
        if toolbar is not None:
            try:
                toolbar.withdraw()
            except tk.TclError:
                pass

    # ── Find / replace panel ─────────────────────────────────────────────────

    def _build_find_panel(self) -> None:
        g = globals()
        self._find_tooltip_buttons: dict[str, tk.Label] = {}
        self.find_panel = tk.Frame(self.root, bg=g["SURFACE_2"])
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self._find_replace_visible = False
        self._find_current_index = None

        find_row = tk.Frame(self.find_panel, bg=g["SURFACE_2"])
        find_row.pack(fill="x", padx=8, pady=(7, 4))
        tk.Label(find_row, text="", bg=g["SURFACE_2"], fg=g["MUTED"], font=("Segoe MDL2 Assets", 11), width=2).pack(side="left")
        self.find_entry = tk.Entry(find_row, textvariable=self.find_var, bg=g["SURFACE"], fg=g["TEXT"], insertbackground=g["TEXT"], relief="flat", borderwidth=0, font=("Segoe UI", 10))
        self.find_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(2, 5))
        self.find_count_label = tk.Label(find_row, text="", bg=g["SURFACE_2"], fg=g["MUTED"], font=("Segoe UI", 9), width=7, anchor="e")
        self.find_count_label.pack(side="left", padx=(0, 4))
        self._mini_button(find_row, "↑", self._find_previous, "tooltip.find_prev").pack(side="left")
        self._mini_button(find_row, "↓", self._find_next, "tooltip.find_next").pack(side="left")
        self._mini_button(find_row, "↔", lambda: self._set_replace_visible(not self._find_replace_visible), "tooltip.find_replace_toggle").pack(side="left")
        self._mini_button(find_row, "×", self._hide_find_panel, "tooltip.find_close").pack(side="left")

        self.replace_row = tk.Frame(self.find_panel, bg=g["SURFACE_2"])
        tk.Label(self.replace_row, text="", bg=g["SURFACE_2"], fg=g["MUTED"], font=("Segoe UI", 10, "bold"), width=2).pack(side="left")
        self.replace_entry = tk.Entry(self.replace_row, textvariable=self.replace_var, bg=g["SURFACE"], fg=g["TEXT"], insertbackground=g["TEXT"], relief="flat", borderwidth=0, font=("Segoe UI", 10))
        self.replace_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(2, 5))
        self._mini_button(self.replace_row, "One", self._replace_current, "tooltip.replace_current").pack(side="left", padx=(0, 3))
        self._mini_button(self.replace_row, "All", self._replace_all, "tooltip.replace_all").pack(side="left")

        tk.Frame(self.find_panel, bg=g["BORDER"], height=1).pack(fill="x")
        self.find_var.trace_add("write", lambda *_: self._refresh_find_matches(True))
        self.find_entry.bind("<Return>", lambda _e: self._find_next() or "break")
        self.find_entry.bind("<Shift-Return>", lambda _e: self._find_previous() or "break")
        self.replace_entry.bind("<Return>", lambda _e: self._replace_current() or "break")
        self.find_panel.bind("<Escape>", lambda _e: self._hide_find_panel() or "break")
        self.find_entry.bind("<Escape>", lambda _e: self._hide_find_panel() or "break")
        self.replace_entry.bind("<Escape>", lambda _e: self._hide_find_panel() or "break")

    def _mini_button(self, parent: tk.Widget, text: str, command: Callable[[], None], tooltip_key: str = "") -> tk.Label:
        g = globals()
        btn = tk.Label(parent, text=text, bg=g["SURFACE_2"], fg=g["MUTED"], font=("Segoe UI", 9, "bold"), cursor="hand2", padx=6, pady=3)
        btn.bind("<Button-1>", lambda _e: command())
        tooltip = t(tooltip_key) if tooltip_key else ""
        btn._tooltip_text = tooltip
        if tooltip_key:
            self._find_tooltip_buttons = getattr(self, "_find_tooltip_buttons", {})
            self._find_tooltip_buttons[tooltip_key] = btn
        btn.bind("<Enter>", lambda _e: (btn.config(bg=globals()["BORDER"], fg=globals()["TEXT"]), self._show_tooltip(btn, getattr(btn, "_tooltip_text", tooltip))))
        btn.bind("<Leave>", lambda _e: (btn.config(bg=globals()["SURFACE_2"], fg=globals()["MUTED"]), self._hide_tooltip()))
        return btn

    def _active_text_widget(self) -> tk.Text:
        if self.preview_path is not None:
            return self.read_text
        return self.text if self.view_mode == "edit" else self.read_text

    def _toggle_find_panel(self, replace: bool = False) -> None:
        if self.find_panel.winfo_ismapped():
            self._hide_find_panel()
            return
        self._open_find_panel(replace)

    def _open_find_panel(self, replace: bool = False) -> None:
        if not self.find_panel.winfo_ismapped():
            self.find_panel.pack(fill="x", after=self.toolbar)
        self._set_replace_visible(replace or self._find_replace_visible)
        selection = self._selected_text(self._active_text_widget())
        if selection and "\n" not in selection and len(selection) <= 120:
            self.find_var.set(selection)
        self.find_entry.focus_set()
        self.find_entry.selection_range(0, tk.END)
        self._refresh_find_matches(True)

    def _set_replace_visible(self, visible: bool) -> None:
        self._find_replace_visible = visible
        if visible:
            self.replace_row.pack(fill="x", padx=8, pady=(0, 7))
        else:
            self.replace_row.pack_forget()

    def _hide_find_panel(self) -> None:
        if hasattr(self, "find_panel"):
            self.find_panel.pack_forget()
        self._clear_find_tags()
        self._find_current_index = None
        if self.view_mode == "edit":
            self.text.focus_set()
        else:
            self.read_text.focus_set()

    def _clear_find_tags(self) -> None:
        for widget in (getattr(self, "text", None), getattr(self, "read_text", None)):
            if widget is None:
                continue
            try:
                widget.tag_remove("find_match", "1.0", tk.END)
                widget.tag_remove("find_current", "1.0", tk.END)
            except tk.TclError:
                pass

    def _refresh_find_matches(self, select_first: bool = False) -> None:
        if not hasattr(self, "find_var"):
            return
        g = globals()
        widget = self._active_text_widget()
        needle = self.find_var.get()
        self._clear_find_tags()
        widget.tag_configure("find_match", background=g["FIND_MATCH"], foreground=g["TEXT"])
        widget.tag_configure("find_current", background=g["ACCENT"], foreground=self._contrast_text(g["ACCENT"]))
        if not needle:
            self.find_count_label.config(text="")
            return
        count_var = tk.IntVar()
        matches = []
        pos = "1.0"
        while True:
            idx = widget.search(needle, pos, stopindex=tk.END, nocase=True, count=count_var)
            if not idx:
                break
            length = count_var.get()
            if length <= 0:
                break
            end = f"{idx}+{length}c"
            widget.tag_add("find_match", idx, end)
            matches.append((idx, length))
            pos = end
        self.find_count_label.config(text=f"{len(matches)}" if matches else "0")
        if matches and select_first:
            self._select_find_result(matches[0][0], matches[0][1])

    def _select_find_result(self, index: str, length: int) -> None:
        widget = self._active_text_widget()
        widget.tag_remove("find_current", "1.0", tk.END)
        end = f"{index}+{length}c"
        widget.tag_add("find_current", index, end)
        widget.mark_set(tk.INSERT, end)
        widget.see(index)
        self._find_current_index = index

    def _find_next(self) -> None:
        if not self.find_panel.winfo_ismapped():
            self._open_find_panel(False)
            return
        self._find_step(forward=True)

    def _find_previous(self) -> None:
        if not self.find_panel.winfo_ismapped():
            self._open_find_panel(False)
            return
        self._find_step(forward=False)

    def _find_step(self, forward: bool = True) -> None:
        widget = self._active_text_widget()
        needle = self.find_var.get()
        if not needle:
            return
        count_var = tk.IntVar()
        if forward:
            start = widget.index(f"{tk.INSERT}+1c")
            idx = widget.search(needle, start, stopindex=tk.END, nocase=True, count=count_var)
            if not idx:
                idx = widget.search(needle, "1.0", stopindex=tk.END, nocase=True, count=count_var)
        else:
            start = widget.index(f"{tk.INSERT}-1c")
            idx = widget.search(needle, start, stopindex="1.0", backwards=True, nocase=True, count=count_var)
            if not idx:
                idx = widget.search(needle, tk.END, stopindex="1.0", backwards=True, nocase=True, count=count_var)
        self._refresh_find_matches(False)
        if idx:
            self._select_find_result(idx, count_var.get())

    def _replace_current(self) -> None:
        if self.view_mode != "edit":
            self._switch_to_edit()
        needle = self.find_var.get()
        replacement = self.replace_var.get()
        if not needle:
            return
        widget = self.text
        ranges = widget.tag_ranges("find_current")
        if len(ranges) < 2:
            self._find_next()
            ranges = widget.tag_ranges("find_current")
            if len(ranges) < 2:
                return
        start, end = ranges[0], ranges[1]
        widget.delete(start, end)
        widget.insert(start, replacement)
        widget.mark_set(tk.INSERT, f"{start}+{len(replacement)}c")
        self._dirty = True
        self._set_status_key("status.unsaved")
        self._schedule_live_render()
        self._schedule_autosave()
        self._refresh_find_matches(False)
        self._find_next()

    def _replace_all(self) -> None:
        if self.view_mode != "edit":
            self._switch_to_edit()
        needle = self.find_var.get()
        if not needle:
            return
        content = self._get_editor_content()
        pattern = re.compile(re.escape(needle), re.IGNORECASE)
        new_content, count = pattern.subn(self.replace_var.get(), content)
        if count == 0:
            return
        self._set_editor_content(new_content)
        self._dirty = True
        self._set_status_key("status.replaced", count=count)
        self._schedule_autosave()
        self._refresh_find_matches(True)

    # ── Outline popup ────────────────────────────────────────────────────────

    def _parse_outline(self) -> list[dict[str, int | str]]:
        headings: list[dict[str, int | str]] = []
        in_code_block = False
        content = self._get_editor_content()
        _header, body = split_front_matter(content)
        body_offset = content[: len(content) - len(body)].count("\n")
        for body_line_no, line in enumerate(body.splitlines(), start=1):
            line_no = body_line_no + body_offset
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if not match:
                continue
            title = self._plain_heading_text(match.group(2)).strip()
            if title:
                headings.append({"level": len(match.group(1)), "title": title, "line": line_no})
        return headings

    def _plain_heading_text(self, text: str) -> str:
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"</?(?:u|sup|sub)>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"(?:~~|==)", "", text)
        text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
        return text.strip()

    def _show_outline_popup(self) -> None:
        self._hide_tooltip()
        popup = getattr(self, "_outline_popup", None)
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
            self._outline_popup = None
            return
        g = globals()
        headings = self._parse_outline()
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=g["BORDER"])
        self._outline_popup = popup

        shell = tk.Frame(popup, bg=g["SURFACE_2"])
        shell.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(shell, bg=g["SURFACE_2"])
        header.pack(fill="x")
        tk.Label(header, text="Outline", bg=g["SURFACE_2"], fg=g["TEXT"], font=("Segoe UI", 10, "bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=(10, 4), pady=(8, 6))
        self._mini_button(header, "×", lambda: self._close_outline_popup(), "Close").pack(side="right", padx=(0, 6), pady=(6, 4))
        tk.Frame(shell, bg=g["BORDER"], height=1).pack(fill="x")

        list_frame = tk.Frame(shell, bg=g["SURFACE_2"])
        list_frame.pack(fill="both", expand=True, padx=4, pady=4)
        if not headings:
            tk.Label(list_frame, text="No headings", bg=g["SURFACE_2"], fg=g["MUTED"], font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=8, pady=10)
        else:
            for item in headings[:80]:
                level = int(item["level"])
                title = str(item["title"])
                line = int(item["line"])
                label = tk.Label(
                    list_frame,
                    text=title,
                    bg=g["SURFACE_2"],
                    fg=g["TEXT"] if level <= 2 else g["TEXT_SOFT"],
                    font=("Segoe UI", 9, "bold" if level == 1 else "normal"),
                    anchor="w",
                    cursor="hand2",
                    padx=8 + (level - 1) * 12,
                    pady=4,
                )
                label.pack(fill="x")
                label.bind("<Button-1>", lambda _e, target=line, name=title: self._jump_to_outline(target, name))
                label.bind("<Enter>", lambda _e, w=label: w.config(bg=globals()["BORDER"]))
                label.bind("<Leave>", lambda _e, w=label: w.config(bg=globals()["SURFACE_2"]))

        popup.update_idletasks()
        width = min(300, max(240, self.panel_w - 24))
        height = min(max(110, popup.winfo_reqheight()), min(420, self.panel_h - 100))
        x = self.outline_btn.winfo_rootx() + self.outline_btn.winfo_width() - width
        y = self.toolbar.winfo_rooty() + self.toolbar.winfo_height() + 4
        x = max(self.work_left + 8, min(x, self.work_right - width - 8))
        y = max(self.work_top + 8, min(y, self.work_bottom - height - 8))
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.bind("<Escape>", lambda _e: self._close_outline_popup() or "break")
        popup.focus_force()

    def _close_outline_popup(self) -> None:
        popup = getattr(self, "_outline_popup", None)
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
            self._outline_popup = None

    def _jump_to_outline(self, line_no: int, title: str) -> None:
        self._close_outline_popup()
        g = globals()
        if self.view_mode == "edit":
            widget = self.text
            index = f"{line_no}.0"
            widget.focus_set()
        else:
            widget = self.read_text
            index = self._find_rendered_heading_index(line_no, title)
            if not index:
                return
        try:
            widget.tag_remove("outline_current", "1.0", tk.END)
            widget.tag_configure("outline_current", background=g["OUTLINE_CURRENT"], foreground=g["TEXT"])
            end = f"{index} lineend"
            widget.tag_add("outline_current", index, end)
            widget.mark_set(tk.INSERT, index)
            widget.see(index)
            self.root.after(1600, lambda w=widget: w.tag_remove("outline_current", "1.0", tk.END))
        except tk.TclError:
            pass

    def _find_rendered_heading_index(self, target_line: int, title: str) -> str | None:
        same_title_before = 0
        for item in self._parse_outline():
            if int(item["line"]) >= target_line:
                break
            if str(item["title"]) == title:
                same_title_before += 1
        start = "1.0"
        count_var = tk.IntVar()
        found = None
        for _ in range(same_title_before + 1):
            found = self.read_text.search(title, start, stopindex=tk.END, nocase=False, count=count_var)
            if not found:
                return None
            start = f"{found}+{max(1, count_var.get())}c"
        return found

    # ── Read / edit view switching ────────────────────────────────────────────

    def _fit_read_view(self) -> None:
        if not hasattr(self, "read_text"):
            return
        width = self.read_text.winfo_width()
        pad = 4 if width < 320 else 8 if width < 420 else 10
        try:
            self.read_text.configure(padx=pad, wrap="char")
        except tk.TclError:
            pass

    def _render_read_content(self) -> None:
        if not hasattr(self, "read_text"):
            return
        if self.preview_path is not None:
            # Fix #10: pass user font settings so preview matches the rest of the UI
            render_file_preview(
                self.read_text,
                self.preview_path,
                font_family=self.config.font_family,
                font_size=self.config.font_size,
            )
        else:
            render_markdown(
                self.read_text,
                self._get_editor_content(),
                self.current_note_path,
                self.config.font_family,
                self.config.font_size,
                wiki_asset_resolver=self._wiki_asset_resolver,
                wiki_note_resolver=self._wiki_note_embed,
            )
            self._bind_rendered_wikilinks()
        # Keep widget selectable so users can copy text; edits are blocked by key binding
        self.read_text.configure(state=tk.NORMAL)
        for tag in ("find_match", "find_current", "outline_current", "sel"):
            try:
                self.read_text.tag_raise(tag)
            except tk.TclError:
                pass

    def _on_read_view_configure(self, _event=None) -> None:
        self._fit_read_view()
        if self.preview_path is None:
            return
        if self._preview_render_after is not None:
            try:
                self.root.after_cancel(self._preview_render_after)
            except tk.TclError:
                pass
        self._preview_render_after = self.root.after(80, self._rerender_file_preview)

    def _rerender_file_preview(self) -> None:
        self._preview_render_after = None
        if self.preview_path is not None and self.read_frame.winfo_ismapped():
            self._render_read_content()

    def _switch_to_edit(self) -> None:
        if self.preview_path is not None:
            self._close_file_preview(restore_note=True)
            if self.view_mode == "edit":
                self.text.focus_set()
                return
        if self.view_mode == "edit":
            return
        self.view_mode = "edit"
        self.config.view_mode = "edit"
        self.read_frame.pack_forget()
        self.edit_frame.pack(fill="both", expand=True)
        self._apply_live_render()
        self._update_view_buttons()
        save_config(self.config)
        self.text.focus_set()

    def _switch_to_read(self) -> None:
        self._hide_quick_format()
        if self.preview_path is not None:
            self._close_file_preview(restore_note=True)
        if self.view_mode == "read":
            return
        self._editor_image_editing_keys.clear()
        self._clear_editor_image_previews()
        self._save_note(False)
        self.view_mode = "read"
        self.config.view_mode = "read"
        self.edit_frame.pack_forget()
        self.read_frame.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self._fit_read_view()
        self._render_read_content()
        if hasattr(self, "find_panel") and self.find_panel.winfo_ismapped():
            self._refresh_find_matches(True)
        self._update_view_buttons()
        save_config(self.config)

    def _toggle_view_mode(self) -> None:
        if not self._is_markdown_document() and self.preview_path is None:
            self._set_status_key("status.text_editing")
            return
        if self.preview_path is not None:
            self._close_file_preview(restore_note=True)
            self.text.focus_set() if self.view_mode == "edit" else self.read_text.focus_set()
            return
        if self.view_mode == "edit":
            self._switch_to_read()
        else:
            self._switch_to_edit()

    def _update_view_buttons(self) -> None:
        g = globals()
        if self.current_note_path is not None and not self._is_markdown_document() and self.preview_path is None:
            self.view_toggle_btn.config(
                text="îœ¶",
                font=("Segoe MDL2 Assets", 11),
                bg=g["SURFACE_2"],
                fg=g["DISABLED"],
            )
            self.view_toggle_btn._normal_bg = g["SURFACE_2"]
            self.view_toggle_btn._normal_fg = g["DISABLED"]
            self.view_toggle_btn._tooltip_text = t("tooltip.read_mode_md_only")
            for btn in self._md_tool_buttons:
                btn.config(fg=g["DISABLED"])
                btn._normal_fg = g["DISABLED"]
            self._relayout_toolbar(force=True)
            self._update_command_tooltips()
            return
        if self.preview_path is not None:
            self.view_toggle_btn.config(
                text="",
                font=("Segoe MDL2 Assets", 11),
                bg=g["ACCENT"],
                fg=self._contrast_text(g["ACCENT"]),
            )
            self.view_toggle_btn._normal_bg = g["ACCENT"]
            self.view_toggle_btn._normal_fg = self._contrast_text(g["ACCENT"])
            self.view_toggle_btn._tooltip_text = t("tooltip.back_to_note")
            for btn in self._md_tool_buttons:
                btn.config(fg=g["DISABLED"])
                btn._normal_fg = g["DISABLED"]
            self._relayout_toolbar(force=True)
            self._update_command_tooltips()
            return
        if self.view_mode == "edit":
            self.view_toggle_btn.config(
                text="",
                font=("Segoe MDL2 Assets", 11),
                bg=g["SURFACE_2"],
                fg=g["TEXT_SOFT"],
            )
            self.view_toggle_btn._normal_bg = g["SURFACE_2"]
            self.view_toggle_btn._normal_fg = g["TEXT_SOFT"]
            self.view_toggle_btn._tooltip_text = t("tooltip.read_mode")
            for btn in self._md_tool_buttons:
                btn.config(fg=g["MUTED"])
                btn._normal_fg = g["MUTED"]
            self._relayout_toolbar(force=True)
        else:
            self.view_toggle_btn.config(
                text="",
                font=("Segoe MDL2 Assets", 11),
                bg=g["ACCENT"],
                fg=self._contrast_text(g["ACCENT"]),
            )
            self.view_toggle_btn._normal_bg = g["ACCENT"]
            self.view_toggle_btn._normal_fg = self._contrast_text(g["ACCENT"])
            self.view_toggle_btn._tooltip_text = t("tooltip.edit_mode")
            for btn in self._md_tool_buttons:
                btn.config(fg=g["DISABLED"])
                btn._normal_fg = g["DISABLED"]
            self._relayout_toolbar(force=True)
        self._update_command_tooltips()

    # ── Read mode copy ───────────────────────────────────────────────────────

    def _read_text_key_filter(self, event) -> str | None:
        """Allow navigation and Ctrl combos (copy, select-all) but block edits."""
        if event.state & 0x4:  # Ctrl held — allow Ctrl+C, Ctrl+A, etc.
            return None
        if event.keysym in (
            "Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next",
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "Escape", "Tab",
        ):
            return None
        return "break"

    def _setup_read_copy_btn(self) -> None:
        g = globals()
        # Borderless: just the word "copy" that darkens/brightens on hover.
        # bg matches the code block so the label blends into it seamlessly.
        btn = tk.Label(
            self.read_frame,
            text=t("editor.copy"),
            bg=g["CODE_BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            cursor="hand2",
            padx=5,
            pady=0,
        )
        btn.place_forget()
        self._read_copy_btn = btn
        self._read_copy_btn_label = btn

        def reset_label() -> None:
            if btn.winfo_exists():
                btn.config(text=t("editor.copy"), fg=globals()["MUTED"])

        def on_copy(_event=None) -> None:
            block = getattr(self, "_read_copy_btn_block", None)
            if not block:
                return
            text = block.get("text", "")
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
            btn.config(text=t("editor.copied"), fg=globals()["ACCENT_2"])
            self.root.after(900, reset_label)

        def on_btn_enter(_event=None) -> None:
            if btn.cget("text") == t("editor.copy"):
                btn.config(fg=globals()["TEXT"])
            self._cancel_copy_btn_hide()

        def on_btn_leave(_event=None) -> None:
            if btn.cget("text") == t("editor.copy"):
                btn.config(fg=globals()["MUTED"])
            self._schedule_copy_btn_hide()

        btn.bind("<Button-1>", on_copy)
        btn.bind("<Enter>", on_btn_enter)
        btn.bind("<Leave>", on_btn_leave)

    def _cancel_copy_btn_hide(self) -> None:
        if self._read_copy_btn_hide_after is not None:
            try:
                self.root.after_cancel(self._read_copy_btn_hide_after)
            except tk.TclError:
                pass
            self._read_copy_btn_hide_after = None

    def _schedule_copy_btn_hide(self, delay: int = 400) -> None:
        self._cancel_copy_btn_hide()
        self._read_copy_btn_hide_after = self.root.after(delay, self._hide_code_copy_btn)

    def _hide_code_copy_btn(self) -> None:
        self._read_copy_btn_hide_after = None
        if hasattr(self, "_read_copy_btn") and self._read_copy_btn.winfo_exists():
            self._read_copy_btn.place_forget()
        self._read_copy_btn_block = None

    def _on_read_hover(self, event) -> None:
        if getattr(self, "animating", False):
            return  # panel slide generates synthetic Motion events — skip work
        if not hasattr(self, "read_text") or not hasattr(self.read_text, "_code_blocks"):
            return
        if not self.read_text._code_blocks:
            return
        try:
            idx = self.read_text.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        line = int(idx.split(".")[0])
        for block in self.read_text._code_blocks:
            start_line = int(str(block["start"]).split(".")[0])
            end_line = int(str(block["end"]).split(".")[0])
            if start_line <= line <= end_line:
                self._cancel_copy_btn_hide()
                if self._read_copy_btn_block is block and self._read_copy_btn.winfo_ismapped():
                    return  # already shown for this block — avoid re-placing per pixel
                self._show_code_copy_btn(block)
                return
        self._schedule_copy_btn_hide(300)

    def _show_code_copy_btn(self, block: dict) -> None:
        if not hasattr(self, "_read_copy_btn"):
            return
        self._read_copy_btn_block = block
        try:
            bbox = self.read_text.dlineinfo(block["start"])
        except tk.TclError:
            return
        if bbox is not None:
            line_y = bbox[1]
        else:
            # Block start is scrolled above the viewport (long code block):
            # pin the button to the top edge of the visible area instead.
            try:
                if self.read_text.compare(block["start"], "<", self.read_text.index("@0,0")):
                    line_y = 0
                else:
                    return
            except tk.TclError:
                return
        btn = self._read_copy_btn
        btn.configure(bg=globals()["CODE_BG"])
        btn_w = max(btn.winfo_reqwidth(), 36)
        # Top-right of the code block, slightly inset; no update_idletasks here —
        # forcing layout per Motion event stutters the panel slide animation
        rx = self.read_text.winfo_x()
        ry = self.read_text.winfo_y()
        x = rx + self.read_text.winfo_width() - btn_w - 10
        y = ry + line_y + 2
        btn.place(x=x, y=y, in_=self.read_frame)
        btn.lift()
