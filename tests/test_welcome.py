from __future__ import annotations

import unittest

from writeonside_app.welcome import WELCOME_NOTE_BODY


class WelcomeNoteTests(unittest.TestCase):
    def test_welcome_note_opens_with_a_read_mode_prompt(self) -> None:
        first_line = WELCOME_NOTE_BODY.splitlines()[0]

        self.assertIn('style="color: #e11d48"', first_line)
        self.assertIn("==", first_line)
        self.assertIn("Ctrl+E", first_line)
        self.assertIn("Read mode", first_line)

    def test_welcome_note_is_a_complete_getting_started_guide(self) -> None:
        expected_topics = (
            "Start here: your first minute",
            "Write without leaving the keyboard",
            "Connect your thinking",
            "Find anything again",
            "Work with more than one note",
            "Add images, attachments, and other files",
            "Manage files safely",
            "Make WriteOnSide fit your workflow",
            "Useful default shortcuts",
        )

        for topic in expected_topics:
            with self.subTest(topic=topic):
                self.assertIn(topic, WELCOME_NOTE_BODY)

    def test_welcome_note_demonstrates_supported_markdown(self) -> None:
        examples = (
            "> [!note]",
            "- [ ]",
            "| Action | Shortcut |",
            "```python",
            "[[My First Note]]",
            "#project/writeonside",
            "[^welcome-footnote]",
            "%% Comments like this",
        )

        for example in examples:
            with self.subTest(example=example):
                self.assertIn(example, WELCOME_NOTE_BODY)

        self.assertGreater(len(WELCOME_NOTE_BODY.splitlines()), 100)


if __name__ == "__main__":
    unittest.main()
