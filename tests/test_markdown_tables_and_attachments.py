from __future__ import annotations

import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from writeonside_app.markdown import _display_width, format_table_lines, parse_table_row, render_markdown


class MarkdownTableAndAttachmentTests(unittest.TestCase):
    def test_table_parser_preserves_escaped_and_code_span_pipes(self) -> None:
        self.assertEqual(
            ["Name | Alias", "`a|b`", r"C:\Files"],
            parse_table_row(r"| Name \| Alias | `a|b` | C:\Files |"),
        )

    def test_table_formatter_aligns_wide_characters_and_limits_width(self) -> None:
        lines = format_table_lines(
            [["名称", "Count", "Description"], ["示例", "12", "A very long description for this row"]],
            ["left", "right", "center"],
            max_width=42,
        )
        widths = {_display_width(line) for line, _tag in lines}
        self.assertEqual(1, len(widths))
        self.assertLessEqual(widths.pop(), 42)
        self.assertTrue(any("示例" in line for line, _tag in lines))

    def test_read_mode_registers_local_attachment_link(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                folder = Path(temp_dir)
                note = folder / "Note.md"
                attachment = folder / "Attachments" / "预算 (2026).xlsx"
                attachment.parent.mkdir()
                attachment.write_bytes(b"xlsx")
                widget = tk.Text(root, width=50, height=8)
                widget.pack()
                root.update_idletasks()

                render_markdown(widget, "[Workbook](Attachments/%E9%A2%84%E7%AE%97%20%282026%29.xlsx)", note)

                self.assertEqual([str(attachment.resolve())], list(widget._attachment_links.values()))
                self.assertIn("Workbook", widget.get("1.0", "end-1c"))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
