from __future__ import annotations

import unittest
from types import SimpleNamespace

from writeonside_app.document_performance import (
    LARGE_DOCUMENT_CHAR_THRESHOLD,
    LARGE_DOCUMENT_LINE_THRESHOLD,
    READ_MODE_RENDER_BYTE_LIMIT,
    limit_read_mode_content,
    metrics_for_content,
)
from writeonside_app.live_highlight import plan_live_highlight_fragment
from writeonside_app.ui.editor import EditorMixin


class DocumentPerformanceTests(unittest.TestCase):
    def test_large_document_detected_by_characters_or_lines(self) -> None:
        by_characters = metrics_for_content("x" * LARGE_DOCUMENT_CHAR_THRESHOLD)
        by_lines = metrics_for_content("\n" * (LARGE_DOCUMENT_LINE_THRESHOLD - 1))
        self.assertTrue(by_characters.is_large)
        self.assertTrue(by_lines.is_large)

    def test_read_mode_limit_stops_at_nearby_line_boundary(self) -> None:
        content = ("line content\n" * ((READ_MODE_RENDER_BYTE_LIMIT // 13) + 10))
        limited, was_limited = limit_read_mode_content(content)
        self.assertTrue(was_limited)
        self.assertLessEqual(len(limited.encode("utf-8")), READ_MODE_RENDER_BYTE_LIMIT)
        self.assertTrue(limited.endswith("content"))

    def test_read_mode_limit_counts_utf8_bytes(self) -> None:
        content = "笔记" * READ_MODE_RENDER_BYTE_LIMIT
        limited, was_limited = limit_read_mode_content(content)
        self.assertTrue(was_limited)
        self.assertLessEqual(len(limited.encode("utf-8")), READ_MODE_RENDER_BYTE_LIMIT)

    def test_fragment_highlight_uses_absolute_lines(self) -> None:
        plan = plan_live_highlight_fragment(
            "## Heading\n- [x] complete\nplain",
            start_line=500,
            simplified=True,
        )
        self.assertEqual((500, 502), plan.line_range)
        self.assertEqual([500, 501], [item.line for item in plan.line_tags])
        self.assertTrue(plan.partial)

    def test_limited_read_mode_find_count_uses_full_editor_content(self) -> None:
        class Harness(EditorMixin):
            preview_path = None
            view_mode = "read"
            _read_content_limited = True
            find_case_sensitive_var = SimpleNamespace(get=lambda: False)

            def _get_editor_content(self) -> str:
                return "Done\nhidden done\nDONE\n"

        self.assertEqual(3, Harness()._full_read_mode_find_count("done"))

    def test_unlimited_read_mode_find_count_does_not_override_rendered_matches(self) -> None:
        class Harness(EditorMixin):
            preview_path = None
            view_mode = "read"
            _read_content_limited = False
            find_case_sensitive_var = SimpleNamespace(get=lambda: False)

            def _get_editor_content(self) -> str:
                return "Done\nhidden done\n"

        self.assertIsNone(Harness()._full_read_mode_find_count("done"))

    def test_outline_cache_tracks_sections_code_ranges_and_parent_stack(self) -> None:
        editor = EditorMixin()
        editor._rebuild_outline_cache(
            "# One\ntext\n## Child\n```python\n# not a heading\n```\n# Two\n"
        )
        headings = editor._parse_outline()
        self.assertEqual(["One", "Child", "Two"], [item["title"] for item in headings])
        self.assertEqual(6, headings[0]["end_line"])
        self.assertEqual((True, "python"), editor._large_document_code_context(5))
        self.assertEqual(
            ["One", "Child"],
            [item["title"] for item in editor._cached_active_heading_stack(4)],
        )

    def test_outline_cache_keeps_more_than_eighty_headings(self) -> None:
        editor = EditorMixin()
        editor._rebuild_outline_cache("\n".join(f"## Heading {index}" for index in range(120)))
        outline = editor._parse_outline()
        self.assertEqual(120, len(outline))
        self.assertEqual("Heading 119", outline[-1]["title"])

    def test_limited_read_outline_jump_uses_source_line_without_rendered_search(self) -> None:
        class Harness(EditorMixin):
            view_mode = "read"
            _read_content_limited = True
            jumped_line = 0
            searched = False

            def _close_outline_popup(self) -> None:
                return None

            def _jump_to_outline_source_line(self, line_no: int) -> None:
                self.jumped_line = line_no

            def _find_rendered_heading_index(self, _line_no: int, _title: str) -> str | None:
                self.searched = True
                return "1.0"

        app = Harness()
        app._jump_to_outline(500, "Heading")
        self.assertEqual(500, app.jumped_line)
        self.assertFalse(app.searched)

    def test_read_markdown_outline_jump_uses_source_line_without_rendered_search(self) -> None:
        class Harness(EditorMixin):
            view_mode = "read"
            _read_content_limited = False
            jumped_line = 0
            searched = False

            def __init__(self) -> None:
                from pathlib import Path

                self.current_note_path = Path("large.md")

            def _close_outline_popup(self) -> None:
                return None

            def _jump_to_outline_source_line(self, line_no: int) -> None:
                self.jumped_line = line_no

            def _find_rendered_heading_index(self, _line_no: int, _title: str) -> str | None:
                self.searched = True
                return "1.0"

        app = Harness()
        app._jump_to_outline(500, "Heading")
        self.assertEqual(500, app.jumped_line)
        self.assertFalse(app.searched)

    def test_fast_outline_jump_avoids_text_see_for_large_editor_document(self) -> None:
        class TextSpy:
            def __init__(self) -> None:
                self.see_called = False
                self.moved_to: float | None = None

            def tag_remove(self, *_args) -> None:
                return None

            def tag_configure(self, *_args, **_kwargs) -> None:
                return None

            def tag_add(self, *_args) -> None:
                return None

            def mark_set(self, *_args) -> None:
                return None

            def see(self, *_args) -> None:
                self.see_called = True

            def focus_set(self) -> None:
                return None

            def yview_moveto(self, ratio: float) -> None:
                self.moved_to = ratio

        class RootSpy:
            def after(self, _delay: int, _callback) -> str:
                return "after-id"

        class Harness(EditorMixin):
            def __init__(self) -> None:
                self.text = TextSpy()
                self.root = RootSpy()
                self.view_mode = "edit"
                self._live_render_after = None

            def _editor_document_metrics(self):
                from writeonside_app.document_performance import DocumentMetrics

                return DocumentMetrics(2_000_000, 20_000)

            def _apply_live_render(self) -> None:
                return None

        app = Harness()
        app._jump_to_editor_source_line(10_000, fast=True)
        self.assertFalse(app.text.see_called)
        self.assertIsNotNone(app.text.moved_to)


if __name__ == "__main__":
    unittest.main()
