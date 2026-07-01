from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from writeonside_app.ui.vault_watcher import VaultWatcherMixin, _resolve_event_path


class _WatcherHarness(VaultWatcherMixin):
    def __init__(self, root: Path) -> None:
        self.root_dir = root
        self.current_note_path: Path | None = root / "Note.txt"
        self.config = SimpleNamespace(current_note_path="")
        self._dirty = False
        self._vault_pending_paths: set[Path] = set()
        self._vault_pending_moves: dict[Path, Path] = {}
        self._vault_pending_directories: set[Path] = set()
        self._vault_internal_writes: dict[Path, float] = {}
        self.reloaded: list[Path] = []
        self.status_keys: list[str] = []
        self.explorer_refreshes = 0
        self.tag_refreshes = 0
        self.wiki_refreshes = 0

    def _workspace_dir(self) -> Path:
        return self.root_dir

    def _schedule_explorer_refresh(self) -> None:
        self.explorer_refreshes += 1

    def _schedule_tag_refresh(self) -> None:
        self.tag_refreshes += 1

    def _schedule_wiki_index_refresh(self) -> None:
        self.wiki_refreshes += 1

    def _schedule_attachment_index_refresh(self) -> None:
        self.attachment_refreshes = getattr(self, "attachment_refreshes", 0) + 1

    def _reload_main_editor_from_disk(self, path: Path) -> None:
        self.reloaded.append(path)

    def _reload_split_notes_after_external_change(
        self,
        paths: set[Path],
        moves: dict[Path, Path],
        directories: set[Path] | None = None,
    ) -> None:
        return

    def _set_status_key(self, key: str, **_kwargs: object) -> None:
        self.status_keys.append(key)

    def _load_initial_note(self) -> None:
        return


class VaultWatcherTests(unittest.TestCase):
    def test_external_change_refreshes_indexes_and_reloads_clean_current_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note = root / "Note.txt"
            note.write_text("external", encoding="utf-8")
            app = _WatcherHarness(root)
            app._vault_pending_paths = {_resolve_event_path(note)}

            with patch("writeonside_app.ui.vault_watcher.save_config"):
                app._process_vault_filesystem_changes()

            self.assertEqual([_resolve_event_path(note)], app.reloaded)
            self.assertEqual(1, app.explorer_refreshes)
            self.assertEqual(1, app.tag_refreshes)
            self.assertEqual(1, app.wiki_refreshes)

    def test_external_change_does_not_overwrite_dirty_current_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note = root / "Note.txt"
            note.write_text("external", encoding="utf-8")
            app = _WatcherHarness(root)
            app._dirty = True
            app._vault_pending_paths = {_resolve_event_path(note)}

            with patch("writeonside_app.ui.vault_watcher.save_config"):
                app._process_vault_filesystem_changes()

            self.assertEqual([], app.reloaded)
            self.assertIn("status.unsaved", app.status_keys)
            self.assertEqual(1, app.explorer_refreshes)

    def test_recent_internal_write_does_not_reload_current_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note = root / "Note.txt"
            note.write_text("saved by app", encoding="utf-8")
            app = _WatcherHarness(root)
            app._mark_vault_internal_write(note)
            app._vault_pending_paths = {_resolve_event_path(note)}

            with patch("writeonside_app.ui.vault_watcher.save_config"):
                app._process_vault_filesystem_changes()

            self.assertEqual([], app.reloaded)
            self.assertEqual(0, app.explorer_refreshes)

    def test_sibling_file_change_does_not_reload_current_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            current = root / "Note.txt"
            sibling = root / "Other.txt"
            current.write_text("current", encoding="utf-8")
            sibling.write_text("changed", encoding="utf-8")
            app = _WatcherHarness(root)
            app.current_note_path = current
            app._vault_pending_paths = {_resolve_event_path(sibling)}

            app._process_vault_filesystem_changes()

            self.assertEqual([], app.reloaded)

    def test_parent_directory_modified_event_does_not_reload_current_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            current = root / "Note.txt"
            current.write_text("current", encoding="utf-8")
            app = _WatcherHarness(root)
            app.current_note_path = current
            # Directory modified/created events are queued as paths for index
            # refresh, but not as destructive directory events.
            app._vault_pending_paths = {_resolve_event_path(root)}

            app._process_vault_filesystem_changes()

            self.assertEqual([], app.reloaded)

    def test_directory_move_relocates_current_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_folder = root / "Old"
            new_folder = root / "New"
            old_folder.mkdir()
            current = old_folder / "Note.txt"
            current.write_text("current", encoding="utf-8")
            app = _WatcherHarness(root)
            app.current_note_path = current
            old_folder.rename(new_folder)
            app._vault_pending_paths = {_resolve_event_path(old_folder), _resolve_event_path(new_folder)}
            app._vault_pending_directories = {_resolve_event_path(old_folder), _resolve_event_path(new_folder)}
            app._vault_pending_moves = {_resolve_event_path(old_folder): _resolve_event_path(new_folder)}

            app._process_vault_filesystem_changes()

            self.assertEqual([_resolve_event_path(new_folder / "Note.txt")], app.reloaded)


if __name__ == "__main__":
    unittest.main()
