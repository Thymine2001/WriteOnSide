import tempfile
import unittest
from pathlib import Path

from PIL import Image

from writeonside_app.editor_images import plan_editor_image_blocks


class EditorImageBlockTests(unittest.TestCase):
    def test_finds_markdown_image_on_its_own_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            image_path = directory / "figure.png"
            Image.new("RGB", (24, 16), "#224466").save(image_path)
            content = "Intro\n![Figure](figure.png)\nTail"
            blocks = plan_editor_image_blocks(content, directory / "note.md")
            self.assertEqual(1, len(blocks))
            block = blocks[0]
            self.assertEqual(2, block.line)
            self.assertEqual("2.0", block.start)
            self.assertEqual("![Figure](figure.png)", block.markdown)
            self.assertEqual(image_path.resolve(), block.image_path)

    def test_ignores_inline_image_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            image_path = directory / "figure.png"
            Image.new("RGB", (24, 16), "#224466").save(image_path)
            content = "See ![Figure](figure.png) here"
            self.assertEqual((), plan_editor_image_blocks(content, directory / "note.md"))

    def test_finds_wiki_embed_image_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            image_path = directory / "photo.jpg"
            Image.new("RGB", (24, 16), "#884422").save(image_path, format="JPEG")
            content = "![[photo.jpg]]"
            blocks = plan_editor_image_blocks(content, directory / "note.md")
            self.assertEqual(1, len(blocks))
            self.assertEqual("![[photo.jpg]]", blocks[0].markdown)

    def test_respects_leading_whitespace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            image_path = directory / "figure.png"
            Image.new("RGB", (24, 16), "#224466").save(image_path)
            content = "  ![Figure](figure.png)"
            blocks = plan_editor_image_blocks(content, directory / "note.md")
            self.assertEqual("1.2", blocks[0].start)
            self.assertEqual("1.23", blocks[0].end)


if __name__ == "__main__":
    unittest.main()
