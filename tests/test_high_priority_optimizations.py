import unittest
import tkinter as tk

from writeonside_app.live_highlight import (
    MD_EDITOR_TAGS,
    apply_live_highlight_plan,
    code_block_active_before,
    plan_live_highlight,
)
from writeonside_app.theme import ActiveTheme, ThemePalette, get_theme
from writeonside_app.ui.editor import EditorMixin
from writeonside_app.ui.editor_structure import EditorStructureMixin


class LiveHighlightTests(unittest.TestCase):
    def test_code_block_state_tracks_fences(self) -> None:
        lines = ["# Title", "```", "code", "```", "text"]
        self.assertFalse(code_block_active_before(lines, 2))
        self.assertTrue(code_block_active_before(lines, 3))
        self.assertFalse(code_block_active_before(lines, 5))

    def test_partial_plan_limits_line_range(self) -> None:
        body = "\n".join(f"line {index}" for index in range(600))
        content = f"---\ntitle: Demo\ntags: []\ncreated: 2024-01-01\n---\n{body}"
        plan = plan_live_highlight(content, focus_line=300)
        self.assertTrue(plan.partial)
        self.assertGreaterEqual(plan.line_range[0], 240)
        self.assertLessEqual(plan.line_range[1], 360)

    def test_large_file_uses_simplified_mode(self) -> None:
        content = "\n".join(f"**bold {index}**" for index in range(2100))
        plan = plan_live_highlight(content, focus_line=1000)
        self.assertTrue(plan.simplified)
        self.assertEqual((), plan.spans)

    def test_task_lines_distinguish_checked_and_unchecked(self) -> None:
        plan = plan_live_highlight("- [ ] open task\n- [x] done task\n- [*] marked task\n- [*]\n-- [ ] loose task")
        tags_by_line = {line_tag.line: line_tag.tag for line_tag in plan.line_tags}
        self.assertEqual("md_task", tags_by_line[1])
        self.assertEqual("md_task_done", tags_by_line[2])
        self.assertEqual("md_task_done", tags_by_line[3])
        self.assertEqual("md_task_done", tags_by_line[4])
        self.assertEqual("md_task", tags_by_line[5])

    def test_color_spans_are_offset_to_their_line_position(self) -> None:
        content = 'Thermal stress (<span style="color: #3b82f6">cold</span> and <span style="color: #e05252">heat</span>)'
        plan = plan_live_highlight(content)
        spans = {(span.color, span.start, span.end) for span in plan.color_spans}
        self.assertIn(("#3b82f6", content.index("cold"), content.index("cold") + len("cold")), spans)
        self.assertIn(("#e05252", content.index("heat"), content.index("heat") + len("heat")), spans)

    def test_live_preview_marker_spans_keep_inline_source_on_active_line(self) -> None:
        content = "\n".join(
            [
                "**Bold** and [Site](https://example.com)",
                "- [*] marked task",
                '<span style="color: #3b82f6">blue</span>',
            ]
        )
        plan = plan_live_highlight(content, focus_line=2)
        markers = {(span.line, span.start, span.end) for span in plan.marker_spans}
        replacements = {(span.line, span.start, span.text) for span in plan.replacements}

        self.assertIn((1, 0, 2), markers)
        self.assertIn((1, 6, 8), markers)
        self.assertIn((1, 13, 14), markers)
        self.assertIn((1, 18, 40), markers)
        self.assertFalse(any(line == 2 for line, _start, _end in markers))
        self.assertFalse(any(line == 2 for line, _start, _text in replacements))
        self.assertTrue(any(line == 3 and start == 0 for line, start, _end in markers))
        self.assertTrue(any(line == 3 and end == len('<span style="color: #3b82f6">blue</span>') for line, _start, end in markers))

    def test_active_task_line_keeps_source_prefix_for_editing(self) -> None:
        plan = plan_live_highlight("- [ ] Copy of all pages of passport", focus_line=1)

        markers = {(span.line, span.start, span.end) for span in plan.marker_spans}
        replacements = {(span.line, span.start, span.text, span.tag) for span in plan.replacements}
        line_tags = {(tag.line, tag.tag) for tag in plan.line_tags}

        self.assertFalse(markers)
        self.assertFalse(replacements)
        self.assertNotIn((1, "md_task"), line_tags)

    def test_live_preview_marker_spans_cover_list_prefixes(self) -> None:
        content = "- bullet\n1. numbered\n> quote\n## Heading\n- [ ] task\n- [x] done"
        plan = plan_live_highlight(content, focus_line=4)
        markers = {(span.line, span.start, span.end) for span in plan.marker_spans}
        replacements = {(span.line, span.start, span.text, span.tag) for span in plan.replacements}

        self.assertIn((1, 0, 2), markers)
        self.assertIn((3, 0, 2), markers)
        self.assertFalse(any(line == 4 for line, _start, _end in markers))
        self.assertIn((1, 0, "• ", "md_list"), replacements)
        self.assertIn((5, 0, "☐ ", "md_list"), replacements)
        self.assertIn((6, 0, "☑ ", "md_task_done"), replacements)

    def test_live_preview_leaves_standalone_media_embeds_to_editor_preview(self) -> None:
        content = "\n".join(
            [
                "![Figure](figure.png)",
                "![[paper.pdf]]",
                "See ![Figure](figure.png) inline",
            ]
        )
        plan = plan_live_highlight(content, focus_line=99)
        markers = {(span.line, span.start, span.end) for span in plan.marker_spans}

        self.assertFalse(any(line == 1 for line, _start, _end in markers))
        self.assertFalse(any(line == 2 for line, _start, _end in markers))
        self.assertTrue(any(line == 3 for line, _start, _end in markers))

    def test_full_color_refresh_clears_previous_dynamic_tags(self) -> None:
        class FakeText:
            def __init__(self) -> None:
                self.removed: list[tuple[str, str, str]] = []
                self.added: list[tuple[str, str, str]] = []
                self.raised: list[str] = []

            def tag_remove(self, tag: str, start: str, end: str) -> None:
                self.removed.append((tag, start, end))

            def tag_add(self, tag: str, start: str, end: str) -> None:
                self.added.append((tag, start, end))

            def tag_raise(self, tag: str, above: str | None = None) -> None:
                self.raised.append(tag)

        first = plan_live_highlight('<span style="color: red">red</span>')
        second = plan_live_highlight('<span style="color: blue">blue</span>')
        widget = FakeText()
        color_tags: set[str] = set()
        apply_live_highlight_plan(
            widget,
            first,
            clear_tags=MD_EDITOR_TAGS,
            clear_line_range=None,
            validate_color=lambda _color: True,
            configure_color_tag=lambda _tag, _color: None,
            editor_color_tags=color_tags,
        )
        old_tags = set(color_tags)
        apply_live_highlight_plan(
            widget,
            second,
            clear_tags=MD_EDITOR_TAGS,
            clear_line_range=None,
            validate_color=lambda _color: True,
            configure_color_tag=lambda _tag, _color: None,
            editor_color_tags=color_tags,
        )
        removed_tags = {tag for tag, _start, _end in widget.removed}
        self.assertTrue(old_tags <= removed_tags)
        self.assertTrue(color_tags.isdisjoint(old_tags))

    def test_editor_color_tags_match_read_mode_font_behavior(self) -> None:
        class FakeText:
            def __init__(self) -> None:
                self.configured: dict[str, object] = {}

            def tag_configure(self, tag: str, **options) -> None:
                self.configured = {"tag": tag, **options}

            def tag_raise(self, tag: str, above: str | None = None) -> None:
                pass

        class Harness(EditorMixin):
            text = FakeText()

        Harness()._configure_editor_color_tag("md_color_test", "#3b82f6")

        self.assertEqual("#3b82f6", Harness.text.configured["foreground"])
        self.assertNotIn("font", Harness.text.configured)

    def test_live_preview_replacements_do_not_enter_undo_stack(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            widget = tk.Text(root, undo=True, width=40, height=5)
            widget.pack()
            widget.tag_configure("md_live_marker_elide", elide=True)
            widget.insert("1.0", "- [ ] task")
            widget.edit_reset()
            widget.insert("end-1c", "!")
            widget.edit_separator()
            root.update_idletasks()

            plan = plan_live_highlight(widget.get("1.0", "end-1c"), focus_line=99)
            before_modified = bool(widget.edit_modified())
            apply_live_highlight_plan(
                widget,
                plan,
                clear_tags=MD_EDITOR_TAGS,
                clear_line_range=None,
                validate_color=lambda _color: True,
                configure_color_tag=lambda tag, color: widget.tag_configure(tag, foreground=color),
                editor_color_tags=set(),
            )
            labels = getattr(widget, "_live_preview_replacements", [])
            self.assertTrue(labels)
            marker = labels[0]["label"]
            self.assertEqual("Canvas", marker.winfo_class())
            self.assertEqual({}, marker.place_info())
            self.assertTrue(labels[0].get("mark"))
            self.assertTrue(widget.window_cget(labels[0]["mark"], "window"))
            self.assertEqual(before_modified, bool(widget.edit_modified()))
            widget.edit_undo()

            self.assertEqual("- [ ] task", widget.get("1.0", "end-1c"))
        finally:
            root.destroy()

    def test_live_preview_skips_embedded_markers_when_text_widget_cannot_host_them(self) -> None:
        class FakeText:
            def __init__(self) -> None:
                self.removed: list[tuple[str, str, str]] = []
                self.added: list[tuple[str, str, str]] = []
                self._live_preview_replacements = []
                self.undo = True

            def cget(self, key: str):
                if key == "undo":
                    return self.undo
                return ""

            def configure(self, **options) -> None:
                if "undo" in options:
                    self.undo = options["undo"]

            def tag_remove(self, tag: str, start: str, end: str) -> None:
                self.removed.append((tag, start, end))

            def tag_add(self, tag: str, start: str, end: str) -> None:
                self.added.append((tag, start, end))

        widget = FakeText()
        plan = plan_live_highlight("- [ ] offscreen", focus_line=99)

        apply_live_highlight_plan(
            widget,
            plan,
            clear_tags=MD_EDITOR_TAGS,
            clear_line_range=None,
            validate_color=lambda _color: True,
            configure_color_tag=lambda _tag, _color: None,
            editor_color_tags=set(),
        )

        self.assertEqual([], widget._live_preview_replacements)
        self.assertTrue(widget.undo)

    def test_editor_scroll_does_not_rerender_inline_live_preview_windows(self) -> None:
        class Text:
            _live_preview_replacements = [{"label": object()}]

        class Harness(EditorStructureMixin):
            def __init__(self) -> None:
                self.text = Text()
                self.structure_refreshes = 0
                self.live_refreshes = 0

            def _schedule_editor_structure_refresh(self) -> None:
                self.structure_refreshes += 1

            def _schedule_live_render(self) -> None:
                self.live_refreshes += 1

            def _should_refresh_live_render_on_scroll(self) -> bool:
                return False

        app = Harness()
        app._on_editor_scroll()

        self.assertEqual(1, app.structure_refreshes)
        self.assertEqual(0, app.live_refreshes)

    def test_live_preview_task_symbol_aligns_with_text_line(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        try:
            widget = tk.Text(root, font=("Segoe UI", 12), width=40, height=5)
            widget.pack()
            widget.tag_configure("md_task", lmargin1=22, lmargin2=22)
            widget.tag_configure("md_live_marker_elide", elide=True)
            widget.insert("1.0", "- [ ] task")
            root.update()
            before_line_info = widget.dlineinfo("1.0")
            self.assertIsNotNone(before_line_info)
            assert before_line_info is not None
            before_line_height = before_line_info[3]

            plan = plan_live_highlight(widget.get("1.0", "end-1c"), focus_line=99)
            apply_live_highlight_plan(
                widget,
                plan,
                clear_tags=MD_EDITOR_TAGS,
                clear_line_range=None,
                validate_color=lambda _color: True,
                configure_color_tag=lambda tag, color: widget.tag_configure(tag, foreground=color),
                editor_color_tags=set(),
            )
            root.update()

            replacement = getattr(widget, "_live_preview_replacements", [])[0]
            marker = replacement["label"]
            mark = replacement["mark"]
            marker_bbox = widget.bbox(mark)
            line_info = widget.dlineinfo("1.0")
            self.assertEqual({}, marker.place_info())
            self.assertTrue(widget.window_cget(mark, "window"))
            self.assertIsNotNone(marker_bbox)
            self.assertIsNotNone(line_info)
            assert marker_bbox is not None
            assert line_info is not None
            self.assertEqual(before_line_height, line_info[3])
            self.assertLessEqual(abs(marker_bbox[1] - line_info[1]), 2)
        finally:
            root.destroy()


class ThemePaletteTests(unittest.TestCase):
    def test_palette_round_trip(self) -> None:
        palette = ThemePalette.from_dict(get_theme("nord"))
        values = palette.as_dict()
        self.assertEqual("#2e3440", values["BG"])
        self.assertEqual(set(values), set(palette.as_dict()))

    def test_icon_themes_have_complete_palettes(self) -> None:
        dark = ThemePalette.from_dict(get_theme("icon_dark"))
        light = ThemePalette.from_dict(get_theme("icon_light"))
        self.assertEqual("#b45cff", dark.ACCENT)
        self.assertEqual("#df7134", light.ACCENT)

    def test_named_theme_updates_are_available(self) -> None:
        mid_night = get_theme("mid_night")
        black_gold = ThemePalette.from_dict(get_theme("black_gold"))
        morandi = ThemePalette.from_dict(get_theme("morandi"))

        self.assertEqual("Mid Night", mid_night["NAME"])
        self.assertEqual("#cfb991", black_gold.ACCENT)
        self.assertEqual("#8fa6a0", morandi.ACCENT)

    def test_active_theme_updates_current_palette(self) -> None:
        active = ActiveTheme()
        active.set("dracula")
        self.assertEqual("#bd93f9", active.palette.ACCENT)
        active.set("unknown-theme")
        self.assertEqual(active.palette.BG, ThemePalette.from_dict(get_theme("graphite")).BG)


if __name__ == "__main__":
    unittest.main()
