from __future__ import annotations

import unittest

from writeonside_app.theme import (
    CUSTOM_THEME_IDS,
    MAX_CUSTOM_THEMES,
    THEMES,
    apply_custom_themes,
    clear_custom_themes,
    normalize_custom_themes,
    normalize_hex_color,
    normalize_palette,
)


class CustomThemeTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_custom_themes()

    def tearDown(self) -> None:
        clear_custom_themes()

    def test_normalize_hex_color(self) -> None:
        self.assertEqual("#AABBCC", normalize_hex_color("#aabbcc"))
        self.assertEqual("#AABBCC", normalize_hex_color("#abc"))
        self.assertEqual("", normalize_hex_color("not-a-color"))

    def test_normalize_palette_fills_missing_keys(self) -> None:
        palette = normalize_palette({"BG": "#111111"})
        self.assertEqual("#111111", palette["BG"])
        self.assertTrue(palette["TEXT"].startswith("#"))

    def test_apply_custom_themes_registers_up_to_two(self) -> None:
        entries = apply_custom_themes(
            [
                {"id": "custom_1", "name": "One", "palette": {"BG": "#101010", "TEXT": "#EEEEEE"}},
                {"id": "custom_2", "name": "Two", "palette": {"BG": "#202020", "TEXT": "#DDDDDD"}},
                {"id": "custom_1", "name": "Overflow", "palette": {"BG": "#303030"}},
            ]
        )
        self.assertEqual(2, len(entries))
        self.assertIn("custom_1", THEMES)
        self.assertIn("custom_2", THEMES)
        self.assertEqual("One", THEMES["custom_1"]["NAME"])
        self.assertEqual("#101010", THEMES["custom_1"]["BG"])

    def test_normalize_custom_themes_rejects_invalid_ids(self) -> None:
        normalized = normalize_custom_themes(
            [{"id": "custom_9", "name": "Bad", "palette": {"BG": "#111111"}}]
        )
        self.assertEqual([], normalized)

    def test_max_custom_themes_constant_matches_slots(self) -> None:
        self.assertEqual(MAX_CUSTOM_THEMES, len(CUSTOM_THEME_IDS))


if __name__ == "__main__":
    unittest.main()
