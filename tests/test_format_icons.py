from __future__ import annotations

import unittest

from writeonside_app.format_icons import FORMAT_MDL2_ICONS, format_action_glyph


class FormatIconTests(unittest.TestCase):
    def test_mdl2_icons_are_defined_for_overflow_menu_items(self) -> None:
        for key in (
            "quote",
            "image",
            "table",
            "task",
            "divider",
            "attachment",
            "paste_clipboard_image",
            "clear_formatting",
        ):
            self.assertIn(key, FORMAT_MDL2_ICONS)
            self.assertTrue(FORMAT_MDL2_ICONS[key])

    def test_preserved_items_keep_fallback_glyph(self) -> None:
        self.assertEqual("🔗", format_action_glyph("link", "🔗"))
        self.assertEqual("•", format_action_glyph("bullet", "•"))


if __name__ == "__main__":
    unittest.main()
