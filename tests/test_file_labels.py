from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from writeonside_app.file_labels import (
    COLOR_TAG_PALETTE,
    colors_for_path,
    is_path_pinned,
    normalize_color_list,
    normalize_custom_color,
    relocate_file_labels,
    remove_file_labels_under,
    toggle_tag_mode,
)


class FileLabelTests(unittest.TestCase):
    def test_two_tag_toggles_represent_all_three_modes(self) -> None:
        self.assertEqual("both", toggle_tag_mode("text", "color"))
        self.assertEqual("color", toggle_tag_mode("both", "text"))
        self.assertEqual("both", toggle_tag_mode("color", "text"))
        self.assertEqual("text", toggle_tag_mode("both", "color"))

    def test_last_visible_tag_layer_cannot_be_disabled(self) -> None:
        self.assertEqual("text", toggle_tag_mode("text", "text"))
        self.assertEqual("color", toggle_tag_mode("color", "color"))

    def test_colors_are_limited_deduplicated_and_accept_one_custom_color(self) -> None:
        values = normalize_color_list(
            [COLOR_TAG_PALETTE[0], COLOR_TAG_PALETTE[0].lower(), "#FFFFFF", *COLOR_TAG_PALETTE[1:]]
        )
        self.assertEqual([COLOR_TAG_PALETTE[0], "#FFFFFF", COLOR_TAG_PALETTE[1]], values)

    def test_color_values_accept_preset_names_or_six_digit_hex(self) -> None:
        self.assertEqual("#12ABEF", normalize_custom_color("#12abef"))
        self.assertEqual(COLOR_TAG_PALETTE[0], normalize_custom_color("red"))
        self.assertEqual("", normalize_custom_color("#FFF"))

    def test_relocate_file_labels_moves_nested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            old = root / "Old"
            new = root / "New"
            note = old / "Nested" / "Note.md"
            colors, pins = relocate_file_labels(
                {str(note): [COLOR_TAG_PALETTE[2]]},
                [str(note)],
                {old: new},
            )
            expected = new / "Nested" / "Note.md"
            self.assertEqual((COLOR_TAG_PALETTE[2],), colors_for_path(colors, expected))
            self.assertTrue(is_path_pinned(pins, expected))

    def test_remove_file_labels_clears_a_deleted_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            removed = root / "Removed"
            deleted_note = removed / "Note.md"
            retained_note = root / "Keep.md"
            colors, pins = remove_file_labels_under(
                {
                    str(deleted_note): [COLOR_TAG_PALETTE[0]],
                    str(retained_note): [COLOR_TAG_PALETTE[1]],
                },
                [str(deleted_note), str(retained_note)],
                removed,
            )
            self.assertFalse(colors_for_path(colors, deleted_note))
            self.assertFalse(is_path_pinned(pins, deleted_note))
            self.assertEqual((COLOR_TAG_PALETTE[1],), colors_for_path(colors, retained_note))
            self.assertTrue(is_path_pinned(pins, retained_note))


if __name__ == "__main__":
    unittest.main()
