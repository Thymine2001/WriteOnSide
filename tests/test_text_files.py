import tempfile
import unittest
from pathlib import Path

from writeonside_app.storage import safe_write_text
from writeonside_app.text_files import (
    is_editable_text_path,
    is_markdown_note,
    read_editable_text,
)


class TextFileTests(unittest.TestCase):
    def test_code_and_text_formats_are_editable_but_only_md_is_a_note(self):
        for suffix in (".py", ".r", ".rmd", ".toml", ".txt", ".json", ".yaml"):
            path = Path(f"example{suffix}")
            self.assertTrue(is_editable_text_path(path))
            self.assertFalse(is_markdown_note(path))
        self.assertTrue(is_editable_text_path(Path("example.md")))
        self.assertTrue(is_markdown_note(Path("example.md")))
        self.assertFalse(is_editable_text_path(Path("example.png")))

    def test_utf8_crlf_round_trip_does_not_add_bom_or_duplicate_carriage_returns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.py"
            path.write_bytes('print("cafe")\r\n'.encode("utf-8"))
            content, encoding, newline = read_editable_text(path)
            safe_write_text(path, content + "# end\n", encoding=encoding, newline=newline)
            data = path.read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"\r\n", data)
            self.assertNotIn(b"\r\r\n", data)


if __name__ == "__main__":
    unittest.main()
