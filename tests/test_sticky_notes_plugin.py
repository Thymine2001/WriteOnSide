import tempfile
import unittest
from pathlib import Path

from writeonside_app.builtin_plugins.sticky_notes import (
    StickyNotesWindow,
    next_sticky_path,
    safe_attachment_name,
    normalize_sticky_tags,
    sticky_window_geometry,
    sticky_note_content,
    sticky_title,
    unique_sticky_path_for_title,
)
from writeonside_app.frontmatter import parse_front_matter, split_front_matter


class StickyNotesPluginTests(unittest.TestCase):
    def test_normalize_sticky_tags_accepts_typed_and_selected_tags(self) -> None:
        self.assertEqual(["todo", "idea", "Project X"], normalize_sticky_tags("#todo, idea，todo\nProject X"))

    def test_sticky_note_content_writes_yaml_but_body_stays_clean(self) -> None:
        content = sticky_note_content(
            "Quick thought\n\nMore detail",
            ["sticky", "idea"],
            title="Quick thought",
            created="2026-06-23",
        )

        metadata = parse_front_matter(content, "fallback")
        _header, body = split_front_matter(content)

        self.assertEqual("Quick thought", metadata.title)
        self.assertEqual(("sticky", "idea"), metadata.tags)
        self.assertEqual("2026-06-23", metadata.created)
        self.assertIn("aliases: []", _header)
        self.assertIn("writeonside_colors: []", _header)
        self.assertIn("writeonside_pinned: false", _header)
        self.assertEqual("Quick thought\n\nMore detail", body)

    def test_sticky_title_uses_first_nonempty_body_line(self) -> None:
        self.assertEqual("Important", sticky_title("\n# Important\nbody", "fallback"))
        self.assertEqual("fallback", sticky_title("\n\n", "fallback"))

    def test_next_sticky_path_is_unique_markdown_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            first = next_sticky_path(folder)
            first.write_text("", encoding="utf-8")
            second = next_sticky_path(folder)

        self.assertEqual(".md", first.suffix)
        self.assertEqual(".md", second.suffix)
        self.assertNotEqual(first.name, second.name)

    def test_sticky_window_geometry_places_window_on_left(self) -> None:
        class DummyApp:
            work_left = 100
            work_top = 50
            work_right = 1700
            work_bottom = 950

        geometry = sticky_window_geometry(DummyApp(), 380, 360, index=0)

        self.assertEqual("380x360+124+114", geometry)

    def test_sticky_window_geometry_offsets_from_previous_window(self) -> None:
        class DummyApp:
            work_left = 100
            work_top = 50
            work_right = 1700
            work_bottom = 950

        class PreviousWindow:
            def update_idletasks(self) -> None:
                pass

            def winfo_x(self) -> int:
                return 210

            def winfo_y(self) -> int:
                return 160

        geometry = sticky_window_geometry(DummyApp(), 380, 360, previous=PreviousWindow())

        self.assertEqual("380x360+232+188", geometry)

    def test_unique_sticky_path_for_title_matches_yaml_title_stem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)

            path = unique_sticky_path_for_title(folder, "My/Sticky:Note")

        self.assertEqual("My-Sticky-Note.md", path.name)
        self.assertEqual("My-Sticky-Note", path.stem)

    def test_unique_sticky_path_for_title_avoids_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            existing = folder / "Idea.md"
            existing.write_text("", encoding="utf-8")

            path = unique_sticky_path_for_title(folder, "Idea")

        self.assertEqual("Idea-2.md", path.name)
        self.assertEqual("Idea-2", path.stem)

    def test_sticky_window_can_be_flagged_to_create_new_note(self) -> None:
        window = StickyNotesWindow(object(), create_new_note=True)

        self.assertTrue(window.create_new_note)

    def test_sticky_window_accepts_initial_path(self) -> None:
        path = Path("Example.md")
        window = StickyNotesWindow(object(), initial_path=path)

        self.assertEqual(path, window.initial_path)

    def test_sync_path_to_title_keeps_existing_note_in_original_folder(self) -> None:
        class DummyApp:
            pass

        with tempfile.TemporaryDirectory() as temp_dir:
            original_folder = Path(temp_dir) / "Project"
            original_folder.mkdir()
            original = original_folder / "Old.md"
            original.write_text("", encoding="utf-8")
            window = StickyNotesWindow(DummyApp(), initial_path=original)
            window.path = original

            target, title = window.sync_path_to_title("New")

        self.assertEqual(original_folder / "New.md", target)
        self.assertEqual("New", title)

    def test_sticky_window_uses_only_plugin_tags_without_ui(self) -> None:
        class DummyApp:
            class Config:
                sticky_notes_default_tag = "sticky"

            config = Config()

        window = StickyNotesWindow(DummyApp())

        self.assertEqual(["plugin-sticky-notes", "sticky-notes"], window.tags())

    def test_sticky_image_markdown_regex_detects_pasted_image(self) -> None:
        from writeonside_app.builtin_plugins.sticky_notes import IMAGE_MD_RE

        match = IMAGE_MD_RE.search("![sticky image](../../Attachments/Plugins/StickyNotes/Note/image.png)")

        self.assertIsNotNone(match)
        self.assertEqual("../../Attachments/Plugins/StickyNotes/Note/image.png", match.group(1))

    def test_sticky_image_markdown_uses_relative_path_for_attachments(self) -> None:
        class DummyApp:
            def __init__(self, workspace: Path) -> None:
                self.workspace = workspace

                class Config:
                    attachments_folder = "Attachments"

                self.config = Config()

            def _workspace_dir(self) -> Path:
                return self.workspace

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            window = StickyNotesWindow(DummyApp(workspace))
            window.path = workspace / "Plugins" / "StickyNotes" / "New sticky note-2.md"
            target = workspace / "Attachments" / "Plugins" / "StickyNotes" / "New sticky note-2" / "sticky.png"

            rel = window.markdown_relative_path(target)

        self.assertEqual("../../Attachments/Plugins/StickyNotes/New sticky note-2/sticky.png", rel)
        self.assertNotIn(":", rel)

    def test_safe_attachment_name_preserves_png_suffix(self) -> None:
        self.assertEqual("sticky-20260623.png", safe_attachment_name("sticky-20260623.png"))
        self.assertEqual("bad-name.png", safe_attachment_name("bad/name.png"))

    def test_sticky_notes_module_is_theme_synced(self) -> None:
        from writeonside_app import theme

        self.assertIn("writeonside_app.builtin_plugins.sticky_notes", theme._THEME_SYNC_MODULES)


if __name__ == "__main__":
    unittest.main()
