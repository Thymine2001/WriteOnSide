import unittest

from writeonside_app.live_highlight import (
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


class ThemePaletteTests(unittest.TestCase):
    def test_palette_round_trip(self) -> None:
        palette = ThemePalette.from_dict(get_theme("nord"))
        values = palette.as_dict()
        self.assertEqual("#2e3440", values["BG"])
        self.assertEqual(set(values), set(palette.as_dict()))

    def test_active_theme_updates_current_palette(self) -> None:
        active = ActiveTheme()
        active.set("dracula")
        self.assertEqual("#bd93f9", active.palette.ACCENT)
        active.set("unknown-theme")
        self.assertEqual(active.palette.BG, ThemePalette.from_dict(get_theme("graphite")).BG)


if __name__ == "__main__":
    unittest.main()
