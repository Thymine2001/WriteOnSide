import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from writeonside_app.wikilinks import (
    WikiLinkIndex,
    find_notes_linking_to,
    refresh_wiki_index,
    rename_note_and_rewrite_wikilinks,
    rewrite_wikilinks_after_rename,
)


class WikiLinkRenameTests(unittest.TestCase):
    def test_rewrite_updates_title_alias_and_heading_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "Old Name.md"
            source = root / "Source.md"
            alias_note = root / "Alias Source.md"
            target.write_text(
                "---\ntitle: Old Title\naliases: [Short Name]\n---\n# Section\n",
                encoding="utf-8",
            )
            source.write_text(
                "See [[Old Title]], [[Old Name#Section]], and [[Short Name|label]].",
                encoding="utf-8",
            )
            alias_note.write_text("Also [[Old Title#Section|jump]].", encoding="utf-8")

            index = WikiLinkIndex.build(root)
            old_path = target.resolve()
            new_path = (root / "New Title.md").resolve()
            target.rename(new_path)
            candidates = find_notes_linking_to(index, old_path)
            changed = rewrite_wikilinks_after_rename(
                root,
                old_path,
                new_path,
                old_title="Old Title",
                old_aliases=("Short Name",),
                index=index,
                candidate_paths=candidates,
            )
            self.assertEqual({source.resolve(), alias_note.resolve()}, {path.resolve() for path in changed})
            self.assertIn("[[New Title]]", source.read_text(encoding="utf-8"))
            self.assertIn("[[New Title#Section]]", source.read_text(encoding="utf-8"))
            self.assertIn("[[New Title|label]]", source.read_text(encoding="utf-8"))
            self.assertIn("[[New Title#Section|jump]]", alias_note.read_text(encoding="utf-8"))

    def test_incremental_wiki_index_reuses_unchanged_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_note = root / "One.md"
            second_note = root / "Two.md"
            first_note.write_text("[[Two]]", encoding="utf-8")
            second_note.write_text("linked", encoding="utf-8")
            index, state = refresh_wiki_index(root)
            self.assertEqual(2, len(index.notes))

            second_note.write_text("updated body with [[One]]", encoding="utf-8")
            next_index, next_state = refresh_wiki_index(root, state)
            self.assertEqual(2, len(next_index.notes))
            self.assertEqual("updated body with [[One]]", next_state.notes[second_note.resolve()].path.read_text(encoding="utf-8"))

    def test_transaction_rolls_back_rename_and_partial_link_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "Old.md"
            first = root / "First.md"
            second = root / "Second.md"
            target.write_text("# Old", encoding="utf-8")
            first.write_text("[[Old]]", encoding="utf-8")
            second.write_text("[[Old]]", encoding="utf-8")
            index = WikiLinkIndex.build(root)
            candidates = find_notes_linking_to(index, target.resolve())
            real_replace = os.replace
            updated_commits = 0

            def fail_second_updated(source, destination):
                nonlocal updated_commits
                if ".updated." in Path(source).name:
                    updated_commits += 1
                    if updated_commits == 2:
                        raise OSError("simulated transaction failure")
                return real_replace(source, destination)

            with patch("writeonside_app.wikilinks.os.replace", side_effect=fail_second_updated):
                with self.assertRaises(OSError):
                    rename_note_and_rewrite_wikilinks(
                        root,
                        target,
                        root / "New.md",
                        old_title="Old",
                        old_aliases=(),
                        index=index,
                        candidate_paths=candidates,
                    )

            self.assertTrue(target.exists())
            self.assertFalse((root / "New.md").exists())
            self.assertEqual("[[Old]]", first.read_text(encoding="utf-8"))
            self.assertEqual("[[Old]]", second.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
