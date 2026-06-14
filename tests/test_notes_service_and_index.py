import tempfile
import unittest
from pathlib import Path

from writeonside_app.note_index import build_note_index
from writeonside_app.notes.service import rename_target, unique_note_path


class NoteServiceTests(unittest.TestCase):
    def test_unique_note_path_appends_number(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            first = unique_note_path(base, "Draft.md")
            first.write_text("one", encoding="utf-8")
            second = unique_note_path(base, "Draft.md")
            self.assertEqual("Draft 1.md", second.name)

    def test_rename_target_for_markdown_and_text(self) -> None:
        md_target = rename_target(Path("Notes/Example.md"), "Renamed", markdown=True)
        self.assertEqual("Renamed.md", md_target.name)
        text_target = rename_target(Path("Notes/log.txt"), "bad/name", markdown=False)
        self.assertEqual("bad-name", text_target.name)


class IncrementalNoteIndexTests(unittest.TestCase):
    def test_reuses_unchanged_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note = root / "note.md"
            note.write_text("---\ntitle: One\ntags: [A]\ncreated: 2024-01-01\n---\n", encoding="utf-8")
            first = build_note_index(root)
            self.assertEqual({"A": 1}, first.tag_counts)

            note.write_text("---\ntitle: One\ntags: [A, B]\ncreated: 2024-01-01\n---\n", encoding="utf-8")
            second = build_note_index(root, first)
            self.assertEqual({"A": 1, "B": 1}, second.tag_counts)
            self.assertIn(str(note.resolve()), second.metadata)


if __name__ == "__main__":
    unittest.main()
