from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from writeonside_app.attachment_index import (
    attachment_index_is_current,
    collect_attachment_references,
    format_file_size,
    matches_filter,
    scan_attachments,
    suffix_category,
)


class AttachmentIndexTests(unittest.TestCase):
    def test_suffix_category_groups_common_types(self) -> None:
        self.assertEqual("images", suffix_category(".png"))
        self.assertEqual("pdf", suffix_category(".pdf"))
        self.assertEqual("text", suffix_category(".py"))
        self.assertEqual("other", suffix_category(".xyz"))

    def test_markdown_files_are_excluded_from_attachment_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            attachments = root / "Attachments" / "Note"
            attachments.mkdir(parents=True)
            (attachments / "orphan.md").write_text("# orphan", encoding="utf-8")
            (attachments / "orphan.pdf").write_bytes(b"pdf")

            _root, items, _state = scan_attachments(root, "Attachments")
            names = {item.path.name for item in items}
            self.assertNotIn("orphan.md", names)
            self.assertIn("orphan.pdf", names)

    def test_format_file_size(self) -> None:
        self.assertEqual("512 B", format_file_size(512))
        self.assertEqual("1.0 KB", format_file_size(1024))

    def test_scan_detects_referenced_and_unreferenced_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            note = root / "Projects" / "Alpha.md"
            note.parent.mkdir(parents=True)
            attachments = root / "Attachments" / "Projects" / "Alpha"
            attachments.mkdir(parents=True)
            used = attachments / "used.png"
            orphan = attachments / "orphan.pdf"
            used.write_bytes(b"png")
            orphan.write_bytes(b"pdf")
            note.write_text(
                "# Alpha\n\n![Used](../Attachments/Projects/Alpha/used.png)\n",
                encoding="utf-8",
            )

            _root, items, _state = scan_attachments(root, "Attachments")
            by_name = {item.path.name: item for item in items}
            self.assertEqual(2, len(items))
            self.assertTrue(by_name["used.png"].referenced)
            self.assertFalse(by_name["orphan.pdf"].referenced)

    def test_collect_references_finds_markdown_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            note = root / "Note.md"
            attachment = root / "Attachments" / "Note" / "sheet.xlsx"
            attachment.parent.mkdir(parents=True)
            attachment.write_bytes(b"xlsx")
            note.write_text("[Budget](Attachments/Note/sheet.xlsx)", encoding="utf-8")

            refs = collect_attachment_references(root, root / "Attachments")
            self.assertEqual(1, refs.get(attachment.resolve(), 0))

    def test_matches_filter_supports_type_query_and_unreferenced(self) -> None:
        from writeonside_app.attachment_index import AttachmentInfo

        referenced = AttachmentInfo(
            path=Path("Attachments/a.png"),
            relative=Path("a.png"),
            size=10,
            suffix=".png",
            reference_count=1,
        )
        orphan = AttachmentInfo(
            path=Path("Attachments/b.pdf"),
            relative=Path("b.pdf"),
            size=20,
            suffix=".pdf",
            reference_count=0,
        )
        self.assertTrue(matches_filter(referenced, type_filter="images", query="", unreferenced_only=False))
        self.assertFalse(matches_filter(orphan, type_filter="images", query="", unreferenced_only=False))
        self.assertTrue(matches_filter(orphan, type_filter="pdf", query="", unreferenced_only=True))

    def test_scan_reuses_cache_when_workspace_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            attachments = root / "Attachments"
            attachments.mkdir(parents=True)
            (attachments / "file.pdf").write_bytes(b"pdf")

            _root, items, state = scan_attachments(root, "Attachments")
            self.assertEqual(1, len(items))

            _root2, items2, state2 = scan_attachments(root, "Attachments", previous=state)
            self.assertIs(state, state2)
            self.assertEqual(items, items2)
            self.assertTrue(attachment_index_is_current(state2, root, "Attachments"))

    def test_cache_invalidates_when_note_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            note = root / "Note.md"
            attachment = root / "Attachments" / "Note" / "used.png"
            attachment.parent.mkdir(parents=True)
            attachment.write_bytes(b"png")
            note.write_text("# empty\n", encoding="utf-8")

            _root, _items, state = scan_attachments(root, "Attachments")
            self.assertFalse(
                any(item.path.name == "used.png" and item.referenced for item in state.items)
            )

            note.write_text(f"![Used]({attachment.as_posix()})\n", encoding="utf-8")
            self.assertFalse(attachment_index_is_current(state, root, "Attachments"))

            _root, items, state2 = scan_attachments(root, "Attachments", previous=state)
            by_name = {item.path.name: item for item in items}
            self.assertTrue(by_name["used.png"].referenced)
            self.assertIsNot(state, state2)


if __name__ == "__main__":
    unittest.main()
