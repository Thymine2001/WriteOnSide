from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
