from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import tkinter as tk

from ..config import save_config
from ..i18n import t
from ..text_files import is_editable_text_path, is_markdown_note, read_editable_text

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover - watchdog is an optional runtime dependency at import time.
    FileSystemEvent = object  # type: ignore[assignment]
    FileSystemEventHandler = object  # type: ignore[assignment]
    Observer = None  # type: ignore[assignment]


def _resolve_event_path(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except OSError:
        return path.expanduser().absolute()


class _VaultFileEventHandler(FileSystemEventHandler):  # type: ignore[misc, valid-type]
    def __init__(self, app: "VaultWatcherMixin") -> None:
        super().__init__()
        self.app = app

    def on_any_event(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if getattr(event, "event_type", "") not in {"created", "deleted", "modified", "moved"}:
            return
        paths = [Path(str(event.src_path))]
        move: tuple[Path, Path] | None = None
        dest_path = getattr(event, "dest_path", None)
        if dest_path:
            destination = Path(str(dest_path))
            paths.append(destination)
            move = (paths[0], destination)
        try:
            directories = (
                tuple(paths)
                if bool(getattr(event, "is_directory", False))
                and getattr(event, "event_type", "") in {"deleted", "moved"}
                else ()
            )
            self.app._post_ui(
                lambda p=tuple(paths), m=move, d=directories: self.app._queue_vault_filesystem_event(
                    p,
                    m,
                    directory_paths=d,
                )
            )
        except Exception:
            pass


class VaultWatcherMixin:
    def _start_vault_watcher(self) -> None:
        self._stop_vault_watcher()
        if Observer is None:
            return
        try:
            root = self._workspace_dir().resolve()
        except OSError:
            return
        observer = Observer()
        try:
            observer.schedule(_VaultFileEventHandler(self), str(root), recursive=True)
            observer.start()
        except Exception:
            try:
                observer.stop()
            except Exception:
                pass
            return
        self._vault_observer = observer
        self._vault_watch_path = root

    def _restart_vault_watcher(self) -> None:
        self._start_vault_watcher()

    def _stop_vault_watcher(self) -> None:
        after_id = getattr(self, "_vault_refresh_after", None)
        if after_id is not None:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
            self._vault_refresh_after = None
        observer = getattr(self, "_vault_observer", None)
        if observer is not None:
            try:
                observer.stop()
                observer.join(timeout=1.0)
            except Exception:
                pass
            self._vault_observer = None
            self._vault_watch_path = None

    def _mark_vault_internal_write(self, path: Path) -> None:
        writes = getattr(self, "_vault_internal_writes", None)
        if writes is None:
            writes = {}
            self._vault_internal_writes = writes
        writes[_resolve_event_path(path)] = time.monotonic()

    def _is_recent_vault_internal_write(self, path: Path) -> bool:
        writes = getattr(self, "_vault_internal_writes", None)
        if not writes:
            return False
        now = time.monotonic()
        stale = [item for item, written_at in writes.items() if now - written_at > 3.0]
        for item in stale:
            writes.pop(item, None)
        return now - writes.get(_resolve_event_path(path), 0.0) <= 1.5

    def _changes_require_explorer_refresh(self, paths: set[Path], moves: dict[Path, Path]) -> bool:
        if moves:
            return True
        for path in paths:
            if not self._is_recent_vault_internal_write(path):
                return True
        return False

    def _queue_vault_filesystem_event(
        self,
        paths: Iterable[Path],
        move: tuple[Path, Path] | None = None,
        *,
        directory_paths: Iterable[Path] = (),
    ) -> None:
        pending_paths = getattr(self, "_vault_pending_paths", None)
        if pending_paths is None:
            pending_paths = set()
            self._vault_pending_paths = pending_paths
        for path in paths:
            pending_paths.add(_resolve_event_path(path))

        pending_directories = getattr(self, "_vault_pending_directories", None)
        if pending_directories is None:
            pending_directories = set()
            self._vault_pending_directories = pending_directories
        for path in directory_paths:
            pending_directories.add(_resolve_event_path(path))

        if move is not None:
            pending_moves = getattr(self, "_vault_pending_moves", None)
            if pending_moves is None:
                pending_moves = {}
                self._vault_pending_moves = pending_moves
            pending_moves[_resolve_event_path(move[0])] = _resolve_event_path(move[1])

        after_id = getattr(self, "_vault_refresh_after", None)
        if after_id is not None:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        self._vault_refresh_after = self.root.after(250, self._process_vault_filesystem_changes)

    def _process_vault_filesystem_changes(self) -> None:
        self._vault_refresh_after = None
        paths = set(getattr(self, "_vault_pending_paths", set()))
        moves = dict(getattr(self, "_vault_pending_moves", {}))
        directories = set(getattr(self, "_vault_pending_directories", set()))
        self._vault_pending_paths = set()
        self._vault_pending_moves = {}
        self._vault_pending_directories = set()
        if not paths and not moves:
            return

        if self._changes_require_explorer_refresh(paths, moves):
            self._schedule_explorer_refresh()
        self._schedule_tag_refresh()
        self._schedule_wiki_index_refresh()
        self._reload_current_note_after_external_change(paths, moves, directories)
        self._reload_split_notes_after_external_change(paths, moves, directories)

    def _path_was_touched(
        self,
        path: Path,
        paths: set[Path],
        directories: set[Path] | None = None,
    ) -> bool:
        target = _resolve_event_path(path)
        if target in paths:
            return True
        # A directory deletion/rename affects descendants; an ordinary sibling
        # file modification does not affect the current document.
        return any(directory == target or directory in target.parents for directory in (directories or set()))

    def _path_after_explicit_move(
        self,
        path: Path,
        moves: dict[Path, Path],
        directories: set[Path],
    ) -> Path | None:
        target = _resolve_event_path(path)
        direct = moves.get(target)
        if direct is not None:
            return direct
        for source, destination in moves.items():
            if source not in directories:
                continue
            try:
                relative = target.relative_to(source)
            except ValueError:
                continue
            return destination / relative
        return None

    def _reload_current_note_after_external_change(
        self,
        paths: set[Path],
        moves: dict[Path, Path],
        directories: set[Path] | None = None,
    ) -> None:
        current = getattr(self, "current_note_path", None)
        if current is None:
            return
        current = _resolve_event_path(Path(current))
        directories = directories or set()
        moved_to = self._path_after_explicit_move(current, moves, directories)
        target = moved_to or current
        if self._is_recent_vault_internal_write(target):
            return
        if moved_to is None and not self._path_was_touched(current, paths, directories):
            return
        if getattr(self, "_dirty", False):
            self._set_status_key("status.unsaved")
            return
        if not target.exists():
            self.current_note_path = None
            self.config.current_note_path = ""
            save_config(self.config)
            self._load_initial_note()
            return
        self._reload_main_editor_from_disk(target)

    def _reload_main_editor_from_disk(self, path: Path) -> None:
        path = _resolve_event_path(path)
        if is_markdown_note(path):
            self._open_note_file(path)
            return
        if not is_editable_text_path(path):
            return
        try:
            content, encoding, newline = read_editable_text(path)
        except (OSError, UnicodeError) as exc:
            self._set_error(t("error.open_failed", exc=exc))
            return
        self.current_note_path = path
        self._document_encoding = encoding
        self._document_newline = newline
        self.config.current_note_path = ""
        self._reset_editor_structure()
        self._set_editor_content(content)
        self._dirty = False
        self._update_note_title()
        self._highlight_current_note()
        self._set_status_key("status.opened")
        self._update_view_buttons()
        save_config(self.config)

    def _reload_split_notes_after_external_change(
        self,
        paths: set[Path],
        moves: dict[Path, Path],
        directories: set[Path] | None = None,
    ) -> None:
        directories = directories or set()
        for note in list(getattr(self, "_split_notes", [])):
            path = _resolve_event_path(Path(note["path"]))
            moved_to = self._path_after_explicit_move(path, moves, directories)
            target = moved_to or path
            if self._is_recent_vault_internal_write(target):
                continue
            if moved_to is None and not self._path_was_touched(path, paths, directories):
                continue
            if note.get("dirty"):
                continue
            if not target.exists():
                continue
            note["path"] = target
            self._render_split_note(note)
