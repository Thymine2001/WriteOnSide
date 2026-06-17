from __future__ import annotations

import re
import webbrowser
from pathlib import Path
import tkinter as tk

from ..frontmatter import note_template, parse_front_matter
from ..markdown import resolve_markdown_path
from ..storage import read_text_file, safe_note_name, safe_write_text
from ..obsidian_md import find_block_line
from ..i18n import t
from ..text_files import is_markdown_note
from ..theme import *  # noqa: F401,F403
from ..wikilinks import WikiLink, WikiLinkIndex, WikiIndexState, refresh_wiki_index, WIKI_LINK_PATTERN

MARKDOWN_URL_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\((https?://[^)\s]+)\)", re.IGNORECASE)
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\n]+)\)")
BARE_URL_PATTERN = re.compile(r"https?://[^\s<>)]+", re.IGNORECASE)


class WikiLinksMixin:
    def _setup_wikilinks(self) -> None:
        self._wiki_index, self._wiki_index_state = refresh_wiki_index(self._workspace_dir())
        self._wiki_index_after: str | None = None
        self._wiki_completion: tk.Toplevel | None = None
        self._wiki_completion_list: tk.Listbox | None = None
        self._wiki_completion_notes = []
        self._wiki_completion_start = ""
        self.text.bind("<KeyRelease>", self._on_wiki_completion_keyrelease, add="+")
        self.text.bind("<Control-Button-1>", self._on_edit_wikilink_click, add="+")
        self.text.bind("<Down>", lambda _event: self._move_wiki_completion(1), add="+")
        self.text.bind("<Up>", lambda _event: self._move_wiki_completion(-1), add="+")
        self.text.bind("<Tab>", lambda _event: self._accept_wiki_completion(), add="+")

    def _schedule_wiki_index_refresh(self) -> None:
        if self._wiki_index_after is not None:
            try:
                self.root.after_cancel(self._wiki_index_after)
            except tk.TclError:
                pass
        self._wiki_index_after = self.root.after(180, self._refresh_wiki_index)

    def _refresh_wiki_index(self) -> None:
        self._wiki_index_after = None
        previous = getattr(self, "_wiki_index_state", None)
        self._wiki_index, self._wiki_index_state = refresh_wiki_index(self._workspace_dir(), previous)

    def _wiki_asset_resolver(self, target: str, source: Path | None) -> Path | None:
        return self._wiki_index.resolve_asset(target, source)

    def _wiki_note_embed(self, target: str, source: Path | None) -> tuple[str, str] | None:
        path = self._wiki_index.resolve(target, source)
        if path is None:
            return None
        try:
            content = read_text_file(path)
        except OSError:
            return None
        from ..frontmatter import parse_front_matter, split_front_matter

        metadata = parse_front_matter(content, path.stem)
        _header, body = split_front_matter(content)
        title = metadata.title or path.stem
        return title, body.strip()

    def _bind_rendered_wikilinks(self) -> None:
        for tag, url in getattr(self.read_text, "_external_links", {}).items():
            self.read_text.tag_bind(tag, "<Enter>", lambda _event: self.read_text.configure(cursor="hand2"))
            self.read_text.tag_bind(tag, "<Leave>", lambda _event: self.read_text.configure(cursor="arrow"))
            self.read_text.tag_bind(
                tag,
                "<Control-Button-1>",
                lambda _event, target=url: self._open_external_url(target),
            )
        for tag, path in getattr(self.read_text, "_attachment_links", {}).items():
            self.read_text.tag_bind(tag, "<Enter>", lambda _event: self.read_text.configure(cursor="hand2"))
            self.read_text.tag_bind(tag, "<Leave>", lambda _event: self.read_text.configure(cursor="arrow"))
            self.read_text.tag_bind(
                tag,
                "<Button-1>",
                lambda _event, target=path: self._open_local_attachment(target),
            )
        for tag, link in getattr(self.read_text, "_wiki_links", {}).items():
            self.read_text.tag_bind(tag, "<Enter>", lambda _event: self.read_text.configure(cursor="hand2"))
            self.read_text.tag_bind(tag, "<Leave>", lambda _event: self.read_text.configure(cursor="arrow"))
            self.read_text.tag_bind(
                tag,
                "<Button-1>",
                lambda _event, target=link: self._open_wikilink(target),
            )

    def _open_wikilink(self, link: WikiLink) -> str:
        source = self.current_note_path
        target = self._wiki_index.resolve(link.target, source)
        if target is None:
            target = source if not link.target else self._create_wikilink_note(link.target)
        if target is None:
            return "break"
        self._open_note_from_tree(target)
        if link.block_id:
            self.root.after_idle(lambda block_id=link.block_id, note=target: self._jump_to_wiki_block(block_id, note))
        elif link.heading:
            self.root.after_idle(lambda heading=link.heading: self._jump_to_wiki_heading(heading))
        return "break"

    def _open_external_url(self, url: str) -> str:
        target = url.strip()
        if not BARE_URL_PATTERN.fullmatch(target):
            return "break"
        webbrowser.open(target)
        return "break"

    def _open_local_attachment(self, path: str | Path) -> str:
        self._open_external_file(Path(path))
        return "break"

    def _create_wikilink_note(self, target: str) -> Path | None:
        raw = target.strip().replace("\\", "/").strip("/")
        parts = [part for part in Path(raw).parts if part not in {"", ".", ".."}]
        if not parts:
            return None
        folder = self._workspace_dir()
        for part in parts[:-1]:
            cleaned = re.sub(r'[<>:"|?*\x00-\x1f]', "-", part).strip().strip(".")
            if cleaned:
                folder /= cleaned
        path = folder / safe_note_name(parts[-1])
        if not path.exists():
            try:
                folder.mkdir(parents=True, exist_ok=True)
                safe_write_text(path, note_template(path), workspace_root=self._workspace_dir())
            except OSError as exc:
                self._set_error(t("error.wikilink_create_failed", exc=exc))
                return None
        self._schedule_wiki_index_refresh()
        self._refresh_explorer()
        return path.resolve()

    def _jump_to_wiki_block(self, block_id: str, note_path: Path | None = None) -> None:
        path = note_path or self.current_note_path
        if path is None:
            self._set_status_key("status.block_not_found", block_id=block_id)
            return
        try:
            content = read_text_file(path)
        except OSError:
            self._set_status_key("status.block_not_found", block_id=block_id)
            return
        line = find_block_line(content, block_id)
        if line is None:
            self._set_status_key("status.block_not_found", block_id=block_id)
            return
        self._jump_to_outline(line, f"^{block_id}")

    def _jump_to_wiki_heading(self, heading: str) -> None:
        normalized = heading.strip().casefold()
        for item in self._parse_outline():
            if str(item["title"]).strip().casefold() != normalized:
                continue
            line = int(item["line"])
            self._jump_to_outline(line, str(item["title"]))
            return
        self._set_status_key("status.heading_not_found", heading=heading)

    def _on_edit_wikilink_click(self, event) -> str | None:
        widget = event.widget if isinstance(getattr(event, "widget", None), tk.Text) else self.text
        source = self.current_note_path
        is_main_editor = widget is self.text
        if not is_main_editor and hasattr(self, "_note_for_text_widget"):
            split_note = self._note_for_text_widget(widget)
            if split_note is not None:
                source = Path(split_note["path"])
        if source is None or not is_markdown_note(source):
            return None
        index = widget.index(f"@{event.x},{event.y}")
        line, column = (int(value) for value in index.split("."))
        line_text = widget.get(f"{line}.0", f"{line}.end")
        for match in MARKDOWN_URL_PATTERN.finditer(line_text):
            if match.start() <= column <= match.end():
                return self._open_external_url(match.group(1))
        for match in BARE_URL_PATTERN.finditer(line_text):
            if match.start() <= column <= match.end():
                return self._open_external_url(match.group(0))
        for match in MARKDOWN_LINK_PATTERN.finditer(line_text):
            if not (match.start() <= column <= match.end()):
                continue
            target = resolve_markdown_path(match.group(1), source)
            if target is not None and target.exists() and target.is_file() and target.suffix.casefold() != ".md":
                return self._open_local_attachment(target)
        if not is_main_editor:
            return None
        for match in WIKI_LINK_PATTERN.finditer(line_text):
            if match.start() <= column <= match.end():
                destination, separator, alias = match.group(2).partition("|")
                target, heading_separator, heading = destination.partition("#")
                heading = heading.strip() if heading_separator else ""
                block_id = ""
                if heading.startswith("^"):
                    block_id = heading[1:].strip()
                    heading = ""
                return self._open_wikilink(
                    WikiLink(
                        raw=match.group(0),
                        target=target.strip(),
                        heading=heading,
                        alias=alias.strip() if separator else "",
                        embed=bool(match.group(1)),
                        start=match.start(),
                        end=match.end(),
                        block_id=block_id,
                    )
                )
        return None

    def _on_wiki_completion_keyrelease(self, event) -> None:
        if event.keysym in {"Up", "Down", "Return", "Tab", "Escape"}:
            return
        if not self._is_markdown_document() or self.view_mode != "edit":
            self._hide_wiki_completion()
            return
        cursor = self.text.index(tk.INSERT)
        line_start = f"{cursor.split('.')[0]}.0"
        before = self.text.get(line_start, cursor)
        match = re.search(r"\[\[([^\[\]\n|#]*)$", before)
        if not match:
            self._hide_wiki_completion()
            return
        query = match.group(1)
        self._wiki_completion_start = self.text.index(f"{cursor}-{len(query) + 2}c")
        suggestions = [
            note
            for note in self._wiki_index.suggestions(query)
            if not self.current_note_path or note.path != self.current_note_path.resolve()
        ][:10]
        if suggestions:
            self._show_wiki_completion(suggestions)
        else:
            self._hide_wiki_completion()

    def _show_wiki_completion(self, notes) -> None:
        self._hide_wiki_completion()
        g = globals()
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        listbox = tk.Listbox(
            popup,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            selectbackground=g["ACCENT"],
            selectforeground=self._contrast_text(g["ACCENT"]),
            activestyle="none",
            relief="flat",
            highlightthickness=1,
            highlightbackground=g["BORDER"],
            font=(self.config.font_family, max(9, self.config.font_size)),
            height=min(8, len(notes)),
            width=32,
        )
        listbox.pack(fill="both", expand=True)
        root = self._workspace_dir()
        for note in notes:
            try:
                relative = note.path.relative_to(root)
            except ValueError:
                relative = note.path
            suffix = f"  -  {relative.parent}" if relative.parent != Path(".") else ""
            listbox.insert(tk.END, f"{note.title}{suffix}")
        listbox.selection_set(0)
        listbox.bind("<ButtonRelease-1>", lambda _event: self._accept_wiki_completion())
        bbox = self.text.bbox(tk.INSERT) or (0, 0, 0, 0)
        popup.update_idletasks()
        x = self.text.winfo_rootx() + bbox[0]
        y = self.text.winfo_rooty() + bbox[1] + bbox[3] + 4
        x = max(self.work_left + 4, min(x, self.work_right - popup.winfo_reqwidth() - 4))
        y = max(self.work_top + 4, min(y, self.work_bottom - popup.winfo_reqheight() - 4))
        popup.geometry(f"+{x}+{y}")
        self._wiki_completion = popup
        self._wiki_completion_list = listbox
        self._wiki_completion_notes = list(notes)

    def _move_wiki_completion(self, delta: int) -> str | None:
        listbox = self._wiki_completion_list
        if not listbox or not listbox.winfo_exists():
            return None
        current = listbox.curselection()
        index = current[0] if current else 0
        index = max(0, min(listbox.size() - 1, index + delta))
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index)
        listbox.see(index)
        return "break"

    def _accept_wiki_completion(self) -> str | None:
        listbox = self._wiki_completion_list
        if not listbox or not listbox.winfo_exists() or not self._wiki_completion_notes:
            return None
        selection = listbox.curselection()
        note = self._wiki_completion_notes[selection[0] if selection else 0]
        self.text.delete(self._wiki_completion_start, tk.INSERT)
        value = f"[[{note.title}]]"
        self.text.insert(self._wiki_completion_start, value)
        self.text.mark_set(tk.INSERT, f"{self._wiki_completion_start}+{len(value)}c")
        self._hide_wiki_completion()
        self.text.focus_set()
        return "break"

    def _hide_wiki_completion(self) -> None:
        if self._wiki_completion is not None:
            try:
                self._wiki_completion.destroy()
            except tk.TclError:
                pass
        self._wiki_completion = None
        self._wiki_completion_list = None
        self._wiki_completion_notes = []

    def _show_backlinks_popup(self) -> None:
        if getattr(self, "_backlinks_popup", None) is not None:
            self._close_backlinks_popup()
            return
        if not self.current_note_path or not self._is_markdown_document():
            self._set_status_key("status.backlinks_md_only")
            return
        self._refresh_wiki_index()
        backlinks = self._wiki_index.backlinks(self.current_note_path)
        g = globals()
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        self._backlinks_popup = popup
        width = min(360, max(250, self.panel_w - 24))
        height = min(330, 72 + max(1, len(backlinks)) * 42)
        frame = tk.Frame(popup, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"])
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, bg=g["SURFACE"])
        header.pack(fill="x")
        tk.Label(
            header,
            text=t("backlinks.title", count=len(backlinks)),
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=12, pady=(10, 7))
        close_btn = tk.Label(
            header,
            text="\u00d7",
            bg=g["SURFACE"],
            fg=g["MUTED"],
            font=("Segoe UI", 13),
            cursor="hand2",
            padx=8,
            pady=3,
        )
        close_btn.pack(side="right", padx=(2, 4), pady=(4, 2))
        close_btn.bind("<Button-1>", lambda _event: self._close_backlinks_popup())
        close_btn.bind("<Enter>", lambda _event: close_btn.configure(bg=globals()["SURFACE_2"], fg=globals()["TEXT"]))
        close_btn.bind("<Leave>", lambda _event: close_btn.configure(bg=globals()["SURFACE"], fg=globals()["MUTED"]))
        if backlinks:
            for note, link in backlinks:
                row = tk.Label(
                    frame,
                    text=f"{note.title}\n{link.raw}",
                    bg=g["SURFACE"],
                    fg=g["TEXT_SOFT"],
                    font=("Segoe UI", 9),
                    anchor="w",
                    justify="left",
                    cursor="hand2",
                    padx=12,
                    pady=5,
                )
                row.pack(fill="x")
                row.bind("<Enter>", lambda _event, widget=row: widget.configure(bg=globals()["SURFACE_2"]))
                row.bind("<Leave>", lambda _event, widget=row: widget.configure(bg=globals()["SURFACE"]))
                row.bind(
                    "<Button-1>",
                    lambda _event, path=note.path, window=popup: self._open_backlink(path, window),
                )
        else:
            tk.Label(
                frame,
                text=t("backlinks.empty"),
                bg=g["SURFACE"],
                fg=g["MUTED"],
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(fill="x", padx=12, pady=12)
        popup.update_idletasks()
        x = self.backlinks_btn.winfo_rootx() + self.backlinks_btn.winfo_width() - width
        y = self.backlinks_btn.winfo_rooty() + self.backlinks_btn.winfo_height() + 5
        x = max(self.work_left + 4, min(x, self.work_right - width - 4))
        y = max(self.work_top + 4, min(y, self.work_bottom - height - 4))
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.bind("<Escape>", lambda _event: self._close_backlinks_popup() or "break")
        popup.bind("<FocusOut>", lambda _event: popup.after(80, self._close_backlinks_if_unfocused))
        popup.focus_force()

    def _open_backlink(self, path: Path, popup: tk.Toplevel) -> None:
        self._close_backlinks_popup()
        self._open_note_from_tree(path)

    def _close_backlinks_if_unfocused(self) -> None:
        popup = getattr(self, "_backlinks_popup", None)
        if popup is None:
            return
        try:
            focused = popup.focus_get()
            if focused is not None and str(focused).startswith(str(popup)):
                return
        except tk.TclError:
            pass
        self._close_backlinks_popup()

    def _close_backlinks_popup(self) -> None:
        popup = getattr(self, "_backlinks_popup", None)
        self._backlinks_popup = None
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
