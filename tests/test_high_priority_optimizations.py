import unittest

from writeonside_app.live_highlight import (
    MD_EDITOR_TAGS,
    apply_live_highlight_plan,
    code_block_active_before,
    plan_live_highlight,
)
from writeonside_app.theme import ActiveTheme, ThemePalette, get_theme


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
        plan = plan_live_highlight("- [ ] open task\n- [x] done task")
        tags_by_line = {line_tag.line: line_tag.tag for line_tag in plan.line_tags}
        self.assertEqual("md_task", tags_by_line[1])
        self.assertEqual("md_task_done", tags_by_line[2])

    def test_color_spans_are_offset_to_their_line_position(self) -> None:
        content = 'Thermal stress (<span style="color: #3b82f6">cold</span> and <span style="color: #e05252">heat</span>)'
        plan = plan_live_highlight(content)
        spans = {(span.color, span.start, span.end) for span in plan.color_spans}
        self.assertIn(("#3b82f6", content.index("cold"), content.index("cold") + len("cold")), spans)
        self.assertIn(("#e05252", content.index("heat"), content.index("heat") + len("heat")), spans)

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

            def tag_raise(self, tag: str) -> None:
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
