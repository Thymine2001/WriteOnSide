import unittest

from writeonside_app.ui.editor import EditorMixin, _literal_find_pattern


class _Value:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


class FindReplaceTests(unittest.TestCase):
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
