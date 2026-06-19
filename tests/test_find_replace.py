import unittest
import tkinter as tk

from writeonside_app.ui.editor import EditorMixin, _literal_find_pattern, _toggle_inline_wrapping


class _Value:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


class FindReplaceTests(unittest.TestCase):
    def test_atomic_replacement_disables_auto_separators_during_edit(self) -> None:
        class TextSpy:
            def __init__(self) -> None:
                self.events = []

            def cget(self, option):
                self.events.append(("cget", option))
                return True

            def edit_separator(self):
                self.events.append(("separator",))

            def configure(self, **kwargs):
                self.events.append(("configure", kwargs))

            def delete(self, start, end):
                self.events.append(("delete", start, end))

            def insert(self, start, value):
                self.events.append(("insert", start, value))

        editor = EditorMixin()
        editor.text = TextSpy()
        editor._replace_text_atomic("1.0", "1.4", "==text==")

        self.assertIn(("configure", {"autoseparators": False}), editor.text.events)
        self.assertEqual(2, editor.text.events.count(("separator",)))
        self.assertLess(editor.text.events.index(("delete", "1.0", "1.4")), editor.text.events.index(("insert", "1.0", "==text==")))

    def test_single_undo_restores_text_before_format_replacement(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            text = tk.Text(root, undo=True, autoseparators=True)
            text.insert("1.0", "selected")
            text.edit_reset()
            editor = EditorMixin()
            editor.text = text

            editor._replace_text_atomic("1.0", "1.8", "==selected==")
            text.edit_undo()

            self.assertEqual("selected", text.get("1.0", "end-1c"))
        finally:
            root.destroy()

    def test_multiline_inline_format_wraps_each_nonempty_line(self) -> None:
        updated, unwrapped = _toggle_inline_wrapping("first\nsecond\n\nthird", "==", "==")
        self.assertEqual("==first==\n==second==\n\n==third==", updated)
        self.assertFalse(unwrapped)

    def test_multiline_inline_format_toggles_off_per_line(self) -> None:
        updated, unwrapped = _toggle_inline_wrapping("~~first~~\n~~second~~\n", "~~", "~~")
        self.assertEqual("first\nsecond\n", updated)
        self.assertTrue(unwrapped)

    def test_find_panel_uses_floating_overlay_geometry(self) -> None:
        class Panel:
            def __init__(self) -> None:
                self.placed = None
                self.lifted = False

            def place(self, **kwargs) -> None:
                self.placed = kwargs

            def lift(self) -> None:
                self.lifted = True

        editor = EditorMixin()
        editor.find_panel = Panel()

        editor._place_find_panel()

        self.assertEqual(8, editor.find_panel.placed["x"])
        self.assertEqual(-16, editor.find_panel.placed["width"])
        self.assertEqual(1.0, editor.find_panel.placed["relwidth"])
        self.assertTrue(editor.find_panel.lifted)

    def test_literal_pattern_is_case_insensitive_by_default(self) -> None:
        pattern = _literal_find_pattern("Note", case_sensitive=False)
        self.assertEqual(("Note", "note", "NOTE"), tuple(pattern.findall("Note note NOTE")))

    def test_literal_pattern_can_match_case(self) -> None:
        pattern = _literal_find_pattern("Note", case_sensitive=True)
        self.assertEqual(("Note",), tuple(pattern.findall("Note note NOTE")))

    def test_find_nocase_tracks_case_sensitive_option(self) -> None:
        editor = EditorMixin()
        editor.find_case_sensitive_var = _Value(False)
        self.assertTrue(editor._find_nocase())
        editor.find_case_sensitive_var.value = True
        self.assertFalse(editor._find_nocase())


if __name__ == "__main__":
    unittest.main()
