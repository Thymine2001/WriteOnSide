from __future__ import annotations

import unittest
from types import SimpleNamespace

from writeonside_app.ui.editor_structure import EditorStructureMixin


class CanvasSpy:
    def __init__(self) -> None:
        self.width = 52

    def winfo_width(self) -> int:
        return self.width

    def configure(self, **kwargs) -> None:
        if "width" in kwargs:
            self.width = int(kwargs["width"])


class TextSpy:
    def index(self, index: str) -> str:
        if index == "end-1c":
            return "515872.0"
        return index


class EditorStructureTests(unittest.TestCase):
    def test_line_number_gutter_expands_for_large_line_counts(self) -> None:
        app = EditorStructureMixin()
        app.line_number_canvas = CanvasSpy()
        app.text = TextSpy()
        app.config = SimpleNamespace(font_size=11)

        app._fit_line_number_gutter()

        self.assertGreater(app.line_number_canvas.width, 52)


if __name__ == "__main__":
    unittest.main()
