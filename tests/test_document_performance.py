from __future__ import annotations

import unittest
from types import SimpleNamespace

from writeonside_app.document_performance import (
    DocumentMetrics,
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

    def test_large_set_editor_content_defers_outline_rebuild(self) -> None:
        class TextSpy:
            def delete(self, *_args) -> None:
                return None

            def insert(self, *_args) -> None:
                return None

            def edit_reset(self) -> None:
                return None

            def edit_modified(self, *_args) -> None:
                return None

            def config(self, **_kwargs) -> None:
                return None

            def get(self, *_args) -> str:
                return "content"

        class Harness(EditorMixin):
            def __init__(self) -> None:
                self.text = TextSpy()
                self.view_mode = "edit"
                self._showing_placeholder = False
                self._editor_image_editing_keys = set()
                self._editor_image_preview_state = None
                self._read_fragment_after = None
                self.scheduled = False
                self.rebuilt = False

            def _cancel_large_read_fragment(self) -> None:
                return None

            def _maybe_show_placeholder(self) -> None:
                return None

            def _schedule_outline_cache_rebuild(self, _content: str) -> None:
                self.scheduled = True

            def _rebuild_outline_cache(self, _content: str | None = None) -> None:
                self.rebuilt = True

            def _apply_live_render(self) -> None:
                return None

            def _schedule_editor_structure_refresh(self, **_kwargs) -> None:
                return None

        app = Harness()
        app._set_editor_content("x" * LARGE_DOCUMENT_CHAR_THRESHOLD)
        self.assertTrue(app.scheduled)
        self.assertFalse(app.rebuilt)

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

    def test_large_read_mode_uses_fragment_renderer_without_full_content(self) -> None:
        class Harness(EditorMixin):
            preview_path = None
            current_note_path = None
            rendered_anchor = 0

            def __init__(self) -> None:
                from pathlib import Path

                self.current_note_path = Path("large.md")
                self.read_text = object()

            def _editor_document_metrics(self) -> DocumentMetrics:
                return DocumentMetrics(2_000_000, 20_000)

            def _current_editor_source_line(self) -> int:
                return 250

            def _render_large_read_fragment(self, anchor_line: int, *, metrics=None) -> None:
                self.rendered_anchor = anchor_line

            def _get_editor_content(self) -> str:
                raise AssertionError("large read mode should not fetch full content")

        app = Harness()
        app._render_read_content()
        self.assertEqual(250, app.rendered_anchor)

    def test_large_read_scroll_schedules_fragment_render(self) -> None:
        class RootSpy:
            def __init__(self) -> None:
                self.after_delay = 0

            def after(self, delay: int, _callback) -> str:
                self.after_delay = delay
                return "after-id"

            def after_cancel(self, _after_id: str) -> None:
                return None

        class Harness(EditorMixin):
            def __init__(self) -> None:
                self.root = RootSpy()
                self._read_fragment_active = True
                self._read_fragment_after = None
                self._read_fragment_anchor_line = 1

            def _editor_document_metrics(self) -> DocumentMetrics:
                return DocumentMetrics(2_000_000, 20_000)

        app = Harness()
        self.assertEqual("break", app._scroll_large_read_fragment(80))
        self.assertEqual(81, app._read_fragment_anchor_line)
        self.assertEqual(80, app.root.after_delay)

    def test_large_read_page_keys_render_immediately(self) -> None:
        class Event:
            state = 0
            keysym = "Next"

        class Harness(EditorMixin):
            def __init__(self) -> None:
                self._read_fragment_active = True
                self._read_fragment_anchor_line = 1
                self.rendered_anchor = 0

            def _editor_document_metrics(self) -> DocumentMetrics:
                return DocumentMetrics(2_000_000, 20_000)

            def _render_large_read_fragment(self, anchor_line: int, *, metrics=None) -> None:
                self.rendered_anchor = anchor_line
                self._read_fragment_anchor_line = anchor_line

        app = Harness()
        self.assertEqual("break", app._read_text_key_filter(Event()))
        self.assertEqual(601, app.rendered_anchor)

    def test_type_completion_matches_english_words_case_insensitively(self) -> None:
        class Harness(EditorMixin):
            def _type_completion_source_text(self) -> str:
                return "The HERITABILITY estimate is stable."

        app = Harness()
        self.assertEqual("herITABILITY", app._find_type_completion_candidate("her"))

    def test_type_completion_continues_as_prefix_grows(self) -> None:
        class Harness(EditorMixin):
            pass

        app = Harness()
        app._type_completion_candidate = "herITABILITY"
        self.assertEqual("heriTABILITY", app._continued_type_completion_candidate("heri"))

    def test_type_completion_switches_when_prefix_disambiguates(self) -> None:
        class Harness(EditorMixin):
            def _type_completion_source_text(self) -> str:
                return "breed bread"

        app = Harness()
        app._type_completion_candidate = "breED"
        self.assertIsNone(app._continued_type_completion_candidate("brea"))
        self.assertEqual("bread", app._find_type_completion_candidate("brea"))

    def test_type_completion_requires_three_letter_prefix(self) -> None:
        class TextSpy:
            def index(self, index: str) -> str:
                return index

            def get(self, _start: str, _end: str) -> str:
                return "he"

        class Harness(EditorMixin):
            pass

        app = Harness()
        app.text = TextSpy()
        self.assertEqual("he", app._current_type_completion_prefix())
        self.assertLess(len(app._current_type_completion_prefix()), 3)

    def test_large_type_completion_uses_visible_fragment_only(self) -> None:
        class TextSpy:
            def count(self, *_args) -> tuple[str]:
                return ("2000000",)

            def index(self, index: str) -> str:
                if index == "end-1c":
                    return "20000.0"
                if index == "@0,0":
                    return "500.0"
                if index.startswith("@0,"):
                    return "520.0"
                return index

            def winfo_height(self) -> int:
                return 240

            def get(self, start: str, _end: str) -> str:
                if start == "400.0":
                    return "VISIBLEWORD hidden"
                raise AssertionError("large completion should only read the visible fragment")

        class Harness(EditorMixin):
            pass

        app = Harness()
        app.text = TextSpy()
        self.assertEqual("visIBLEWORD", app._find_type_completion_candidate("vis"))


if __name__ == "__main__":
    unittest.main()
