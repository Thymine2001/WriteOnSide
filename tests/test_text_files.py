import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from writeonside_app.storage import safe_write_text
from writeonside_app.text_files import (
    is_editable_text_path,
    is_markdown_note,
    read_editable_text,
    requested_file_from_args,
)
from writeonside_app.ui.editor import EditorMixin
from writeonside_app.platform import SingleInstanceGuard, file_open_command, normalize_file_association_extensions


class TextFileTests(unittest.TestCase):
    def test_code_and_text_formats_are_editable_but_only_md_is_a_note(self):
        for suffix in (".html", ".py", ".r", ".rmd", ".rs", ".cpp", ".c", ".toml", ".txt", ".json", ".yaml"):
            path = Path(f"example{suffix}")
            self.assertTrue(is_editable_text_path(path))
            self.assertFalse(is_markdown_note(path))
        self.assertTrue(is_editable_text_path(Path("example.md")))
        self.assertTrue(is_markdown_note(Path("example.md")))
        self.assertFalse(is_editable_text_path(Path("example.png")))
        self.assertTrue(is_editable_text_path(Path("Dockerfile")))
        self.assertTrue(is_editable_text_path(Path("Makefile")))

    def test_requested_file_from_args_returns_existing_external_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "outside.py"
            path.write_text("print('outside')", encoding="utf-8")
            self.assertEqual(path.resolve(), requested_file_from_args(["--ignored", str(path)]))
            self.assertIsNone(requested_file_from_args([str(path.with_name("missing.py"))]))

    def test_single_instance_open_request_returns_original_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            external = root / "requested.cpp"
            external.write_text("int main() {}", encoding="utf-8")
            request = root / "request.json"
            request.write_text(json.dumps(str(external)), encoding="utf-8")
            guard = object.__new__(SingleInstanceGuard)

            with patch("writeonside_app.platform.OPEN_REQUEST_PATH", request):
                self.assertEqual(external.resolve(), guard.consume_open_request())

            self.assertFalse(request.exists())

    def test_windows_file_association_command_forwards_quoted_path(self):
        self.assertTrue(file_open_command().endswith('"%1"'))
        self.assertEqual(
            (".cpp", ".md", ".py"),
            normalize_file_association_extensions(["PY", ".md", ".CPP", ".py"]),
        )

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

    def test_external_file_save_updates_original_path_and_preserves_newlines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            external = root / "external.py"
            external.write_bytes(b"value = 1\r\n")

            class SaveHarness(EditorMixin):
                current_note_path = external
                config = SimpleNamespace(current_note_path="")
                _document_encoding = "utf-8"
                _document_newline = "\r\n"
                _dirty = True
                _autosave_after = None

                def _get_editor_content(self) -> str:
                    return "value = 2\n"

                def _is_in_workspace(self, _path: Path) -> bool:
                    return False

                def _workspace_dir(self) -> Path:
                    return root / "Vault"

                def _mark_vault_internal_write(self, _path: Path) -> None:
                    return

                def _set_status_key(self, _key: str, **_kwargs: object) -> None:
                    return

            with patch("writeonside_app.ui.editor.save_config"):
                SaveHarness()._save_note(False)

            self.assertEqual(b"value = 2\r\n", external.read_bytes())
            self.assertFalse((root / "Vault" / "external.py").exists())


if __name__ == "__main__":
    unittest.main()
