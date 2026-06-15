import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writeonside_app.dragdrop import compact_paths, format_paths_for_drag
from writeonside_app.platform import reveal_in_file_explorer


class ExplorerClipboardTests(unittest.TestCase):
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
