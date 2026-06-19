from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from urllib.parse import quote

import tkinter as tk
from PIL import Image, ImageGrab
from tkinterdnd2 import DND_FILES, DND_TEXT

from ..config import APP_NAME, save_config
from ..dragdrop import is_image_path, is_image_url, is_url, local_path_from_drop, split_drop_data
from ..editor_images import EDITOR_IMAGE_ELIDE_TAG, load_preview_photo, plan_editor_image_blocks
from ..frontmatter import note_template, parse_front_matter
from ..diagnostics import get_logger
from ..i18n import t
from ..live_highlight import MD_EDITOR_TAGS, apply_live_highlight_plan, plan_live_highlight
from ..live_highlight import plan_live_highlight_fragment
from ..document_performance import DocumentMetrics, SOURCE_HIGHLIGHT_FULL_CHAR_LIMIT, VISIBLE_HIGHLIGHT_MARGIN
from ..preview import render_file_preview
from ..notes.service import rename_target, unique_note_path
from ..storage import read_text_file, safe_write_text
from ..syntax_highlight import source_token_spans, syntax_tag_name
from ..text_files import is_editable_text_path, is_markdown_note, read_editable_text
from ..theme import *  # noqa: F401,F403
from ..wikilinks import find_notes_linking_to, rewrite_wikilinks_after_rename


class NotesMixin:
    _MAX_OPEN_NOTES = 4

    # ── Note CRUD ────────────────────────────────────────────────────────────

    def _new_note_path(self, suggested: str = "Untitled.md") -> Path:
        return unique_note_path(self._workspace_dir(), suggested)

    def _ask_new_item_name(self, title: str, prompt: str, initial_value: str = "") -> str | None:
        g = globals()
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=g["BG"])
        win.transient(self.root)
        win.attributes("-topmost", True)
        win.resizable(False, False)

        width = 390
        height = 188
        try:
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - width) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - height) // 2)
        except tk.TclError:
            x = self.work_left + max(0, (self.work_right - self.work_left - width) // 2)
            y = self.work_top + max(0, (self.work_bottom - self.work_top - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

        shell = tk.Frame(win, bg=g["BG"], padx=18, pady=16)
        shell.pack(fill="both", expand=True)
        tk.Label(
            shell,
            text=title,
            bg=g["BG"],
            fg=g["TEXT"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            shell,
            text=prompt,
            bg=g["BG"],
            fg=g["TEXT_SOFT"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(4, 10))

        entry_wrap = tk.Frame(shell, bg=g["ACCENT"], padx=1, pady=1)
        entry_wrap.pack(fill="x")
        entry = tk.Entry(
            entry_wrap,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            insertbackground=g["TEXT"],
            relief="flat",
            font=("Segoe UI", 11),
        )
        entry.insert(0, initial_value)
        entry.pack(fill="x", ipady=7, padx=0, pady=0)
        entry.selection_range(0, tk.END)

        actions = tk.Frame(shell, bg=g["BG"])
        actions.pack(fill="x", pady=(16, 0))
        result = {"value": None}

        def close(value: str | None) -> None:
            result["value"] = value
            win.grab_release()
            win.destroy()

        def submit(_event=None) -> str:
            value = entry.get().strip()
            if value:
                close(value)
            else:
                entry.focus_set()
            return "break"

        cancel_btn = tk.Label(
            actions,
            text=t("dialog.cancel"),
            bg=g["SURFACE"],
            fg=g["TEXT_SOFT"],
            font=("Segoe UI", 10),
            padx=14,
            pady=7,
            cursor="hand2",
        )
        create_btn = tk.Label(
            actions,
            text=t("dialog.create"),
            bg=g["ACCENT"],
            fg=self._contrast_text(g["ACCENT"]),
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=7,
            cursor="hand2",
        )
        create_btn.pack(side="right")
        cancel_btn.pack(side="right", padx=(0, 8))
        cancel_btn.bind("<Button-1>", lambda _event: close(None))
        create_btn.bind("<Button-1>", submit)
        entry.bind("<Return>", submit)
        win.bind("<Escape>", lambda _event: close(None) or "break")
        win.protocol("WM_DELETE_WINDOW", lambda: close(None))

        entry.focus_set()
        win.grab_set()
        self.root.wait_window(win)
        return result["value"]

    def _ask_new_note_name(self) -> str | None:
        return self._ask_new_item_name(
            t("dialog.new_note_title"),
            t("dialog.new_note_prompt"),
            "Untitled.md",
        )

    def _create_new_note(self) -> None:
        self._save_note(False)
        name = self._ask_new_note_name()
        if name is None:
            return
        path = self._new_note_path(name)
        try:
            self._mark_vault_internal_write(path)
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
        self._note_split_paths_after_relocate({old_path: new_path})
        self._refresh_explorer()
        self._schedule_wiki_index_refresh()
        if changed_notes:
            self._set_status_key("status.renamed_links", count=len(changed_notes))

    def _delete_note(self, path: Path) -> None:
        if not messagebox.askyesno(APP_NAME, t("dialog.delete_note", name=path.name)):
            return
        attachment_error: OSError | None = None
        try:
            path.unlink()
        except OSError as exc:
            self._set_error(t("error.delete_failed", exc=exc))
            return
        try:
            self._delete_note_attachment_folder(path)
        except OSError as exc:
            attachment_error = exc
        if self.current_note_path and self.current_note_path.resolve() == path.resolve():
            self.current_note_path = None
            self._load_initial_note()
        self._close_deleted_split_notes(path)
        self._refresh_explorer()
        self._schedule_wiki_index_refresh()
        if attachment_error is not None:
            self._set_error(t("error.attachment_cleanup_failed", exc=attachment_error))

    # ── Open / load notes ────────────────────────────────────────────────────

    def _open_file_dialog(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title=t("dialog.open_file"),
            filetypes=[
                (t("dialog.text_and_code_files"), "*.*"),
                (t("dialog.all_files"), "*.*"),
            ],
        )
        if path:
            self._open_file_in_editor(Path(path), reveal_panel=True)

    def _open_file_in_editor(
        self,
        path: Path,
        reveal_panel: bool = True,
        prefer_split: bool = True,
    ) -> None:
        path = path.expanduser().resolve()
        if not path.exists() or not path.is_file():
            self._set_error(t("error.open_failed", exc=t("error.file_not_found")))
            return
        if getattr(self, "preview_path", None) is not None:
            self._close_file_preview(restore_note=True)
        if prefer_split and self.current_note_path is not None and path != self.current_note_path.resolve():
            if self._open_note_split(path):
                if reveal_panel:
                    if not self.is_open:
                        self.open_panel()
                    else:
                        self.root.deiconify()
                        self.root.lift()
                        self.root.focus_force()
                return
        if is_markdown_note(path):
            if not self.current_note_path or path != self.current_note_path.resolve():
                self._save_note(False)
                self._open_note_file(path)
        else:
            self._open_text_file_from_tree(path)
        if reveal_panel:
            if not self.is_open:
                self.open_panel()
            else:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()

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
        self._close_split_note_for_path(path)
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
            self.edit_frame.pack_forget()
            self.read_frame.pack_forget()
            if self.view_mode == "read":
                self.read_frame.pack(fill="both", expand=True)
            else:
                self.edit_frame.pack(fill="both", expand=True)
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
        self._close_split_note_for_path(path)
        self._close_file_preview(restore_note=False)
        try:
            content, encoding, newline = read_editable_text(path)
        except (OSError, UnicodeError) as exc:
            self._set_error(t("error.open_failed", exc=exc))
            return
        self.current_note_path = path.resolve()
        self._document_encoding = encoding
        self._document_newline = newline
        self.config.current_note_path = str(self.current_note_path) if self._is_in_workspace(path) else ""
        self._reset_editor_structure()
        self._set_editor_content(content)
        self._dirty = False
        self._update_note_title()
        self._highlight_current_note()
        self._set_status_key("status.opened")
        self._update_view_buttons()
        save_config(self.config)
        if self.view_mode == "read":
            self._render_read_content()

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
        self._save_all_split_notes()
        self.config.notes_directory = new_notes_dir
        new_root = self._workspace_dir().resolve()
        if new_root == old_root:
            self._refresh_explorer()
            return
        self.current_note_path = None
        self.config.current_note_path = ""
        self._close_all_split_notes()
        self._refresh_wiki_index()
        self._set_status_key("status.workspace_changed")
        self._load_initial_note()
        self._restart_vault_watcher()
        if self.explorer_visible:
            self._position_explorer()
            self._position_nav_bar()

    def _highlight_current_note(self) -> None:
        if not self.current_note_path or not hasattr(self, "file_tree"):
            return
        path = self.current_note_path.resolve()
        self._ignore_tree_events = True
        try:
            self._reveal_path_in_tree(path)
            iid = str(path)
            if self.file_tree.exists(iid):
                self.file_tree.selection_set(iid)
                self.file_tree.see(iid)
        finally:
            self._ignore_tree_events = False

    # ── Split note panes ─────────────────────────────────────────────────────

    def _open_note_count(self) -> int:
        return 1 + len(getattr(self, "_split_notes", []))

    def _is_split_note_path(self, path: Path) -> bool:
        target = path.resolve()
        return any(Path(note["path"]).resolve() == target for note in getattr(self, "_split_notes", []))

    def _register_note_drop_target(self, widget: tk.Misc) -> None:
        try:
            widget.drop_target_register(DND_FILES, DND_TEXT)
            widget.dnd_bind("<<Drop>>", self._on_editor_drop)
        except (AttributeError, tk.TclError):
            pass

    def _open_note_split(self, path: Path) -> bool:
        if not path.exists() or not path.is_file():
            return False
        if not is_editable_text_path(path):
            try:
                read_editable_text(path)
            except (OSError, UnicodeError):
                return False
        path = path.resolve()
        if self.current_note_path and path == self.current_note_path.resolve():
            self._set_status(f"{path.name} is already open as the main note")
            return True
        if self._is_split_note_path(path):
            self._focus_split_note(path)
            return True
        if self._open_note_count() >= self._MAX_OPEN_NOTES:
            self._set_error(t("error.open_file_limit", count=self._MAX_OPEN_NOTES))
            return True

        frame = tk.Frame(self.note_split, bg=globals()["BG"])
        header = tk.Frame(frame, bg=globals()["SURFACE_2"], height=28)
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Label(
            header,
            text=path.name,
            bg=globals()["SURFACE_2"],
            fg=globals()["TEXT"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        title.pack(side="left", fill="x", expand=True, padx=(8, 4))
        save_btn = tk.Label(
            header,
            text="💾",
            bg=globals()["SURFACE_2"],
            fg=globals()["MUTED"],
            font=("Segoe UI Emoji", 9),
            cursor="hand2",
            padx=6,
        )
        save_btn.pack(side="right", padx=(0, 2))
        open_btn = tk.Label(
            header,
            text="↕",
            bg=globals()["SURFACE_2"],
            fg=globals()["MUTED"],
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=6,
        )
        open_btn.pack(side="right", padx=(0, 2))
        close_btn = tk.Label(
            header,
            text="x",
            bg=globals()["SURFACE_2"],
            fg=globals()["MUTED"],
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=7,
        )
        close_btn.pack(side="right", padx=(0, 4))

        body = tk.Frame(frame, bg=globals()["BG"])
        body.pack(fill="both", expand=True)
        text = tk.Text(
            body,
            bg=globals()["BG"],
            fg=globals()["TEXT"],
            insertbackground=globals()["ACCENT"],
            selectbackground=globals()["ACCENT"],
            selectforeground=self._contrast_text(globals()["ACCENT"]),
            font=(self.config.font_family or "Segoe UI", self.config.font_size + 3),
            relief="flat",
            padx=8,
            pady=10,
            wrap="word",
            undo=True,
            exportselection=False,
            spacing1=2,
            spacing3=4,
            borderwidth=0,
            width=1,
            height=1,
        )
        text.pack(side="left", fill="both", expand=True)
        self._attach_dark_scrollbar(body, text)
        text.bind("<FocusIn>", lambda _event: self._activate_split_note(note))
        text.bind("<<Modified>>", lambda _event: self._on_split_text_modified(note))
        text.bind("<Control-s>", lambda _event: self._save_split_note(note, show_indicator=True) or "break")
        text.bind("<Control-S>", lambda _event: self._save_split_note(note, show_indicator=True) or "break")
        text.bind("<Control-Button-1>", self._on_edit_wikilink_click, add="+")
        text.bind("<Escape>", lambda _event: self._on_escape())
        text.bind("<Configure>", lambda _event: self._schedule_split_live_render(note), add="+")
        text.bind("<ButtonRelease-1>", lambda _event: self._on_split_image_click_outside(note), add="+")

        note = {
            "path": path,
            "frame": frame,
            "header": header,
            "title": title,
            "body": body,
            "text": text,
            "save_btn": save_btn,
            "open_btn": open_btn,
            "close_btn": close_btn,
            "encoding": "utf-8",
            "newline": "\n",
            "dirty": False,
            "loading": False,
            "autosave_after": None,
            "live_render_after": None,
            "color_tags": set(),
            "image_previews": {},
            "preview_photos": [],
            "image_blocks": {},
            "image_preview_state": None,
            "image_last_width": None,
            "image_editing_keys": set(),
            "image_preview_busy": False,
            "large_highlight_range": None,
        }
        text._scroll_refresh_callback = lambda n=note: self._schedule_split_live_render(n)
        self._split_notes.append(note)
        save_btn.bind("<Button-1>", lambda _event, n=note: self._save_split_note(n, show_indicator=True))
        close_btn.bind("<Button-1>", lambda _event, f=frame: self._close_split_note(f))
        open_btn.bind("<Button-1>", lambda _event, n=note: self._open_split_note_as_primary(n))
        tooltips = {
            save_btn: "tooltip.split_save",
            open_btn: "tooltip.split_main",
            close_btn: "tooltip.close",
        }
        for button in (save_btn, open_btn, close_btn):
            button.bind(
                "<Enter>",
                lambda _event, w=button, key=tooltips[button]: (
                    w.configure(bg=globals()["BORDER"], fg=globals()["TEXT"]),
                    self._show_tooltip(w, t(key)),
                ),
            )
            button.bind(
                "<Leave>",
                lambda _event, w=button: (
                    w.configure(bg=globals()["SURFACE_2"], fg=globals()["MUTED"]),
                    self._hide_tooltip(),
                ),
            )

        for target in (frame, header, body, text):
            self._register_note_drop_target(target)
        self._render_split_note(note)
        self.note_split.add(frame, minsize=120, stretch="always")
        self._set_status(f"Opened split note: {path.name}")
        return True

    def _render_split_note(self, note: dict[str, object]) -> None:
        path = Path(note["path"])
        text = note["text"]
        if not isinstance(text, tk.Text):
            return
        try:
            content, encoding, newline = read_editable_text(path)
        except (OSError, UnicodeError) as exc:
            content = f"Unable to open {path.name}: {exc}"
            encoding = "utf-8"
            newline = "\n"
        note["loading"] = True
        note["encoding"] = encoding
        note["newline"] = newline
        note["dirty"] = False
        text.delete("1.0", tk.END)
        text.insert("1.0", content)
        text.edit_reset()
        text.edit_modified(False)
        note["loading"] = False
        self._update_split_note_title(note)
        self._apply_split_live_render(note)

    def _refresh_split_note_panes(self) -> None:
        for note in getattr(self, "_split_notes", []):
            for key in ("frame", "body"):
                widget = note.get(key)
                if isinstance(widget, tk.Misc):
                    widget.configure(bg=globals()["BG"])
            header = note.get("header")
            title = note.get("title")
            text = note.get("text")
            if isinstance(header, tk.Misc):
                header.configure(bg=globals()["SURFACE_2"])
            if isinstance(title, tk.Misc):
                title.configure(bg=globals()["SURFACE_2"], fg=globals()["TEXT"])
            if isinstance(text, tk.Text):
                text.configure(
                    bg=globals()["BG"],
                    fg=globals()["TEXT"],
                    insertbackground=globals()["ACCENT"],
                    selectbackground=globals()["ACCENT"],
                    selectforeground=self._contrast_text(globals()["ACCENT"]),
                    font=(self.config.font_family or "Segoe UI", self.config.font_size + 3),
                )
            self._update_split_note_title(note, active=note is getattr(self, "_last_focused_split_note", None))
            self._apply_split_live_render(note)

    def _configure_split_markdown_tags(self, text: tk.Text) -> None:
        family = self.config.font_family or "Segoe UI"
        delta = self.config.font_size - 10
        g = globals()
        text.tag_configure("md_h1", font=(family, 18 + delta, "bold"), foreground=g["TEXT"], spacing3=6)
        text.tag_configure("md_h2", font=(family, 16 + delta, "bold"), foreground=g["TEXT"], spacing3=5)
        text.tag_configure("md_h3", font=(family, 14 + delta, "bold"), foreground=g["TEXT"], spacing3=4)
        text.tag_configure("md_h4", font=(family, 13 + delta, "bold"), foreground=g["TEXT"], spacing3=3)
        text.tag_configure("md_h5", font=(family, 12 + delta, "bold"), foreground=g["TEXT_SOFT"], spacing3=3)
        text.tag_configure("md_h6", font=(family, 11 + delta, "bold"), foreground=g["MUTED"], spacing3=2)
        text.tag_configure("md_bold", font=(family, 13 + delta, "bold"), foreground=g["TEXT"])
        text.tag_configure("md_italic", font=(family, 13 + delta, "italic"), foreground=g["TEXT_SOFT"])
        text.tag_configure("md_underline", underline=True, foreground=g["TEXT"])
        text.tag_configure("md_strike", overstrike=True, foreground=g["TEXT_SOFT"])
        text.tag_configure("md_highlight", background=g["HIGHLIGHT_BG"], foreground=g["HIGHLIGHT_FG"])
        text.tag_configure("md_sup", font=(family, 10 + delta), offset=4, foreground=g["TEXT"])
        text.tag_configure("md_sub", font=(family, 10 + delta), offset=-3, foreground=g["TEXT"])
        text.tag_configure("md_code", font=("Consolas", 12 + delta), background=g["CODE_BG"], foreground=g["CODE_TEXT"])
        text.tag_configure("md_link", foreground=g["LINK"], underline=True)
        text.tag_configure("md_image", foreground=g["IMAGE_LINK"], underline=True)
        text.tag_configure("md_quote", foreground=g["QUOTE"], lmargin1=18, lmargin2=18)
        text.tag_configure("md_list", lmargin1=22, lmargin2=22)
        text.tag_configure("md_task", lmargin1=22, lmargin2=22)
        text.tag_configure("md_task_done", lmargin1=22, lmargin2=22, foreground=g["MUTED"], overstrike=True)
        text.tag_configure("md_table", font=("Consolas", 11 + delta), foreground=g["TEXT_SOFT"])
        text.tag_configure("md_hr", foreground=g["MUTED"])
        text.tag_configure(
            "md_frontmatter",
            font=("Consolas", 10 + delta),
            foreground=g["MUTED"],
            background=g["SURFACE_2"],
            lmargin1=8,
            lmargin2=8,
        )
        text.tag_configure("md_obsidian_tag", foreground=g["ACCENT_2"])
        text.tag_configure("md_callout", background=g["SURFACE_2"], foreground=g["TEXT"])
        text.tag_configure("md_comment", foreground=g["DISABLED"], overstrike=True)
        try:
            text.tag_raise("sel")
        except tk.TclError:
            pass

    def _clear_split_markdown_tags(self, note: dict[str, object]) -> None:
        text = note.get("text")
        if not isinstance(text, tk.Text):
            return
        color_tags = note.setdefault("color_tags", set())
        for tag in ("source_code", *MD_EDITOR_TAGS, *color_tags):
            try:
                text.tag_remove(tag, "1.0", tk.END)
            except tk.TclError:
                pass
        if isinstance(color_tags, set):
            color_tags.clear()

    def _clear_split_markdown_only_tags(self, note: dict[str, object]) -> None:
        text = note.get("text")
        if not isinstance(text, tk.Text):
            return
        for tag in MD_EDITOR_TAGS:
            try:
                text.tag_remove(tag, "1.0", tk.END)
            except tk.TclError:
                pass

    def _clear_split_source_tags(self, note: dict[str, object], start: str, end: str) -> None:
        text = note.get("text")
        if not isinstance(text, tk.Text):
            return
        color_tags = note.setdefault("color_tags", set())
        for tag in ("source_code", *(color_tags if isinstance(color_tags, set) else set())):
            try:
                text.tag_remove(tag, start, end)
            except tk.TclError:
                pass

    def _split_document_metrics(self, text: tk.Text) -> DocumentMetrics:
        try:
            return DocumentMetrics(
                int(text.count("1.0", "end-1c", "chars")[0]),
                int(str(text.index("end-1c")).split(".")[0]),
            )
        except (tk.TclError, TypeError, ValueError):
            return DocumentMetrics(0, 1)

    def _visible_split_line_range(self, text: tk.Text, metrics: DocumentMetrics) -> tuple[int, int]:
        try:
            top = int(str(text.index("@0,0")).split(".")[0])
            bottom = int(str(text.index(f"@0,{max(1, text.winfo_height())}")).split(".")[0])
        except (tk.TclError, TypeError, ValueError):
            top, bottom = 1, min(metrics.lines, 200)
        return (
            max(1, top - VISIBLE_HIGHLIGHT_MARGIN),
            min(metrics.lines, bottom + VISIBLE_HIGHLIGHT_MARGIN),
        )

    def _apply_split_source_file_highlight(self, note: dict[str, object], text: tk.Text, path: Path) -> None:
        metrics = self._split_document_metrics(text)
        use_fragment = metrics.is_large or metrics.characters > SOURCE_HIGHLIGHT_FULL_CHAR_LIMIT
        if use_fragment:
            start_line, end_line = self._visible_split_line_range(text, metrics)
            content = text.get(f"{start_line}.0", f"{end_line}.end")
            previous_range = note.get("large_highlight_range")
            clear_range = (start_line, end_line)
            if isinstance(previous_range, tuple) and len(previous_range) == 2:
                clear_range = (
                    min(int(previous_range[0]), start_line),
                    max(int(previous_range[1]), end_line),
                )
            self._clear_split_source_tags(note, f"{clear_range[0]}.0", f"{clear_range[1]}.end")
            base_index = f"{start_line}.0"
            tag_start = f"{start_line}.0"
            tag_end = f"{end_line}.end"
            note["large_highlight_range"] = (start_line, end_line)
        else:
            previous_range = note.get("large_highlight_range")
            if isinstance(previous_range, tuple) and len(previous_range) == 2:
                self._clear_split_source_tags(note, f"{int(previous_range[0])}.0", f"{int(previous_range[1])}.end")
            note["large_highlight_range"] = None
            self._clear_split_source_tags(note, "1.0", tk.END)
            content = text.get("1.0", "end-1c")
            base_index = "1.0"
            tag_start = "1.0"
            tag_end = tk.END

        code_font = ("Consolas", max(9, self.config.font_size + 2))
        text.tag_configure("source_code", font=code_font, foreground=globals()["TEXT"])
        text.tag_add("source_code", tag_start, tag_end)
        color_tags = note.setdefault("color_tags", set())
        if not isinstance(color_tags, set):
            color_tags = set()
            note["color_tags"] = color_tags
        for span in source_token_spans(content, path, background=globals()["BG"]):
            tag = syntax_tag_name("source_syntax", span.color)
            text.tag_configure(tag, foreground=span.color, font=code_font)
            color_tags.add(tag)
            text.tag_add(tag, f"{base_index}+{span.start}c", f"{base_index}+{span.end}c")
        text.tag_raise("sel")

    def _schedule_split_live_render(self, note: dict[str, object]) -> None:
        previous = note.get("live_render_after")
        if previous is not None:
            try:
                self.root.after_cancel(previous)
            except tk.TclError:
                pass
        note["live_render_after"] = self.root.after(80, lambda n=note: self._apply_split_live_render(n))

    def _apply_split_live_render(self, note: dict[str, object]) -> None:
        note["live_render_after"] = None
        if note not in getattr(self, "_split_notes", []):
            return
        text = note.get("text")
        path = Path(note["path"])
        if not isinstance(text, tk.Text):
            return
        if not is_markdown_note(path):
            self._clear_split_markdown_only_tags(note)
            self._clear_split_image_previews(note)
            self._apply_split_source_file_highlight(note, text, path)
            return
        self._configure_split_markdown_tags(text)
        metrics = self._split_document_metrics(text)
        if metrics.is_large:
            start_line, end_line = self._visible_split_line_range(text, metrics)
            fragment = text.get(f"{start_line}.0", f"{end_line}.end")
            plan = plan_live_highlight_fragment(fragment, start_line=start_line, simplified=True)
            previous_range = note.get("large_highlight_range")
            clear_range = plan.line_range
            if isinstance(previous_range, tuple) and len(previous_range) == 2:
                clear_range = (
                    min(int(previous_range[0]), plan.line_range[0]),
                    max(int(previous_range[1]), plan.line_range[1]),
                )
            note["large_highlight_range"] = plan.line_range
            color_tags = note.setdefault("color_tags", set())
            if not isinstance(color_tags, set):
                color_tags = set()
                note["color_tags"] = color_tags
            apply_live_highlight_plan(
                text,
                plan,
                clear_tags=MD_EDITOR_TAGS,
                clear_line_range=clear_range,
                validate_color=lambda color, widget=text: self._validate_split_color(widget, color),
                configure_color_tag=lambda tag, color, widget=text: self._configure_split_color_tag(widget, tag, color),
                editor_color_tags=color_tags,
            )
            self._clear_split_image_previews(note)
            return

        note["large_highlight_range"] = None
        content = text.get("1.0", "end-1c")
        try:
            focus_line = int(str(text.index("insert")).split(".")[0])
        except (tk.TclError, ValueError):
            focus_line = None
        plan = plan_live_highlight(content, focus_line=focus_line)
        color_tags = note.setdefault("color_tags", set())
        if not isinstance(color_tags, set):
            color_tags = set()
            note["color_tags"] = color_tags
        apply_live_highlight_plan(
            text,
            plan,
            clear_tags=MD_EDITOR_TAGS,
            clear_line_range=plan.line_range if plan.partial else None,
            validate_color=lambda color, widget=text: self._validate_split_color(widget, color),
            configure_color_tag=lambda tag, color, widget=text: self._configure_split_color_tag(widget, tag, color),
            editor_color_tags=color_tags,
        )
        try:
            text.tag_raise("sel")
        except tk.TclError:
            pass
        self._apply_split_image_previews(note, content)

    def _validate_split_color(self, widget: tk.Text, color: str) -> bool:
        try:
            widget.winfo_rgb(color)
        except tk.TclError:
            return False
        return True

    def _configure_split_color_tag(self, widget: tk.Text, tag: str, color: str) -> None:
        family = self.config.font_family or "Segoe UI"
        widget.tag_configure(tag, foreground=color, font=(family, self.config.font_size + 3))

    def _remove_split_image_preview(self, note: dict[str, object], key: str) -> None:
        text = note.get("text")
        previews = note.get("image_previews")
        if not isinstance(text, tk.Text) or not isinstance(previews, dict):
            return
        preview = previews.pop(key, None)
        if not preview:
            return
        window_mark = preview.get("window_mark")
        window_widget = preview.get("window_widget")
        if window_mark:
            try:
                window_index = text.index(window_mark)
                if text.window_cget(window_index, "window"):
                    text.delete(window_index)
            except tk.TclError:
                pass
            try:
                text.mark_unset(window_mark)
            except tk.TclError:
                pass
        if window_widget is not None:
            try:
                if window_widget.winfo_exists():
                    window_widget.destroy()
            except tk.TclError:
                pass
        source_start_mark = preview.get("source_start_mark")
        source_end_mark = preview.get("source_end_mark")
        if source_start_mark and source_end_mark:
            try:
                text.tag_remove(EDITOR_IMAGE_ELIDE_TAG, source_start_mark, source_end_mark)
            except tk.TclError:
                pass
            for mark in (source_start_mark, source_end_mark):
                try:
                    text.mark_unset(mark)
                except tk.TclError:
                    pass

    def _clear_split_image_previews(self, note: dict[str, object]) -> None:
        previews = note.get("image_previews")
        if isinstance(previews, dict):
            for key in list(previews.keys()):
                self._remove_split_image_preview(note, key)
        note["preview_photos"] = []
        note["image_blocks"] = {}
        note["image_preview_state"] = None
        note["image_last_width"] = None
        text = note.get("text")
        if isinstance(text, tk.Text):
            try:
                text.tag_remove(EDITOR_IMAGE_ELIDE_TAG, "1.0", tk.END)
            except tk.TclError:
                pass

    def _apply_split_image_previews(self, note: dict[str, object], content: str | None = None) -> None:
        text = note.get("text")
        path = Path(note["path"])
        if not isinstance(text, tk.Text) or not is_markdown_note(path):
            self._clear_split_image_previews(note)
            return
        try:
            metrics = DocumentMetrics(
                int(text.count("1.0", "end-1c", "chars")[0]),
                int(str(text.index("end-1c")).split(".")[0]),
            )
        except (tk.TclError, TypeError, ValueError):
            metrics = DocumentMetrics(0, 1)
        if metrics.is_large:
            self._clear_split_image_previews(note)
            return
        if content is None:
            content = text.get("1.0", "end-1c")
        blocks = plan_editor_image_blocks(
            content,
            path,
            wiki_asset_resolver=self._wiki_asset_resolver,
        )
        note["image_blocks"] = {block.key: block for block in blocks}
        text.update_idletasks()
        try:
            max_width = max(160, text.winfo_width() - 48)
        except tk.TclError:
            max_width = 160
        editing_keys = note.setdefault("image_editing_keys", set())
        if not isinstance(editing_keys, set):
            editing_keys = set()
            note["image_editing_keys"] = editing_keys
        previews = note.setdefault("image_previews", {})
        if not isinstance(previews, dict):
            previews = {}
            note["image_previews"] = previews
        desired_keys = {block.key for block in blocks if block.key not in editing_keys}
        signature = tuple((block.key, block.markdown, str(block.image_path)) for block in blocks)
        preview_state = (signature, max_width, frozenset(editing_keys), frozenset(previews.keys()))
        if preview_state == note.get("image_preview_state"):
            return
        note["image_preview_busy"] = True
        try:
            for key in list(previews.keys()):
                if key not in desired_keys:
                    self._remove_split_image_preview(note, key)
            for block in blocks:
                if block.key not in desired_keys:
                    continue
                preview = previews.get(block.key)
                if (
                    preview
                    and preview.get("markdown") == block.markdown
                    and preview.get("max_width") == max_width
                    and preview.get("image_path") == str(block.image_path)
                ):
                    continue
                if preview:
                    self._remove_split_image_preview(note, block.key)
                self._insert_split_image_preview(note, block, max_width)
            note["image_last_width"] = max_width
            note["image_preview_state"] = (
                signature,
                max_width,
                frozenset(editing_keys),
                frozenset(previews.keys()),
            )
        finally:
            note["image_preview_busy"] = False

    def _insert_split_image_preview(self, note: dict[str, object], block, max_width: int) -> None:
        text = note.get("text")
        if not isinstance(text, tk.Text):
            return
        photo = load_preview_photo(block.image_path, max_width)
        if photo is None:
            return
        photos = note.setdefault("preview_photos", [])
        if isinstance(photos, list):
            photos.append(photo)
        g = globals()
        outer = tk.Frame(text, bg=g["BG"], highlightthickness=2, highlightbackground=g["BG"])
        image_label = tk.Label(outer, image=photo, bg=g["BG"], cursor="hand2", borderwidth=0)
        image_label.pack()
        toolbar = tk.Frame(outer, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"])
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
            outer.config(highlightbackground=globals()["ACCENT"])
            if not toolbar.winfo_ismapped():
                toolbar.place(relx=1.0, rely=0.0, anchor="ne", x=-4, y=4)

        def hide_toolbar(_event=None) -> None:
            outer.config(highlightbackground=globals()["BG"])
            if toolbar.winfo_ismapped():
                toolbar.place_forget()
            edit_btn.config(fg=globals()["MUTED"])

        def on_edit(_event=None) -> None:
            self._show_split_image_source(note, block)

        outer.bind("<Enter>", show_toolbar, add="+")
        outer.bind("<Leave>", hide_toolbar, add="+")
        edit_btn.bind("<Enter>", lambda _e: edit_btn.config(fg=globals()["TEXT"]), add="+")
        edit_btn.bind("<Leave>", lambda _e: edit_btn.config(fg=globals()["MUTED"]), add="+")
        edit_btn.bind("<Button-1>", on_edit)
        image_label.bind("<Button-1>", on_edit)

        safe_note = re.sub(r"\W+", "_", str(id(note)))
        safe_key = re.sub(r"\W+", "_", block.key)
        window_mark = f"_split_image_window_{safe_note}_{safe_key}"
        source_start_mark = f"_split_image_source_start_{safe_note}_{safe_key}"
        source_end_mark = f"_split_image_source_end_{safe_note}_{safe_key}"
        try:
            if text.compare(block.start, ">", tk.END):
                return
            text.mark_set(window_mark, block.start)
            text.mark_gravity(window_mark, tk.LEFT)
            text.window_create(window_mark, window=outer, stretch=True)
            md_start = text.index(f"{window_mark} + 1c")
            md_end = text.index(f"{md_start} + {len(block.markdown)}c")
            text.mark_set(source_start_mark, md_start)
            text.mark_set(source_end_mark, md_end)
            text.mark_gravity(source_start_mark, tk.LEFT)
            text.mark_gravity(source_end_mark, tk.RIGHT)
            text.tag_add(EDITOR_IMAGE_ELIDE_TAG, md_start, md_end)
            previews = note.setdefault("image_previews", {})
            if isinstance(previews, dict):
                previews[block.key] = {
                    "window_mark": window_mark,
                    "window_widget": outer,
                    "source_start_mark": source_start_mark,
                    "source_end_mark": source_end_mark,
                    "block": block,
                    "markdown": block.markdown,
                    "max_width": max_width,
                    "image_path": str(block.image_path),
                }
        except tk.TclError:
            for mark in (window_mark, source_start_mark, source_end_mark):
                try:
                    text.mark_unset(mark)
                except tk.TclError:
                    pass
            outer.destroy()

    def _show_split_image_source(self, note: dict[str, object], block) -> None:
        editing_keys = note.setdefault("image_editing_keys", set())
        if isinstance(editing_keys, set):
            editing_keys.add(block.key)
        self._remove_split_image_preview(note, block.key)
        text = note.get("text")
        if not isinstance(text, tk.Text):
            return
        try:
            md_start = block.start
            md_end = text.index(f"{md_start} + {len(block.markdown)}c")
            text.tag_add(tk.SEL, md_start, md_end)
            text.mark_set(tk.INSERT, md_end)
            text.focus_set()
        except tk.TclError:
            pass

    def _on_split_image_click_outside(self, note: dict[str, object]) -> None:
        editing_keys = note.get("image_editing_keys")
        image_blocks = note.get("image_blocks")
        text = note.get("text")
        if not isinstance(editing_keys, set) or not editing_keys:
            return
        if not isinstance(image_blocks, dict) or not isinstance(text, tk.Text):
            return
        try:
            index = text.index("insert")
            insert_line = int(str(index).split(".")[0])
        except (tk.TclError, ValueError):
            return
        changed = False
        for key in list(editing_keys):
            block = image_blocks.get(key)
            if block is None or insert_line != block.line:
                editing_keys.discard(key)
                changed = True
        if changed:
            note["image_preview_state"] = None
            self._apply_split_image_previews(note)

    def _activate_split_note(self, note: dict[str, object]) -> None:
        previous = getattr(self, "_last_focused_split_note", None)
        if previous is not None and previous is not note:
            self._update_split_note_title(previous, active=False)
        self._last_focused_split_note = note
        self._update_split_note_title(note, active=True)
        path = Path(note["path"])
        self._set_status(f"Editing split note: {path.name}")

    def _update_split_note_title(self, note: dict[str, object], active: bool = False) -> None:
        title = note.get("title")
        if not isinstance(title, tk.Misc):
            return
        path = Path(note["path"])
        marker = "*" if note.get("dirty") else ""
        prefix = "> " if active else ""
        title.configure(text=f"{prefix}{path.name}{marker}")

    def _on_split_text_modified(self, note: dict[str, object]) -> None:
        text = note.get("text")
        if not isinstance(text, tk.Text):
            return
        if not text.edit_modified():
            return
        text.edit_modified(False)
        if note.get("loading"):
            return
        note["dirty"] = True
        self._update_split_note_title(note, active=note is getattr(self, "_last_focused_split_note", None))
        self._set_status(f"Unsaved split note: {Path(note['path']).name}")
        self._schedule_split_live_render(note)
        self._schedule_split_note_autosave(note)

    def _schedule_split_note_autosave(self, note: dict[str, object]) -> None:
        if not self.config.auto_save:
            return
        previous = note.get("autosave_after")
        if previous is not None:
            try:
                self.root.after_cancel(previous)
            except tk.TclError:
                pass
        note["autosave_after"] = self.root.after(
            self.config.auto_save_delay_ms,
            lambda n=note: self._save_split_note(n, show_indicator=False),
        )

    def _save_split_note(self, note: dict[str, object], show_indicator: bool = False) -> None:
        text = note.get("text")
        path = Path(note["path"])
        if not isinstance(text, tk.Text) or not path.exists():
            return
        if not show_indicator and not note.get("dirty"):
            return
        content = text.get("1.0", "end-1c")
        in_workspace = self._is_in_workspace(path)
        backup_root = self._workspace_dir() if in_workspace else path.parent
        try:
            self._mark_vault_internal_write(path)
            safe_write_text(
                path,
                content,
                encoding=str(note.get("encoding") or "utf-8"),
                newline=str(note.get("newline") or "\n"),
                workspace_root=backup_root,
            )
        except OSError as exc:
            self._set_error(t("error.save_failed", exc=exc))
            return
        note["dirty"] = False
        previous = note.get("autosave_after")
        if previous is not None:
            try:
                self.root.after_cancel(previous)
            except tk.TclError:
                pass
            note["autosave_after"] = None
        self._update_split_note_title(note, active=note is getattr(self, "_last_focused_split_note", None))
        if show_indicator:
            self.save_indicator.config(text=t("status.saved"))
            self.root.after(1400, lambda: self.save_indicator.config(text=""))
        self._set_status_key("status.saved")
        if is_markdown_note(path) and in_workspace:
            self._schedule_tag_refresh()
            self._schedule_wiki_index_refresh()

    def _save_all_split_notes(self) -> None:
        for note in list(getattr(self, "_split_notes", [])):
            self._save_split_note(note, show_indicator=False)

    def _focused_split_note(self) -> dict[str, object] | None:
        focused = self.root.focus_get()
        for note in getattr(self, "_split_notes", []):
            if note.get("text") is focused:
                return note
        return None

    def _active_split_note(self) -> dict[str, object] | None:
        focused = self._focused_split_note()
        if focused is not None:
            return focused
        last = getattr(self, "_last_focused_split_note", None)
        if last in getattr(self, "_split_notes", []):
            return last
        return None

    def _note_for_text_widget(self, widget: tk.Text) -> dict[str, object] | None:
        for note in getattr(self, "_split_notes", []):
            if note.get("text") is widget:
                return note
        return None

    def _split_text_widgets(self) -> tuple[tk.Text, ...]:
        widgets: list[tk.Text] = []
        for note in getattr(self, "_split_notes", []):
            text = note.get("text")
            if isinstance(text, tk.Text):
                widgets.append(text)
        return tuple(widgets)

    def _apply_split_note_typography(self) -> None:
        family = self.config.font_family or "Segoe UI"
        font = (family, self.config.font_size + 3)
        for note in getattr(self, "_split_notes", []):
            text = note.get("text")
            if isinstance(text, tk.Text):
                try:
                    text.configure(font=font)
                except tk.TclError:
                    pass
            self._apply_split_live_render(note)

    def _focus_split_note(self, path: Path) -> None:
        for note in getattr(self, "_split_notes", []):
            if Path(note["path"]).resolve() != path.resolve():
                continue
            text = note.get("text")
            if isinstance(text, tk.Text):
                text.focus_set()
                self._set_status(f"{path.name} is already open in split view")
            return

    def _close_split_note(self, frame: tk.Misc) -> None:
        closing = next((note for note in self._split_notes if note.get("frame") is frame), None)
        if closing is not None:
            self._save_split_note(closing, show_indicator=False)
            for key in ("autosave_after", "live_render_after"):
                previous = closing.get(key)
                if previous is not None:
                    try:
                        self.root.after_cancel(previous)
                    except tk.TclError:
                        pass
                    closing[key] = None
        self._split_notes = [note for note in self._split_notes if note.get("frame") is not frame]
        if getattr(self, "_last_focused_split_note", None) is closing:
            self._last_focused_split_note = None
        try:
            self.note_split.forget(frame)
        except tk.TclError:
            pass
        try:
            frame.destroy()
        except tk.TclError:
            pass
        self._set_status_key("status.ready")

    def _close_split_note_for_path(self, path: Path) -> None:
        target = path.resolve()
        for note in list(getattr(self, "_split_notes", [])):
            if Path(note["path"]).resolve() == target:
                frame = note.get("frame")
                if isinstance(frame, tk.Misc):
                    self._close_split_note(frame)

    def _close_deleted_split_notes(self, path: Path) -> None:
        target = path.resolve()
        for note in list(getattr(self, "_split_notes", [])):
            note_path = Path(note["path"]).resolve()
            if note_path == target or self._path_is_descendant(target, note_path):
                frame = note.get("frame")
                if isinstance(frame, tk.Misc):
                    self._close_split_note(frame)

    def _close_all_split_notes(self) -> None:
        for note in list(getattr(self, "_split_notes", [])):
            frame = note.get("frame")
            if isinstance(frame, tk.Misc):
                self._close_split_note(frame)
        self._split_notes = []

    def _open_split_note_as_primary(self, note: dict[str, object]) -> str:
        split_path = Path(note["path"]).resolve()
        self._save_split_note(note, show_indicator=False)
        if self.preview_path is not None:
            self._close_file_preview(restore_note=True)
        if not self.current_note_path:
            frame = note.get("frame")
            if isinstance(frame, tk.Misc):
                self._close_split_note(frame)
            if is_markdown_note(split_path):
                self._open_note_from_tree(split_path)
            else:
                self._open_text_file_from_tree(split_path)
            return "break"

        main_path = self.current_note_path.resolve()
        if main_path == split_path:
            return "break"

        self._save_note(False)
        main_encoding = self._document_encoding
        main_newline = self._document_newline

        note["path"] = main_path
        note["encoding"] = main_encoding
        note["newline"] = main_newline
        note["dirty"] = False
        note["autosave_after"] = None

        if is_markdown_note(split_path):
            self._open_note_from_tree(split_path)
        else:
            self._open_text_file_from_tree(split_path)
        self._render_split_note(note)
        self._set_status(f"Swapped main note with {main_path.name}")
        return "break"

    def _note_split_paths_after_relocate(self, mapping: dict[Path, Path]) -> None:
        if not mapping:
            return
        resolved_mapping = {old.resolve(): new.resolve() for old, new in mapping.items()}
        for note in getattr(self, "_split_notes", []):
            old_path = Path(note["path"]).resolve()
            new_path = resolved_mapping.get(old_path)
            if not new_path:
                continue
            note["path"] = new_path
            title = note.get("title")
            if isinstance(title, tk.Misc):
                title.configure(text=new_path.name)
            self._render_split_note(note)

    # ── Status bar ───────────────────────────────────────────────────────────

    def _update_note_title(self) -> None:
        active_path = self.preview_path or self.current_note_path
        name = active_path.name if active_path else t("note.no_note")
        self.note_title.config(text=name)
        self._update_hotkey_hints()

    def _set_status(self, text: str) -> None:
        active_path = self.preview_path or self.current_note_path
        note = active_path.name if active_path else t("note.no_note")
        self.status_label.config(text=t("status.bar", note=note, message=text))

    def _set_error(self, text: str) -> None:
        get_logger().warning("UI error: %s", text)
        self.status_label.config(text=text, fg=globals()["DANGER"])
        self.root.after(3000, lambda: self.status_label.config(fg=globals()["MUTED"]))

    # ── Attachments ──────────────────────────────────────────────────────────

    def _attachment_folder_for_note(self, note_path: Path | None) -> Path | None:
        if note_path is None or not is_markdown_note(note_path):
            return None
        root = self._workspace_dir().resolve()
        try:
            note_key = note_path.resolve().relative_to(root).with_suffix("")
        except ValueError:
            note_key = Path(note_path.stem)
        attachments_root = (root / self.config.attachments_folder).resolve()
        folder = (attachments_root / note_key).resolve()
        try:
            folder.relative_to(attachments_root)
        except ValueError:
            return None
        return folder

    def _figure_folder(self) -> Path | None:
        return self._attachment_folder_for_note(self.current_note_path)

    def _delete_note_attachment_folder(self, note_path: Path) -> None:
        folder = self._attachment_folder_for_note(note_path)
        if folder is None or not folder.exists():
            return
        attachments_root = (self._workspace_dir().resolve() / self.config.attachments_folder).resolve()
        if folder == attachments_root:
            return
        if folder.is_symlink():
            folder.unlink()
        elif folder.is_dir():
            shutil.rmtree(folder)
        else:
            folder.unlink()
        parent = folder.parent
        while parent != attachments_root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

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
        return quote(rel.as_posix(), safe="/")

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
        drop_widget = getattr(event, "widget", None)
        if not hasattr(drop_widget, "tk"):
            drop_widget = self.text
        values = split_drop_data(drop_widget, event.data)
        if self.view_mode != "edit":
            return getattr(event, "action", None)
        self._clear_placeholder()
        self.text.mark_set(tk.INSERT, self._editor_drop_index())
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
