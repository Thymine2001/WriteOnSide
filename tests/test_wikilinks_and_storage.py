from __future__ import annotations

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from writeonside_app.frontmatter import parse_front_matter
from writeonside_app.config import normalize_relative_folder
from writeonside_app.markdown import render_markdown
from writeonside_app.storage import BACKUP_RETENTION, safe_write_text
from writeonside_app.ui.notes import NotesMixin
from writeonside_app.wikilinks import WikiLinkIndex, parse_wiki_links


class WikiLinkTests(unittest.TestCase):
    def test_obsidian_link_shapes_and_aliases(self) -> None:
        links = parse_wiki_links(
            "[[Note]] [[Folder/Note#Heading|Label]] ![[image.png]] [[#Local heading]] [[Note#^block]]"
        )
        self.assertEqual(5, len(links))
        self.assertEqual(("Note", "", "", False), (links[0].target, links[0].heading, links[0].alias, links[0].embed))
        self.assertEqual(
            ("Folder/Note", "Heading", "Label", False),
            (links[1].target, links[1].heading, links[1].alias, links[1].embed),
        )
        self.assertTrue(links[2].embed)
        self.assertEqual("", links[3].target)
        self.assertEqual("Local heading", links[3].heading)

        metadata = parse_front_matter(
            "---\ntitle: Canonical\naliases: [Short, \"Other name\"]\ntags: []\n---\n",
            "Fallback",
        )
        self.assertEqual(("Short", "Other name"), metadata.aliases)

    def test_index_resolves_relative_paths_aliases_and_backlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder_a = root / "A"
            folder_b = root / "B"
            folder_a.mkdir()
            folder_b.mkdir()
            target_a = folder_a / "Target.md"
            target_b = folder_b / "Target.md"
            source = folder_a / "Source.md"
            target_a.write_text(
                "---\ntitle: Primary\naliases: [Alias]\n---\n# Section\n",
                encoding="utf-8",
            )
            target_b.write_text("# Other\n", encoding="utf-8")
            source.write_text("[[Target#Section]] and [[Alias]]", encoding="utf-8")

            index = WikiLinkIndex.build(root)
            self.assertEqual(target_a.resolve(), index.resolve("Target", source))
            self.assertEqual(target_a.resolve(), index.resolve("Alias", source))
            backlinks = index.backlinks(target_a)
            self.assertEqual(2, len(backlinks))
            self.assertEqual(source.resolve(), backlinks[0][0].path)

    def test_wiki_image_embed_renders_and_link_metadata_is_retained(self) -> None:
        try:
            root_window = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root_window.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                note = root / "Note.md"
                image_path = root / "Attachments" / "image.png"
                image_path.parent.mkdir()
                Image.new("RGB", (24, 16), "#336699").save(image_path)
                widget = tk.Text(root_window, width=40, height=10)
                widget.pack()
                root_window.update_idletasks()
                render_markdown(
                    widget,
                    "![[image.png]]\n\nSee [[Other note|the other note]].",
                    note,
                    wiki_asset_resolver=lambda target, _source: image_path if target == "image.png" else None,
                )
                self.assertEqual(1, len(widget._clickable_images))
                self.assertEqual(1, len(widget._wiki_links))
                self.assertIn("the other note", widget.get("1.0", "end-1c"))
        finally:
            root_window.destroy()


class StorageTests(unittest.TestCase):
    def test_attachment_folder_is_portable_and_scoped_to_relative_note_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()

            class AttachmentPaths(NotesMixin):
                config = SimpleNamespace(attachments_folder="Resources/Media")
                current_note_path = root / "Projects" / "Alpha" / "Note.md"

                def _workspace_dir(self) -> Path:
                    return root

            folder = AttachmentPaths()._figure_folder()
            self.assertEqual(root / "Resources" / "Media" / "Projects" / "Alpha" / "Note", folder)

    def test_invalid_attachment_folder_config_falls_back(self) -> None:
        self.assertEqual("Attachments", normalize_relative_folder("../Outside"))
        self.assertEqual("Attachments", normalize_relative_folder(r"C:\Outside"))
        self.assertEqual("Resources/Media", normalize_relative_folder(r"Resources\Media"))

    def test_backups_are_kept_outside_the_vault_and_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as backup_dir:
            root = Path(temp_dir)
            note = root / "Folder" / "Note.md"
            with patch("writeonside_app.storage.BACKUP_DIR", Path(backup_dir)):
                safe_write_text(note, "version 0", workspace_root=root)
                for version in range(BACKUP_RETENTION + 5):
                    safe_write_text(note, f"version {version + 1}", workspace_root=root)
            self.assertFalse(note.with_suffix(".md.bak").exists())
            backups = list(Path(backup_dir).rglob("*.bak"))
            self.assertEqual(BACKUP_RETENTION, len(backups))
            self.assertEqual(f"version {BACKUP_RETENTION + 5}", note.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
