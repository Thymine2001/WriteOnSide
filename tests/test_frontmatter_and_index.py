from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from writeonside_app.frontmatter import ensure_front_matter, note_template, parse_front_matter, split_front_matter
from writeonside_app.note_index import build_note_index, filter_workspace_files


class FrontMatterTests(unittest.TestCase):
    def test_inline_tags_and_unicode_title(self) -> None:
        content = (
            "---\n"
            "title: 我的笔记\n"
            "tags: [读书笔记, Python, 2024]\n"
            "created: 2024-01-15\n"
            "---\n"
            "# Content\n"
        )
        metadata = parse_front_matter(content, "Fallback")
        self.assertEqual(metadata.title, "我的笔记")
        self.assertEqual(metadata.tags, ("读书笔记", "Python", "2024"))
        self.assertEqual(metadata.created, "2024-01-15")

    def test_block_tags_are_supported_and_deduplicated(self) -> None:
        content = "---\ntags:\n  - Python\n  - Notes\n  - Python\n---\nBody"
        metadata = parse_front_matter(content, "Example")
        self.assertEqual(metadata.tags, ("Python", "Notes"))

    def test_ensure_front_matter_does_not_duplicate_existing_header(self) -> None:
        original = "---\ntitle: Existing\ntags: []\ncreated: 2024-01-01\n---\nBody"
        unchanged, created = ensure_front_matter(original, "Other")
        self.assertFalse(created)
        self.assertEqual(unchanged, original)

    def test_note_template_places_metadata_before_body(self) -> None:
        content = note_template(Path("Example.md"), "# Heading")
        header, body = split_front_matter(content)
        self.assertIsNotNone(header)
        self.assertIn("title: Example", header)
        self.assertEqual(body.lstrip(), "# Heading")


class NoteIndexTests(unittest.TestCase):
    def test_index_and_recursive_and_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "Library" / "Python"
            nested.mkdir(parents=True)
            (nested / "one.md").write_text(
                "---\ntitle: One\ntags: [Python, Reading]\ncreated: 2024-01-01\n---\nOne",
                encoding="utf-8",
            )
            (nested / "two.md").write_text(
                "---\ntitle: Two\ntags: [Python]\ncreated: 2024-01-02\n---\nTwo",
                encoding="utf-8",
            )
            (root / "Library" / "image.png").write_bytes(b"image")
            hidden = root / ".cache"
            hidden.mkdir()
            (hidden / "hidden.md").write_text(
                "---\ntitle: Hidden\ntags: [Python]\ncreated: 2024-01-03\n---\nHidden",
                encoding="utf-8",
            )

            state = build_note_index(root / "Library")
            metadata = state.metadata
            counts = state.tag_counts
            self.assertEqual(counts, {"Python": 2, "Reading": 1})

            tagged = filter_workspace_files(root / "Library", "", {"Python", "Reading"}, metadata)
            self.assertEqual([path.name for path in tagged], ["one.md"])

            queried = filter_workspace_files(root / "Library", "python", set(), metadata)
            self.assertEqual({path.name for path in queried}, {"one.md", "two.md"})

            images = filter_workspace_files(root / "Library", "image", set(), metadata)
            self.assertEqual(images, [])


if __name__ == "__main__":
    unittest.main()
