from __future__ import annotations

import unittest
from types import SimpleNamespace

from writeonside_app.ui.editor_structure import (
    EditorStructureMixin,
    body_display_line_number,
    frontmatter_prefix_line_count,
    line_number_center_y,
)


class CanvasSpy:
    def __init__(self) -> None:
        self.width = 52

    def winfo_width(self) -> int:
        return self.width

    def configure(self, **kwargs) -> None:
        if "width" in kwargs:
            self.width = int(kwargs["width"])


class TextSpy:
    line_y: int | None = 0

    def index(self, index: str) -> str:
        if index == "end-1c":
            return "515872.0"
        if index == "@0,0":
            return "1.0"
        return index

    def dlineinfo(self, _index: str):
        if self.line_y is None:
            return None
        return (0, self.line_y, 100, 20, 15)


class EditorStructureTests(unittest.TestCase):
    def test_frontmatter_prefix_lines_are_excluded_from_display_numbers(self) -> None:
        content = "---\ntitle: Example\ncreated: 2026-06-29\n---\n# Body\n"
        prefix_lines = frontmatter_prefix_line_count(content)

        self.assertEqual(4, prefix_lines)
        self.assertIsNone(body_display_line_number(1, prefix_lines))
        self.assertIsNone(body_display_line_number(4, prefix_lines))
        self.assertEqual(1, body_display_line_number(5, prefix_lines))
        self.assertEqual(2, body_display_line_number(6, prefix_lines))

    def test_line_number_uses_visible_line_center(self) -> None:
        self.assertEqual(30, line_number_center_y((0, 20, 100, 20, 15)))
        self.assertEqual(21, line_number_center_y((0, 20, 100, 1, 1)))

    def test_line_number_aligns_with_first_wrapped_display_line(self) -> None:
        wrapped = line_number_center_y((0, 20, 100, 40, 15), single_line_height=20)
        single = line_number_center_y((0, 20, 100, 20, 15), single_line_height=20)

        self.assertEqual(30, wrapped)
        self.assertEqual(30, single)

    def test_line_number_gutter_expands_for_large_line_counts(self) -> None:
        app = EditorStructureMixin()
        app.line_number_canvas = CanvasSpy()
        app.text = TextSpy()
        app.config = SimpleNamespace(font_size=11)

        app._fit_line_number_gutter()

        self.assertGreater(app.line_number_canvas.width, 52)

    def test_sticky_heading_hidden_while_heading_line_is_visible(self) -> None:
        app = EditorStructureMixin()
        app.text = TextSpy()
        app.text.line_y = 0
        app._is_markdown_document = lambda: True
        app._cached_active_heading_stack = lambda _line: [{"level": 1, "title": "Title", "line": 1}]

        self.assertEqual([], app._sticky_heading_stack())

    def test_sticky_heading_shows_after_heading_scrolls_above_view(self) -> None:
        app = EditorStructureMixin()
        app.text = TextSpy()
        app.text.line_y = -12
        app._is_markdown_document = lambda: True
        app._cached_active_heading_stack = lambda _line: [{"level": 1, "title": "Title", "line": 1}]

        self.assertEqual([{"level": 1, "title": "Title", "line": 1}], app._sticky_heading_stack())


if __name__ == "__main__":
    unittest.main()
