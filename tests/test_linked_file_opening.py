import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from writeonside_app.ui.notes import NotesMixin
from writeonside_app.ui.wikilinks_ui import WikiLinksMixin


class LinkedFileOpeningTests(unittest.TestCase):
    class FakeText:
        def __init__(self, line: str) -> None:
            self.line = line

        def index(self, _position: str) -> str:
            return f"1.{self.column}"

        def get(self, _start: str, _end: str) -> str:
            return self.line

    def test_external_file_can_use_windows_open_with_dialog(self) -> None:
        class Harness(NotesMixin):
            def _set_error(self, _message: str) -> None:
                raise AssertionError("OpenAs_RunDLL should not fail")

        with patch("writeonside_app.ui.notes.subprocess.Popen") as popen:
            Harness()._open_external_file(Path("data.txt"), choose_app=True)

        popen.assert_called_once_with(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", "data.txt"])

    def test_choose_app_for_directory_opens_explorer_instead(self) -> None:
        class Harness(NotesMixin):
            def _set_error(self, _message: str) -> None:
                raise AssertionError("directory open should not fail")

        with tempfile.TemporaryDirectory() as temp_dir, patch("writeonside_app.ui.notes.os.startfile", create=True) as startfile, patch(
            "writeonside_app.ui.notes.subprocess.Popen"
        ) as popen:
            folder = Path(temp_dir)
            Harness()._open_external_file(folder, choose_app=True)

        startfile.assert_called_once_with(folder)
        popen.assert_not_called()

    def test_local_non_markdown_attachment_asks_for_app_choice(self) -> None:
        calls: list[tuple[Path, bool]] = []

        class Harness(WikiLinksMixin):
            def _open_external_file(self, path: Path, *, choose_app: bool = False) -> None:
                calls.append((path, choose_app))

        result = Harness()._open_local_attachment("data.csv")

        self.assertEqual("break", result)
        self.assertEqual([(Path("data.csv"), True)], calls)

    def test_local_xlsx_attachment_asks_for_app_choice(self) -> None:
        calls: list[tuple[Path, bool]] = []

        class Harness(WikiLinksMixin):
            def _open_external_file(self, path: Path, *, choose_app: bool = False) -> None:
                calls.append((path, choose_app))

        result = Harness()._open_local_attachment("table.xlsx")

        self.assertEqual("break", result)
        self.assertEqual([(Path("table.xlsx"), True)], calls)

    def test_local_markdown_attachment_opens_inside_app(self) -> None:
        calls: list[Path] = []

        class Harness(WikiLinksMixin):
            def _open_note_from_tree(self, path: Path) -> None:
                calls.append(path)

        result = Harness()._open_local_attachment("note.md")

        self.assertEqual("break", result)
        self.assertEqual([Path("note.md")], calls)

    def test_edit_mode_markdown_file_link_action_opens_local_attachment(self) -> None:
        calls: list[Path] = []

        class Harness(WikiLinksMixin):
            def _open_local_attachment(self, path: str | Path) -> str:
                calls.append(Path(path))
                return "break"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note = root / "note.md"
            target = root / "data.csv"
            target.write_text("a,b\n", encoding="utf-8")
            text = self.FakeText("[data](data.csv)")
            text.column = 3
            app = Harness()
            app.text = text
            app.current_note_path = note

            action = app._edit_link_action_at(text, text.column, 0)

            self.assertIsNotNone(action)
            self.assertEqual("break", action())
            self.assertEqual([target], calls)

    def test_edit_mode_markdown_directory_link_action_opens_local_attachment(self) -> None:
        calls: list[Path] = []

        class Harness(WikiLinksMixin):
            def _open_local_attachment(self, path: str | Path) -> str:
                calls.append(Path(path))
                return "break"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note = root / "note.md"
            (root / "tables").mkdir()
            text = self.FakeText("[tables](tables)")
            text.column = 4
            app = Harness()
            app.text = text
            app.current_note_path = note

            action = app._edit_link_action_at(text, text.column, 0)

            self.assertIsNotNone(action)
            self.assertEqual("break", action())
            self.assertEqual([root / "tables"], calls)

    def test_edit_mode_wiki_link_action_opens_wikilink(self) -> None:
        calls = []

        class Harness(WikiLinksMixin):
            def _open_wikilink(self, link) -> str:
                calls.append((link.target, link.heading, link.alias))
                return "break"

        text = self.FakeText("[[Project Note#Plan|plan]]")
        text.column = 4
        app = Harness()
        app.text = text
        app.current_note_path = Path("note.md")

        action = app._edit_link_action_at(text, text.column, 0)

        self.assertIsNotNone(action)
        self.assertEqual("break", action())
        self.assertEqual([("Project Note", "Plan", "plan")], calls)


if __name__ == "__main__":
    unittest.main()
