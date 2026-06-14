import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from writeonside_app.markdown import render_markdown
from writeonside_app.obsidian_md import find_block_line
from writeonside_app.wikilinks import parse_wiki_links


class ObsidianMarkdownTests(unittest.TestCase):
    def test_block_reference_links_parse_separately_from_headings(self) -> None:
        links = parse_wiki_links("[[Note#^block-id]] [[#^local-id|Jump]] [[Note#Heading]]")
        self.assertEqual("block-id", links[0].block_id)
        self.assertEqual("", links[0].heading)
        self.assertEqual("local-id", links[1].block_id)
        self.assertEqual("Jump", links[1].alias)
        self.assertEqual("Heading", links[2].heading)
        self.assertEqual("", links[2].block_id)

    def test_find_block_line_matches_obsidian_block_suffix(self) -> None:
        content = "Paragraph one\n\nTarget paragraph ^my-block\n"
        self.assertEqual(3, find_block_line(content, "my-block"))

    def test_callouts_tags_comments_and_footnotes_render(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            widget = tk.Text(root, width=60, height=20)
            widget.pack()
            root.update_idletasks()
            render_markdown(
                widget,
                "\n".join(
                    [
                        "Tags #project/demo and #idea",
                        "",
                        "%% secret draft %%",
                        "",
                        "> [!warning] Watch out",
                        "> Something important",
                        "",
                        "Use footnote[^note]",
                        "",
                        "[^note]: Hidden detail",
                    ]
                ),
                Path("Note.md"),
            )
            rendered = widget.get("1.0", "end-1c")
            self.assertIn("#project/demo", rendered)
            self.assertIn("Watch out", rendered)
            self.assertIn("Footnotes", rendered)
            self.assertIn("Hidden detail", rendered)
            self.assertNotIn("secret draft", rendered)
        finally:
            root.destroy()

    def test_note_embed_renders_transcluded_body(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                note = Path(temp_dir) / "Host.md"
                widget = tk.Text(root, width=50, height=12)
                widget.pack()
                root.update_idletasks()
                render_markdown(
                    widget,
                    "![[Other]]",
                    note,
                    wiki_note_resolver=lambda target, _source: ("Other", "Embedded **body**")
                    if target == "Other"
                    else None,
                )
                rendered = widget.get("1.0", "end-1c")
                self.assertIn("Other", rendered)
                self.assertIn("Embedded", rendered)
                self.assertIn("body", rendered)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
