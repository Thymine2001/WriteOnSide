import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writeonside_app.dragdrop import compact_paths, format_paths_for_drag
from writeonside_app.platform import reveal_in_file_explorer
from writeonside_app.ui.explorer import ExplorerMixin


class ExplorerClipboardTests(unittest.TestCase):
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

                def _set_status_key(self, key: str, **kwargs: object) -> None:
                    self.created_status = (key, kwargs)

                def _set_error(self, _text: str) -> None:
                    self.fail("Folder creation unexpectedly failed")

            app = FolderHarness()
            with patch("writeonside_app.ui.explorer.simpledialog.askstring", return_value="Alpha"):
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
