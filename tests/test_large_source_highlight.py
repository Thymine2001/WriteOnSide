from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from writeonside_app.syntax_highlight import SyntaxSpan
from writeonside_app.ui.editor import EditorMixin
from writeonside_app.ui.notes import NotesMixin


class FakeText:
    def __init__(self, content: str, top_line: int = 5000, bottom_line: int = 5020) -> None:
        self.content = content
        self.lines = content.split("\n")
        self.top_line = top_line
        self.bottom_line = bottom_line
        self.added: list[tuple[str, str, str]] = []
        self.removed: list[tuple[str, str, str]] = []

    def count(self, _start: str, _end: str, _what: str) -> tuple[str]:
        return (str(len(self.content)),)

    def index(self, index: str) -> str:
        if index == "end-1c":
            return f"{len(self.lines)}.{len(self.lines[-1])}"
        if index == "@0,0":
            return f"{self.top_line}.0"
        if index.startswith("@0,"):
            return f"{self.bottom_line}.0"
        return index

    def winfo_height(self) -> int:
        return 240

    def get(self, start: str, end: str) -> str:
        start_line = int(start.split(".", 1)[0])
        end_line = int(end.split(".", 1)[0])
        return "\n".join(self.lines[start_line - 1 : end_line])

    def tag_configure(self, *_args, **_kwargs) -> None:
        return None

    def tag_add(self, tag: str, start: str, end: str) -> None:
        self.added.append((tag, start, end))

    def tag_remove(self, tag: str, start: str, end: str) -> None:
        self.removed.append((tag, start, end))

    def tag_raise(self, _tag: str) -> None:
        return None


class LargeSourceHighlightTests(unittest.TestCase):
    def test_main_editor_large_source_highlights_visible_fragment(self) -> None:
        content = "\n".join(f"print({index})" for index in range(12_000))
        fake_text = FakeText(content)

        class Harness(EditorMixin):
            pass

        app = Harness()
        app.text = fake_text
        app.current_note_path = Path("large.py")
        app.config = SimpleNamespace(font_size=11)
        app._editor_color_tags = set()
        app._large_highlight_range = None

        captured: list[str] = []

        def fake_source_token_spans(code: str, _path: Path, **_kwargs) -> tuple[SyntaxSpan, ...]:
            captured.append(code)
            return (SyntaxSpan(0, min(5, len(code)), "#ff0000"),)

        with patch("writeonside_app.ui.editor.source_token_spans", fake_source_token_spans):
            app._apply_source_file_highlight()

        self.assertEqual(1, len(captured))
        self.assertLess(captured[0].count("\n"), content.count("\n") // 10)
        self.assertIn(("source_code", "4900.0", "5120.end"), fake_text.added)

    def test_split_large_source_highlights_visible_fragment(self) -> None:
        content = "\n".join(f"print({index})" for index in range(12_000))
        fake_text = FakeText(content)
        note = {"text": fake_text, "path": Path("split.py"), "color_tags": set(), "large_highlight_range": None}

        class Harness(NotesMixin):
            pass

        app = Harness()
        app.config = SimpleNamespace(font_size=11)

        captured: list[str] = []

        def fake_source_token_spans(code: str, _path: Path, **_kwargs) -> tuple[SyntaxSpan, ...]:
            captured.append(code)
            return (SyntaxSpan(0, min(5, len(code)), "#ff0000"),)

        with patch("writeonside_app.ui.notes.source_token_spans", fake_source_token_spans):
            app._apply_split_source_file_highlight(note, fake_text, Path("split.py"))

        self.assertEqual(1, len(captured))
        self.assertLess(captured[0].count("\n"), content.count("\n") // 10)
        self.assertIn(("source_code", "4900.0", "5120.end"), fake_text.added)


if __name__ == "__main__":
    unittest.main()
