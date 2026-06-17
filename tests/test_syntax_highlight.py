from __future__ import annotations

import unittest

from writeonside_app.live_highlight import plan_live_highlight
from writeonside_app.syntax_highlight import code_token_spans, normalize_code_language


class SyntaxHighlightTests(unittest.TestCase):
    def test_language_aliases_are_normalized(self) -> None:
        self.assertEqual("python", normalize_code_language("py"))
        self.assertEqual("bash", normalize_code_language("shell"))
        self.assertEqual("json", normalize_code_language("{json}"))
        self.assertEqual("", normalize_code_language(""))
        self.assertEqual("", normalize_code_language("   "))
        self.assertEqual((), code_token_spans("value\n", "   ", background="#2b303b"))

    def test_pygments_returns_token_color_spans_for_common_languages(self) -> None:
        for language, code in (
            ("python", "def demo(value):\n    return value + 1\n"),
            ("json", '{"name": "WriteOnSide", "ok": true}\n'),
            ("bash", "echo \"$HOME\"\n"),
        ):
            spans = code_token_spans(code, language, background="#2b303b")
            self.assertTrue(spans, language)
            self.assertTrue(all(span.start < span.end for span in spans))
            self.assertTrue(all(span.color.startswith("#") for span in spans))

    def test_live_highlight_adds_color_spans_inside_fenced_code_block(self) -> None:
        content = "```python\ndef demo():\n    return 1\n```\n"
        plan = plan_live_highlight(content)

        self.assertTrue(any(tag.tag == "md_code" and tag.line == 2 for tag in plan.line_tags))
        self.assertTrue(any(span.line == 2 for span in plan.color_spans))

    def test_unknown_language_keeps_code_block_safe_without_color_spans(self) -> None:
        content = "```not-a-real-language\nvalue\n```\n"
        plan = plan_live_highlight(content)

        self.assertTrue(any(tag.tag == "md_code" and tag.line == 2 for tag in plan.line_tags))
        self.assertFalse(plan.color_spans)


if __name__ == "__main__":
    unittest.main()
