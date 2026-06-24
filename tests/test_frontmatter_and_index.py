from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from writeonside_app.frontmatter import (
    ensure_complete_front_matter,
    ensure_front_matter,
    note_template,
    parse_front_matter,
    set_writeonside_properties,
    split_front_matter,
)
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

    def test_ensure_complete_front_matter_creates_all_supported_fields(self) -> None:
        updated, created = ensure_complete_front_matter("# Heading\n", "Example")
        header, body = split_front_matter(updated)

        self.assertTrue(created)
        self.assertIn("title: Example", header)
        self.assertIn("tags: []", header)
        self.assertIn("created:", header)
        self.assertIn("aliases: []", header)
        self.assertIn("writeonside_colors: []", header)
        self.assertIn("writeonside_pinned: false", header)
        self.assertEqual("# Heading\n", body.lstrip())

    def test_ensure_complete_front_matter_only_adds_missing_fields(self) -> None:
        original = "---\ntitle: Existing\ntags: [Keep]\ncreated: 2024-01-01\n---\nBody"
        updated, changed = ensure_complete_front_matter(original, "Other")
        header, body = split_front_matter(updated)

        self.assertTrue(changed)
        self.assertIn("title: Existing", header)
        self.assertIn("tags: [Keep]", header)
        self.assertIn("created: 2024-01-01", header)
        self.assertIn("aliases: []", header)
        self.assertIn("writeonside_colors: []", header)
        self.assertIn("writeonside_pinned: false", header)
        self.assertEqual("Body", body)

    def test_note_template_places_metadata_before_body(self) -> None:
        content = note_template(Path("Example.md"), "# Heading")
        header, body = split_front_matter(content)
        self.assertIsNotNone(header)
        self.assertIn("title: Example", header)
        self.assertIn("tags: []", header)
        self.assertIn("created:", header)
        self.assertIn("aliases: []", header)
        self.assertIn("writeonside_colors: []", header)
        self.assertIn("writeonside_pinned: false", header)
        self.assertEqual(body.lstrip(), "# Heading")

    def test_writeonside_colors_and_pin_are_parsed_from_yaml(self) -> None:
        content = (
            "---\n"
            "title: Negishi\n"
            "tags: [Server, Purdue]\n"
            "created: 2026-06-22\n"
            'writeonside_colors: ["#DE2F24", "#5175B8"]\n'
            "writeonside_pinned: true\n"
            "---\n"
        )
        metadata = parse_front_matter(content, "Negishi")
        self.assertEqual(("#DE2F24", "#5175B8"), metadata.color_tags)
        self.assertTrue(metadata.pinned)

    def test_set_writeonside_properties_preserves_existing_header(self) -> None:
        original = "---\ntitle: Negishi\ntags: [Server, Purdue]\ncreated: 2026-06-22\naliases: [Server]\n---\nBody"
        updated = set_writeonside_properties(
            original,
            color_tags=["#DE2F24", "#5175B8"],
            pinned=True,
        )
        header, body = split_front_matter(updated)
        self.assertIn('writeonside_colors: ["red", "blue"]', header)
        self.assertIn("writeonside_pinned: true", header)
        self.assertIn("aliases: [Server]", header)
        self.assertEqual("Body", body)


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

            created = filter_workspace_files(
                root / "Library",
                "",
                set(),
                metadata,
                selected_created_dates={"2024-01-02"},
            )
            self.assertEqual([path.name for path in created], ["two.md"])


if __name__ == "__main__":
    unittest.main()
