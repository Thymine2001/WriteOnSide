from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import tkinter as tk
from PIL import Image, ImageGrab

from ..config import APP_NAME, save_config
from ..dragdrop import is_image_path, is_image_url, is_url, local_path_from_drop, split_drop_data
from ..frontmatter import note_template, parse_front_matter
from ..hotkeys import format_hotkey_display
from ..i18n import t
from ..markdown import render_markdown
from ..preview import render_file_preview
from ..notes.service import rename_target, unique_note_path
from ..storage import read_text_file, safe_write_text
from ..text_files import is_editable_text_path, is_markdown_note, read_editable_text
from ..theme import *  # noqa: F401,F403
from ..wikilinks import find_notes_linking_to, rewrite_wikilinks_after_rename


class NotesMixin:
    # ── Note CRUD ────────────────────────────────────────────────────────────

    def _new_note_path(self, suggested: str = "Untitled.md") -> Path:
        return unique_note_path(self._workspace_dir(), suggested)

    def _create_new_note(self) -> None:
        self._save_note(False)
        name = simpledialog.askstring(t("dialog.new_note_title"), t("dialog.new_note_prompt"), parent=self.root, initialvalue="Untitled.md")
        if name is None:
            return
        path = self._new_note_path(name)
        try:
            safe_write_text(path, note_template(path))
        except OSError as exc:
            self._set_error(t("error.create_failed", exc=exc))
            return
        self._open_note_file(path)
        self._refresh_explorer()
        self._schedule_wiki_index_refresh()

    def _rename_note(self, path: Path) -> None:
        if not path.exists():
            return
        new_name = simpledialog.askstring(t("dialog.rename_note_title"), t("dialog.rename_note_prompt"), parent=self.root, initialvalue=path.name)
        if not new_name:
            return
        target = rename_target(path, new_name, markdown=is_markdown_note(path))
        if target.exists() and target != path:
            messagebox.showerror(APP_NAME, t("dialog.note_exists"))
            return
        old_path = path.resolve()
        link_sources: set[Path] = set()
        old_title = path.stem
        old_aliases: tuple[str, ...] = ()
        pre_index = None
        if is_markdown_note(path):
            try:
                old_content = read_text_file(path)
                old_metadata = parse_front_matter(old_content, path.stem)
                old_title = old_metadata.title or path.stem
                old_aliases = old_metadata.aliases
            except OSError:
                pass
            self._refresh_wiki_index()
            pre_index = self._wiki_index
            link_sources = find_notes_linking_to(pre_index, old_path)
        try:
            path.rename(target)
        except OSError as exc:
            self._set_error(t("error.rename_failed", exc=exc))
            return
        new_path = target.resolve()
        changed_notes: list[Path] = []
        if is_markdown_note(new_path) and link_sources and pre_index is not None:
            changed_notes = rewrite_wikilinks_after_rename(
                self._workspace_dir(),
                old_path,
                new_path,
                old_title=old_title,
                old_aliases=old_aliases,
                index=pre_index,
                candidate_paths=link_sources,
            )
        if self.current_note_path and self.current_note_path.resolve() == old_path:
            self.current_note_path = new_path
            self.config.current_note_path = str(new_path) if is_markdown_note(new_path) else ""
            self._update_note_title()
        elif self.current_note_path and self.current_note_path.resolve() in {note.resolve() for note in changed_notes}:
            self._open_note_file(self.current_note_path)
        self._refresh_explorer()
        self._schedule_wiki_index_refresh()
        if changed_notes:
            self._set_status_key("status.renamed_links", count=len(changed_notes))

    def _delete_note(self, path: Path) -> None:
        if not messagebox.askyesno(APP_NAME, t("dialog.delete_note", name=path.name)):
            return
        try:
            path.unlink()
        except OSError as exc:
            self._set_error(t("error.delete_failed", exc=exc))
            return
        if self.current_note_path and self.current_note_path.resolve() == path.resolve():
            self.current_note_path = None
            self._load_initial_note()
        self._refresh_explorer()
        self._schedule_wiki_index_refresh()

    # ── Open / load notes ────────────────────────────────────────────────────

    def _open_note_from_tree(self, path: Path) -> None:
        was_previewing = self.preview_path is not None
        self._close_file_preview(restore_note=True)
        if self.current_note_path and path.resolve() == self.current_note_path.resolve():
            if was_previewing:
                self._set_status_key("status.ready")
            return
        self._save_note(False)
        self._open_note_file(path)

    def _open_text_file_from_tree(self, path: Path) -> None:
        self._close_file_preview(restore_note=False)
        if self.current_note_path and path.resolve() == self.current_note_path.resolve():
            return
        self._save_note(False)
        try:
            content, encoding, newline = read_editable_text(path)
        except (OSError, UnicodeError) as exc:
            self._set_error(t("error.open_failed", exc=exc))
            return
        self.current_note_path = path.resolve()
        self._document_encoding = encoding
        self._document_newline = newline
        self.config.current_note_path = ""
        self._reset_editor_structure()
        if self.view_mode != "edit":
            self.view_mode = "edit"
            self.config.view_mode = "edit"
            self.read_frame.pack_forget()
            self.edit_frame.pack(fill="both", expand=True)
        self._set_editor_content(content)
        self._dirty = False
        self._update_note_title()
        self._highlight_current_note()
        self._set_status_key("status.text_file")
        self._update_view_buttons()
        save_config(self.config)
        self.text.focus_set()

    def _open_external_file(self, path: Path) -> None:
        try:
            os.startfile(path)
        except OSError as exc:
            self._set_error(t("error.open_failed", exc=exc))

    def _preview_explorer_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file() or is_editable_text_path(path):
            return
        if self.preview_path is None:
            self._preview_previous_mode = self.view_mode
        self._save_note(False)
        self.preview_path = path.resolve()
        self.edit_frame.pack_forget()
        self.read_frame.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self._fit_read_view()
        self._render_read_content()
        self.note_title.config(text=path.name)
        self._set_status_key("status.preview")
        self._update_view_buttons()
        self.read_text.focus_set()

    def _close_file_preview(self, restore_note: bool = True) -> None:
        if self.preview_path is None:
            return
        previous_mode = self._preview_previous_mode or self.view_mode
        self.preview_path = None
        self._preview_previous_mode = None
        self.view_mode = previous_mode
        if self._preview_render_after is not None:
            try:
                self.root.after_cancel(self._preview_render_after)
            except tk.TclError:
                pass
            self._preview_render_after = None
        if not restore_note:
            return
        self.edit_frame.pack_forget()
        self.read_frame.pack_forget()
        if self.view_mode == "read":
            self.read_frame.pack(fill="both", expand=True)
            self._render_read_content()
        else:
            self.edit_frame.pack(fill="both", expand=True)
        self._update_note_title()
        self._update_view_buttons()

    def _open_note_file(self, path: Path) -> None:
        self._close_file_preview(restore_note=False)
        try:
            content = read_text_file(path) if path.exists() else ""
        except OSError as exc:
            self._set_error(t("error.open_failed", exc=exc))
            return
        self.current_note_path = path.resolve()
        self._document_encoding = "utf-8"
        self._document_newline = "\n"
        self.config.current_note_path = str(self.current_note_path)
        self._reset_editor_structure()
        self._set_editor_content(content)
        self._dirty = False
        self._update_note_title()
        self._highlight_current_note()
        self._set_status_key("status.opened")
        self._update_view_buttons()
        save_config(self.config)
        if self.view_mode == "read":
            render_markdown(
                self.read_text,
                content,
                self.current_note_path,
                self.config.font_family,
                self.config.font_size,
                wiki_asset_resolver=self._wiki_asset_resolver,
            )
            self._bind_rendered_wikilinks()

    def _load_initial_note(self) -> None:
        root = self._workspace_dir()
        last = Path(self.config.current_note_path).expanduser() if self.config.current_note_path else None
        if (
            self.config.remember_last_note
            and last
            and last.exists()
            and last.suffix.lower() == ".md"
            and self._is_in_workspace(last)
        ):
            self._open_note_file(last)
        else:
            notes = sorted(root.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if notes:
                self._open_note_file(notes[0])
            else:
                welcome = root / "Welcome.md"
                if not welcome.exists():
                    safe_write_text(
                        welcome,
                        note_template(welcome, "# Welcome to WriteOnSide\n\nStart writing here.\n"),
                    )
                self._open_note_file(welcome)
        self._refresh_explorer()

    def _switch_workspace(self, new_notes_dir: str) -> None:
        old_root = self._workspace_dir().resolve()
        self._save_note(False)
        self.config.notes_directory = new_notes_dir
        new_root = self._workspace_dir().resolve()
        if new_root == old_root:
            self._refresh_explorer()
            return
        self.current_note_path = None
        self.config.current_note_path = ""
        self._refresh_wiki_index()
        self._set_status_key("status.workspace_changed")
        self._load_initial_note()
        if self.explorer_visible:
            self._position_explorer()
            self._position_nav_bar()

    def _highlight_current_note(self) -> None:
        if not self.current_note_path or not hasattr(self, "file_tree"):
            return
        iid = str(self.current_note_path)
        self._ignore_tree_events = True
        try:
            if self.file_tree.exists(iid):
                self.file_tree.selection_set(iid)
                self.file_tree.see(iid)
        finally:
            self._ignore_tree_events = False

    # ── Status bar ───────────────────────────────────────────────────────────

    def _update_note_title(self) -> None:
        active_path = self.preview_path or self.current_note_path
        name = active_path.name if active_path else t("note.no_note")
        self.note_title.config(text=name)
        self._update_hotkey_hints()

    def _set_status(self, text: str) -> None:
        hotkey = format_hotkey_display(self.config.hotkey)
        active_path = self.preview_path or self.current_note_path
        note = active_path.name if active_path else t("note.no_note")
        self.status_label.config(text=t("status.bar", note=note, message=text, hotkey=hotkey))

    def _set_error(self, text: str) -> None:
        self.status_label.config(text=text, fg=globals()["DANGER"])
        self.root.after(3000, lambda: self.status_label.config(fg=globals()["MUTED"]))

    # ── Attachments ──────────────────────────────────────────────────────────

    def _figure_folder(self) -> Path | None:
        if not self.current_note_path or not is_markdown_note(self.current_note_path):
            return None
        root = self._workspace_dir().resolve()
        try:
            note_key = self.current_note_path.resolve().relative_to(root).with_suffix("")
        except ValueError:
            note_key = Path(self.current_note_path.stem)
        return root / self.config.attachments_folder / note_key

    def _unique_attachment_path(self, folder: Path, name: str) -> Path:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name).strip().strip(".") or "attachment"
        target = folder / cleaned
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        for n in range(1, 10000):
            candidate = folder / f"{stem} {n}{suffix}"
            if not candidate.exists():
                return candidate
        raise OSError("Unable to create unique attachment name.")

    def _markdown_relative_path(self, path: Path) -> str:
        if not self.current_note_path:
            return path.name
        try:
            rel = path.relative_to(self.current_note_path.parent)
        except ValueError:
            rel = path
        return rel.as_posix().replace(" ", "%20")

    def _copy_attachment(self, source: Path) -> Path | None:
        folder = self._figure_folder()
        if not folder:
            self._set_error(t("error.attachments_need_note"))
            return None
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = self._unique_attachment_path(folder, source.name)
            shutil.copy2(source, target)
            return target
        except OSError as exc:
            self._set_error(t("error.attachment_failed", exc=exc))
            return None

    def _insert_attachment_markdown(self, target: Path, image: bool) -> None:
        rel = self._markdown_relative_path(target)
        label = target.stem.replace("_", " ")
        snippet = f"![{label}]({rel})" if image else f"[{target.name}]({rel})"
        self._insert_text(snippet)
        self._insert_text("\n")

    # ── Editor drop ──────────────────────────────────────────────────────────

    def _editor_drop_index(self) -> str:
        x = self.text.winfo_pointerx() - self.text.winfo_rootx()
        y = self.text.winfo_pointery() - self.text.winfo_rooty()
        return self.text.index(f"@{max(0, x)},{max(0, y)}")

    def _insert_dropped_text(self, value: str) -> None:
        value = value.strip()
        if not value:
            return
        if is_image_url(value):
            self._insert_text(f"![]({value})")
        elif is_url(value):
            self._insert_text(f"[{value}]({value})")
        else:
            self._insert_text(value)

    def _on_editor_drop(self, event):
        if self.view_mode != "edit":
            return getattr(event, "action", None)
        self._clear_placeholder()
        self.text.mark_set(tk.INSERT, self._editor_drop_index())
        values = split_drop_data(self.text, event.data)
        if not any(
            (path := local_path_from_drop(value)) is not None and path.exists()
            for value in values
        ):
            values = [str(event.data).strip()]
        inserted = 0
        for value in values:
            source = local_path_from_drop(value)
            if source and source.is_file():
                target = self._copy_attachment(source)
                if target:
                    self._insert_attachment_markdown(target, image=is_image_path(target))
                    inserted += 1
                continue
            if source and source.is_dir():
                continue
            self._insert_dropped_text(value)
            inserted += 1
        if inserted:
            self.text.focus_set()
            self._set_status_key("status.inserted_items", count=inserted)
        else:
            self._set_error(t("error.nothing_supported_drop"))
        return getattr(event, "action", None)

    def _insert_image_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title=t("dialog.insert_image"),
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp;*.tif;*.tiff;*.ico"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        target = self._copy_attachment(Path(path))
        if target:
            self._insert_attachment_markdown(target, image=True)

    def _insert_attachment_file(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title=t("dialog.insert_attachment"))
        if not path:
            return
        source = Path(path)
        target = self._copy_attachment(source)
        if target:
            self._insert_attachment_markdown(target, image=is_image_path(target))

    def _insert_clipboard_image(self) -> None:
        self._save_clipboard_image(show_errors=True)

    def _paste_from_clipboard(self, _event=None):
        if self._save_clipboard_image(show_errors=False):
            return "break"
        return None

    def _save_clipboard_image(self, show_errors: bool) -> bool:
        folder = self._figure_folder()
        if not folder:
            if show_errors:
                self._set_error(t("error.images_need_note"))
            return False
        try:
            image = ImageGrab.grabclipboard()
        except Exception as exc:
            if show_errors:
                self._set_error(t("error.clipboard_unavailable", exc=exc))
            return False
        if not isinstance(image, Image.Image):
            if show_errors:
                self._set_error(t("error.clipboard_no_image"))
            return False
        try:
            folder.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("clipboard-%Y%m%d-%H%M%S.png")
            target = self._unique_attachment_path(folder, stamp)
            image.save(target, "PNG")
        except OSError as exc:
            if show_errors:
                self._set_error(t("error.image_save_failed", exc=exc))
            return False
        self._insert_attachment_markdown(target, image=True)
        return True
