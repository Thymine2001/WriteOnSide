from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from writeonside_app.file_labels import COLOR_TAG_PALETTE, path_key
from writeonside_app.frontmatter import NoteMetadata
from writeonside_app.ui.explorer import ExplorerMixin


class TagFilterCascadeTests(unittest.TestCase):
    def test_color_selection_limits_available_dates_and_text_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            red_note = root / "red.md"
            blue_note = root / "blue.md"
            both_note = root / "both.md"

            class Harness(ExplorerMixin):
                def __init__(self) -> None:
                    self.config = SimpleNamespace(file_color_tags={}, custom_tag_color="")
                    self._selected_tags = set()
                    self._selected_colors = {COLOR_TAG_PALETTE[0]}
                    self._selected_created_dates = set()
                    self._note_metadata = {
                        path_key(red_note): NoteMetadata(
                            title="Red",
                            tags=("project",),
                            created="2026-01-01",
                            color_tags=(COLOR_TAG_PALETTE[0],),
                        ),
                        path_key(blue_note): NoteMetadata(
                            title="Blue",
                            tags=("archive",),
                            created="2026-02-01",
                            color_tags=(COLOR_TAG_PALETTE[4],),
                        ),
                        path_key(both_note): NoteMetadata(
                            title="Both",
                            tags=("project", "shared"),
                            created="2026-03-01",
                            color_tags=(COLOR_TAG_PALETTE[0], COLOR_TAG_PALETTE[4]),
                        ),
                    }

                def _tag_scope_root(self) -> Path:
                    return root

            app = Harness()
            candidates = app._tag_candidate_items()

            self.assertEqual({"red.md", "both.md"}, {path.name for path, _metadata in candidates})
            self.assertEqual(
                {"project": 2, "shared": 1},
                app._tag_counts_for_items(candidates),
            )
            self.assertEqual(
                {"2026-01-01": 1, "2026-03-01": 1},
                app._created_date_counts_for_items(candidates),
            )
            self.assertEqual(2, app._color_tag_counts_for_items(candidates)[COLOR_TAG_PALETTE[0]])
            self.assertEqual(1, app._color_tag_counts_for_items(candidates)[COLOR_TAG_PALETTE[4]])

    def test_date_and_text_selection_limit_available_colors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            first = root / "first.md"
            second = root / "second.md"

            class Harness(ExplorerMixin):
                def __init__(self) -> None:
                    self.config = SimpleNamespace(file_color_tags={}, custom_tag_color="")
                    self._selected_tags = {"work"}
                    self._selected_colors = set()
                    self._selected_created_dates = {"2026-01-01"}
                    self._note_metadata = {
                        path_key(first): NoteMetadata(
                            title="First",
                            tags=("work", "draft"),
                            created="2026-01-01",
                            color_tags=(COLOR_TAG_PALETTE[0],),
                        ),
                        path_key(second): NoteMetadata(
                            title="Second",
                            tags=("work", "archive"),
                            created="2026-02-01",
                            color_tags=(COLOR_TAG_PALETTE[4],),
                        ),
                    }

                def _tag_scope_root(self) -> Path:
                    return root

            app = Harness()
            candidates = app._tag_candidate_items()
            color_counts = app._color_tag_counts_for_items(candidates)

            self.assertEqual(["first.md"], [path.name for path, _metadata in candidates])
            self.assertEqual(1, color_counts[COLOR_TAG_PALETTE[0]])
            self.assertEqual(0, color_counts[COLOR_TAG_PALETTE[4]])
            self.assertEqual({"work": 1, "draft": 1}, app._tag_counts_for_items(candidates))


if __name__ == "__main__":
    unittest.main()
