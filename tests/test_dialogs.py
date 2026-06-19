from __future__ import annotations

import unittest

from writeonside_app.ui.dialogs import DialogMixin


class DialogMixinTests(unittest.TestCase):
    def test_confirmation_requires_explicit_true_choice(self) -> None:
        dialog = DialogMixin()
        dialog._ask_choice_dialog = lambda *_args, **_kwargs: True
        self.assertTrue(dialog._ask_confirmation_dialog("Delete?", danger=True))
        dialog._ask_choice_dialog = lambda *_args, **_kwargs: None
        self.assertFalse(dialog._ask_confirmation_dialog("Delete?", danger=True))

    def test_save_dialog_preserves_three_distinct_results(self) -> None:
        dialog = DialogMixin()
        for expected in ("save", "discard", None):
            dialog._ask_choice_dialog = lambda *_args, value=expected, **_kwargs: value
            self.assertEqual(expected, dialog._ask_save_discard_dialog("Save?"))


if __name__ == "__main__":
    unittest.main()
