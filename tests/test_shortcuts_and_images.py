import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from PIL import Image

from writeonside_app.markdown import render_markdown
from writeonside_app.shortcuts import (
    COMMAND_SHORTCUTS,
    DEFAULT_COMMAND_SHORTCUTS,
    hotkey_to_tk_sequence,
    normalize_command_shortcuts,
    shortcut_conflicts,
)


class ShortcutTests(unittest.TestCase):
    def test_defaults_cover_every_command_without_conflicts(self):
        self.assertEqual(set(COMMAND_SHORTCUTS), set(DEFAULT_COMMAND_SHORTCUTS))
        self.assertEqual({}, shortcut_conflicts(DEFAULT_COMMAND_SHORTCUTS))
        for shortcut in DEFAULT_COMMAND_SHORTCUTS.values():
            self.assertIsNotNone(hotkey_to_tk_sequence(shortcut))

    def test_user_shortcuts_merge_with_defaults_and_allow_disabled_commands(self):
        merged = normalize_command_shortcuts({"bold": "alt+b", "image": ""})
        self.assertEqual("alt+b", merged["bold"])
        self.assertEqual("", merged["image"])
        self.assertEqual(DEFAULT_COMMAND_SHORTCUTS["save_note"], merged["save_note"])

    def test_conflicts_are_reported(self):
        conflicts = shortcut_conflicts({"bold": "ctrl+b", "bullet": "CTRL + B"})
        self.assertEqual({"ctrl+b": ["bold", "bullet"]}, conflicts)


class MarkdownImageTests(unittest.TestCase):
    def test_rendered_image_keeps_clickable_source_path(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                directory = Path(temp_dir)
                note = directory / "note.md"
                image_path = directory / "figure.png"
                Image.new("RGB", (32, 20), "#336699").save(image_path)
                widget = tk.Text(root, width=40, height=10)
                widget.pack()
                root.update_idletasks()
                render_markdown(widget, "![Figure](figure.png)", note)
                self.assertEqual(1, len(widget._clickable_images))
                self.assertEqual(str(image_path.resolve()), next(iter(widget._clickable_images.values())))
        finally:
            root.destroy()

    def test_html_font_colors_render_without_showing_html_tags(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            widget = tk.Text(root, width=50, height=10)
            widget.pack()
            root.update_idletasks()
            render_markdown(
                widget,
                '<span style="color: #ff0000">Red</span> '
                '<font color="blue">Blue</font> '
                '<span style="color: rgb(12, 34, 56)">RGB</span>',
                Path("note.md"),
            )
            self.assertEqual("Red Blue RGB", widget.get("1.0", "end-1c").strip())
            colors = {
                widget.tag_cget(tag, "foreground")
                for tag in widget.tag_names()
                if tag.startswith("html_color_")
            }
            self.assertEqual({"#ff0000", "blue", "#0c2238"}, colors)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
