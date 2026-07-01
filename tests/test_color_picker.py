from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from writeonside_app.color_picker_store import (
    append_color_pick,
    color_picker_day_file,
    format_pick_line,
    parse_pick_lines,
)


class ColorPickerStoreTests(unittest.TestCase):
    def test_format_pick_line_uses_colored_a(self) -> None:
        line = format_pick_line("#AABBCC", (170, 187, 204), 100, 200, when=datetime(2025, 6, 30, 14, 30, 25))
        self.assertIn('<span style="color: #aabbcc">A</span>', line)
        self.assertIn("`#AABBCC`", line)
        self.assertIn("(100, 200)", line)

    def test_append_color_pick_writes_daily_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            path = append_color_pick(root, "#112233", (17, 34, 51), 10, 20)
            expected = color_picker_day_file(root, date.today())
            self.assertEqual(expected, path)
            self.assertTrue(path.exists())
            content = path.read_text(encoding="utf-8")
            self.assertIn("# Color Picker", content)
            self.assertIn('<span style="color: #112233">A</span>', content)

    def test_parse_pick_lines(self) -> None:
        content = (
            "# title\n\n"
            '- `12:00:00` — <span style="color: #ff0000">A</span> `#FF0000` · rgb(255, 0, 0) · (1, 2)\n'
        )
        picks = parse_pick_lines(content)
        self.assertEqual(1, len(picks))
        self.assertEqual("#FF0000", picks[0]["hex"])


if __name__ == "__main__":
    unittest.main()
