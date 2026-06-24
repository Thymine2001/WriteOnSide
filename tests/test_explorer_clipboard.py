import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from writeonside_app.dragdrop import compact_paths, format_paths_for_drag
from writeonside_app.file_labels import colors_for_path
from writeonside_app.platform import reveal_in_file_explorer
from writeonside_app.ui.explorer import ExplorerMixin, natural_sort_key


class ExplorerClipboardTests(unittest.TestCase):
    def test_natural_sort_key_orders_numbered_notes(self) -> None:
        names = ["note1.md", "note11.md", "note2.md"]

        self.assertEqual(["note1.md", "note2.md", "note11.md"], sorted(names, key=natural_sort_key))

    def test_create_folder_uses_context_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            parent = root / "Projects"
            parent.mkdir()

            class FolderHarness(ExplorerMixin):
                def __init__(self) -> None:
                    self.root = object()
                    self.created_status = None

                def _workspace_dir(self) -> Path:
                    return root

                def _is_in_workspace(self, path: Path) -> bool:
                    return path.resolve().is_relative_to(root)

                def _explorer_paste_destination(self, _item=None) -> Path:
                    return parent

                def _refresh_explorer(self) -> None:
                    return

                def _ask_new_item_name(self, _title: str, _prompt: str, _initial_value: str = "") -> str:
                    return "Alpha"

                def _set_status_key(self, key: str, **kwargs: object) -> None:
                    self.created_status = (key, kwargs)

                def _set_error(self, _text: str) -> None:
                    self.fail("Folder creation unexpectedly failed")

            app = FolderHarness()
            app._create_explorer_folder("ignored")

            self.assertTrue((parent / "Alpha").is_dir())
            self.assertEqual(("status.folder_created", {"name": "Alpha"}), app.created_status)

    def test_compact_paths_drops_nested_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            child = root / "notes"
            child.mkdir()
            file_path = child / "a.md"
            file_path.write_text("x", encoding="utf-8")
            compacted = compact_paths([file_path, child, root / "other.txt"])
            self.assertEqual({child, root / "other.txt"}, set(compacted))

    def test_format_paths_for_drag_returns_resolved_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "note.md"
            file_path.write_text("x", encoding="utf-8")
            self.assertEqual((str(file_path.resolve()),), format_paths_for_drag([file_path]))

    def test_copy_into_same_explorer_folder_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            file_path = root / "Brito_Machine_learning.md"
            file_path.write_text("x", encoding="utf-8")

            class Harness(ExplorerMixin):
                def _ensure_imported_note_template(self, _path: Path) -> None:
                    self.fail("same-folder drop should not rewrite the note")

            app = Harness()
            self.assertIsNone(app._copy_into_explorer(file_path, root))
            self.assertEqual("x", file_path.read_text(encoding="utf-8"))

    def test_drop_from_workspace_moves_instead_of_copying(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            destination = root / "Archive"
            destination.mkdir()
            source = root / "Note.md"
            source.write_text("# Note", encoding="utf-8")

            class TreeStub:
                class TkStub:
                    @staticmethod
                    def splitlist(data):
                        return (data,)

                tk = TkStub()

            class Harness(ExplorerMixin):
                def __init__(self) -> None:
                    self.file_tree = TreeStub()
                    self.config = SimpleNamespace(file_color_tags={}, pinned_notes=[])
                    self.relocated = {}
                    self.status = None

                def _workspace_dir(self) -> Path:
                    return root

                def _is_in_workspace(self, path: Path) -> bool:
                    return path.resolve().is_relative_to(root)

                def _explorer_drop_directory(self) -> Path:
                    return destination

                def _note_paths_after_relocate(self, mapping) -> None:
                    self.relocated = mapping

                def _refresh_explorer(self) -> None:
                    return

                def _schedule_wiki_index_refresh(self) -> None:
                    return

                def _set_status_key(self, key: str, **kwargs) -> None:
                    self.status = (key, kwargs)

                def _set_error(self, message: str) -> None:
                    self.fail(message)

                def _write_note_label_metadata(self, path: Path, colors: list[str], pinned: bool) -> None:
                    return

            app = Harness()
            result = app._on_explorer_drop(SimpleNamespace(data=str(source), action="move"))

            target = destination / source.name
            self.assertEqual("move", result)
            self.assertFalse(source.exists())
            self.assertTrue(target.exists())
            self.assertEqual({source.resolve(): target.resolve()}, app.relocated)
            self.assertEqual(("status.moved_items", {"count": 1}), app.status)

    def test_pin_toggle_adds_and_removes_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            note = root / "Note.md"
            note.write_text("# Note", encoding="utf-8")

            class Harness(ExplorerMixin):
                def __init__(self) -> None:
                    self.config = SimpleNamespace(file_color_tags={}, pinned_notes=[])

                def _workspace_dir(self) -> Path:
                    return root

                def _is_in_workspace(self, path: Path) -> bool:
                    return path.resolve().is_relative_to(root)

                def _refresh_explorer(self, rebuild_index=True) -> None:
                    return

                def _write_note_label_metadata(self, path: Path, colors: list[str], pinned: bool) -> None:
                    return

            app = Harness()
            with patch("writeonside_app.ui.explorer.save_config"):
                app._toggle_note_pin(note)
                self.assertTrue(app._is_note_pinned(note))
                app._toggle_note_pin(note)
                self.assertFalse(app._is_note_pinned(note))

    def test_choosing_custom_color_migrates_existing_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            note = root / "Note.md"
            note.write_text("# Note", encoding="utf-8")

            class Harness(ExplorerMixin):
                def __init__(self) -> None:
                    self.root = object()
                    self.config = SimpleNamespace(
                        custom_tag_color="#123456",
                        file_color_tags={str(note): ["#123456"]},
                        pinned_notes=[],
                    )

                def _refresh_explorer(self, rebuild_index=True) -> None:
                    return

                def _set_error(self, message: str) -> None:
                    self.fail(message)

                def _write_note_label_metadata(self, path: Path, colors: list[str], pinned: bool) -> None:
                    return

            app = Harness()
            with patch("writeonside_app.ui.explorer.colorchooser.askcolor", return_value=((171, 205, 239), "#abcdef")), patch(
                "writeonside_app.ui.explorer.save_config"
            ):
                app._choose_custom_tag_color(note)

            self.assertEqual("#ABCDEF", app.config.custom_tag_color)
            self.assertEqual(("#ABCDEF",), colors_for_path(app.config.file_color_tags, note))

    def test_reveal_in_file_explorer_opens_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            with patch("subprocess.Popen") as popen:
                reveal_in_file_explorer(folder)
            popen.assert_called_once_with(["explorer", str(folder.resolve())])

    def test_reveal_in_file_explorer_selects_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "note.md"
            file_path.write_text("hello", encoding="utf-8")
            with patch("subprocess.Popen") as popen:
                reveal_in_file_explorer(file_path)
            popen.assert_called_once_with(["explorer", "/select,", str(file_path.resolve())])


if __name__ == "__main__":
    unittest.main()
