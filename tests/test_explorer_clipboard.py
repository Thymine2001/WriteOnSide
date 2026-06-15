import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writeonside_app.platform import reveal_in_file_explorer


class ExplorerClipboardTests(unittest.TestCase):
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
