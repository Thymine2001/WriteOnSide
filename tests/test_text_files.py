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
from writeonside_app.ui.notes import NotesMixin
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

    def test_utf8_lf_read_preserves_content_and_newline_style(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.md"
            path.write_bytes(b"one\ntwo\n")
            content, encoding, newline = read_editable_text(path)
            self.assertEqual("one\ntwo\n", content)
            self.assertEqual("utf-8", encoding)
            self.assertEqual("\n", newline)

    def test_read_editable_text_supports_utf16_and_crlf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.md"
            path.write_text("one\r\ntwo\r\n", encoding="utf-16", newline="")
            content, encoding, newline = read_editable_text(path)
            self.assertEqual("one\ntwo\n", content)
            self.assertEqual("utf-16", encoding)
            self.assertEqual("\r\n", newline)

    def test_read_editable_text_falls_back_to_gb18030(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.md"
            path.write_bytes("中文\rend".encode("gb18030"))
            content, encoding, newline = read_editable_text(path)
            self.assertEqual("中文\nend", content)
            self.assertEqual("gb18030", encoding)
            self.assertEqual("\r", newline)

    def test_read_editable_text_rejects_binary_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.txt"
            path.write_bytes(b"text\x00more")
            with self.assertRaisesRegex(UnicodeError, "binary"):
                read_editable_text(path)

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

    def test_additional_external_file_prefers_split_but_initial_file_uses_main(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main = root / "main.md"
            external = root / "external.cpp"
            main.write_text("# Main", encoding="utf-8")
            external.write_text("int main() {}", encoding="utf-8")

            class OpenHarness(NotesMixin):
                current_note_path = main

                def __init__(self) -> None:
                    self.split_paths: list[Path] = []
                    self.main_paths: list[Path] = []

                def _open_note_split(self, path: Path) -> bool:
                    self.split_paths.append(path)
                    return True

                def _open_text_file_from_tree(self, path: Path) -> None:
                    self.main_paths.append(path)

                def _set_error(self, _message: str) -> None:
                    self.fail("Opening unexpectedly failed")

            app = OpenHarness()
            app._open_file_in_editor(external, reveal_panel=False)
            self.assertEqual([external.resolve()], app.split_paths)
            self.assertEqual([], app.main_paths)

            app._open_file_in_editor(external, reveal_panel=False, prefer_split=False)
            self.assertEqual([external.resolve()], app.main_paths)

    def test_four_file_limit_rejects_fifth_external_file_before_creating_ui(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main = root / "main.md"
            fifth = root / "fifth.py"
            main.write_text("# Main", encoding="utf-8")
            fifth.write_text("print('fifth')", encoding="utf-8")

            class LimitHarness(NotesMixin):
                current_note_path = main

                def __init__(self) -> None:
                    self._split_notes = [{"path": root / f"split-{index}.py"} for index in range(3)]
                    self.error = ""

                def _set_error(self, message: str) -> None:
                    self.error = message

            app = LimitHarness()
            self.assertTrue(app._open_note_split(fifth))
            self.assertIn("4", app.error)

    def test_external_file_title_uses_file_name_and_parent_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Vault"
            external_dir = Path(temp_dir) / "Outside"
            root.mkdir()
            external_dir.mkdir()
            external = external_dir / "example.py"
            external.write_text("print('x')", encoding="utf-8")

            class LabelSpy:
                def __init__(self) -> None:
                    self.text = ""

                def config(self, **kwargs: str) -> None:
                    self.text = kwargs["text"]

            class RootSpy:
                def __init__(self) -> None:
                    self.title_text = ""

                def title(self, text: str) -> None:
                    self.title_text = text

            class TitleHarness(NotesMixin):
                preview_path = None
                current_note_path = external

                def __init__(self) -> None:
                    self.app_title_label = LabelSpy()
                    self.note_title = LabelSpy()
                    self.root = RootSpy()

                def _workspace_dir(self) -> Path:
                    return root

                def _update_hotkey_hints(self) -> None:
                    return None

            app = TitleHarness()
            app._update_note_title()

            self.assertEqual("example.py", app.app_title_label.text)
            self.assertEqual(str(external_dir), app.note_title.text)
            self.assertEqual("example.py - WriteOnSide", app.root.title_text)

    def test_workspace_file_title_uses_relative_parent_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Vault"
            folder = root / "Folder"
            folder.mkdir(parents=True)
            note = folder / "example.md"
            note.write_text("# Example", encoding="utf-8")

            class TitleHarness(NotesMixin):
                preview_path = None
                current_note_path = note

                def _workspace_dir(self) -> Path:
                    return root

            app = TitleHarness()
            self.assertEqual(("example.md", "Folder"), app._active_title_parts())

    def test_closing_preview_without_restore_resyncs_visible_frame(self):
        class FrameSpy:
            def __init__(self) -> None:
                self.packed = False
                self.pack_calls: list[dict[str, str]] = []

            def pack(self, **kwargs: str) -> None:
                self.packed = True
                self.pack_calls.append(kwargs)

            def pack_forget(self) -> None:
                self.packed = False

        class RootSpy:
            def after_cancel(self, _after_id: str) -> None:
                return None

        class PreviewHarness(NotesMixin):
            def __init__(self, view_mode: str) -> None:
                self.preview_path = Path("preview.bin")
                self._preview_previous_mode = view_mode
                self._preview_render_after = "after-id"
                self.view_mode = "read"
                self.root = RootSpy()
                self.edit_frame = FrameSpy()
                self.read_frame = FrameSpy()

        edit_app = PreviewHarness("edit")
        edit_app.read_frame.packed = True
        edit_app._close_file_preview(restore_note=False)
        self.assertIsNone(edit_app.preview_path)
        self.assertTrue(edit_app.edit_frame.packed)
        self.assertFalse(edit_app.read_frame.packed)

        read_app = PreviewHarness("read")
        read_app.read_frame.packed = True
        read_app._close_file_preview(restore_note=False)
        self.assertTrue(read_app.read_frame.packed)
        self.assertFalse(read_app.edit_frame.packed)


if __name__ == "__main__":
    unittest.main()
