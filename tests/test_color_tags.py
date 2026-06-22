from __future__ import annotations

import unittest

from writeonside_app.file_labels import (
    COLOR_TAG_PALETTE,
    color_tag_storage_name,
    normalize_color_list,
    normalize_custom_color,
)
from writeonside_app.frontmatter import parse_front_matter, set_writeonside_properties, split_front_matter
from writeonside_app.i18n import set_language
from writeonside_app.ui.explorer import ExplorerMixin


class ColorTagTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_language("en")

    def test_color_names_are_normalized_across_languages_and_case(self) -> None:
        self.assertEqual("#5175B8", normalize_custom_color("BLUE"))
        self.assertEqual("#5175B8", normalize_custom_color("blue"))
        self.assertEqual("#5175B8", normalize_custom_color("蓝色"))
        self.assertEqual("#5175B8", normalize_custom_color("Bleu"))
        self.assertEqual("#DE2F24", normalize_custom_color("红"))
        self.assertEqual("#7BC5D4", normalize_custom_color("청록색"))

    def test_color_list_accepts_names_and_hex_values(self) -> None:
        self.assertEqual(
            ["#5175B8", "#DE2F24", "#7BC5D4"],
            normalize_color_list(["蓝色", "#DE2F24", "cyan"]),
        )

    def test_frontmatter_reads_names_and_writes_stable_names(self) -> None:
        content = (
            "---\n"
            "title: Note\n"
            "writeonside_colors: [蓝色, BLUE, red]\n"
            "writeonside_pinned: false\n"
            "---\n"
            "Body"
        )
        metadata = parse_front_matter(content, "Note")
        self.assertEqual(("#5175B8", "#DE2F24"), metadata.color_tags)

        updated = set_writeonside_properties(content, color_tags=["#DE2F24", "#5175B8"], pinned=True)
        header, _body = split_front_matter(updated)
        self.assertIn('writeonside_colors: ["red", "blue"]', header)
        self.assertNotIn("#DE2F24", header)

    def test_color_tag_storage_name_keeps_custom_colors_as_hex(self) -> None:
        self.assertEqual("blue", color_tag_storage_name(COLOR_TAG_PALETTE[4]))
        self.assertEqual("#123456", color_tag_storage_name("#123456"))

    def test_color_tag_labels_are_localized(self) -> None:
        app = ExplorerMixin()
        set_language("zh")
        self.assertEqual("蓝色", app._color_tag_label("#5175B8"))
        set_language("en")
        self.assertEqual("Blue", app._color_tag_label("#5175B8"))
        self.assertEqual("#123456", app._color_tag_label("#123456"))


if __name__ == "__main__":
    unittest.main()
