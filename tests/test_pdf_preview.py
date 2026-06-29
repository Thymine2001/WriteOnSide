import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from writeonside_app.preview import (
    PDF_CUSTOM_ZOOM,
    PDF_FIT_PAGE,
    PDF_FIT_WIDTH,
    _is_pdf_path,
    _pdf_preview_fit,
    _pdf_preview_size,
    forward_mousewheel_to_text,
    render_file_preview,
    set_pdf_preview_fit,
    set_pdf_preview_zoom,
    insert_pdf_preview_block,
    text_content_width,
)
from writeonside_app.ui.editor import EditorMixin


class PdfPreviewTests(unittest.TestCase):
    def test_pdf_path_detection(self) -> None:
        self.assertTrue(_is_pdf_path(Path("report.PDF")))
        self.assertFalse(_is_pdf_path(Path("report.txt")))

    def test_pdf_preview_renders_first_page_and_controls(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf = Path(temp_dir) / "report.pdf"
                pdf.write_bytes(b"%PDF-1.7\n")
                widget = tk.Text(root, width=60, height=20)
                widget.pack()
                root.update_idletasks()

                with patch(
                    "writeonside_app.preview._render_pdf_page",
                    return_value=(Image.new("RGB", (80, 100), "white"), 3),
                ) as render_page:
                    result = render_file_preview(widget, pdf)

                self.assertEqual("pdf", result)
                render_page.assert_called_once()
                self.assertEqual(0, widget._pdf_preview_page)
                self.assertEqual(3, widget._pdf_preview_page_count)
                self.assertEqual(1, len(widget._file_preview_images))
                self.assertEqual(1, len(widget._file_preview_windows))
                self.assertIn("PDF", widget.get("1.0", "end-1c"))
        finally:
            root.destroy()

    def test_svg_file_preview_renders_as_image(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                svg = Path(temp_dir) / "diagram.svg"
                svg.write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="16">'
                    '<rect width="24" height="16" fill="#336699"/>'
                    "</svg>",
                    encoding="utf-8",
                )
                widget = tk.Text(root, width=60, height=20)
                widget.pack()
                root.update_idletasks()

                result = render_file_preview(widget, svg)

                self.assertEqual("image", result)
                self.assertEqual(1, len(widget._file_preview_images))
                self.assertIn("24 x 16", widget.get("1.0", "end-1c"))
        finally:
            root.destroy()

    def test_pdf_block_frame_uses_text_width(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf = Path(temp_dir) / "report.pdf"
                pdf.write_bytes(b"%PDF-1.7\n")
                widget = tk.Text(root, width=80, height=20)
                widget.pack()
                root.update_idletasks()

                with patch(
                    "writeonside_app.preview._render_pdf_page",
                    return_value=(Image.new("RGB", (80, 100), "white"), 1),
                ):
                    frame = insert_pdf_preview_block(widget, pdf)

                self.assertIsNotNone(frame)
                self.assertEqual(text_content_width(widget), int(frame.cget("width")))
        finally:
            root.destroy()

    def test_pdf_block_toolbar_does_not_force_frame_wider_than_text(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf = Path(temp_dir) / "report.pdf"
                pdf.write_bytes(b"%PDF-1.7\n")
                widget = tk.Text(root, width=44, height=20, padx=8)
                widget.pack()
                root.update_idletasks()

                with patch(
                    "writeonside_app.preview._render_pdf_page",
                    return_value=(Image.new("RGB", (260, 320), "white"), 4),
                ):
                    frame = insert_pdf_preview_block(widget, pdf)
                    root.update_idletasks()

                self.assertIsNotNone(frame)
                self.assertLessEqual(frame.winfo_reqwidth(), text_content_width(widget) + 2)
        finally:
            root.destroy()

    def test_pdf_block_toolbar_keeps_page_controls_visible(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf = Path(temp_dir) / "report.pdf"
                pdf.write_bytes(b"%PDF-1.7\n")
                widget = tk.Text(root, width=44, height=20, padx=8)
                widget.pack()
                root.update_idletasks()

                with patch(
                    "writeonside_app.preview._render_pdf_page",
                    return_value=(Image.new("RGB", (260, 320), "white"), 4),
                ):
                    frame = insert_pdf_preview_block(widget, pdf)
                    root.update_idletasks()

                entries: list[tk.Entry] = []
                labels: list[tk.Label] = []

                def collect(child: tk.Widget) -> None:
                    if isinstance(child, tk.Entry):
                        entries.append(child)
                    if isinstance(child, tk.Label):
                        labels.append(child)
                    for grandchild in child.winfo_children():
                        collect(grandchild)

                self.assertIsNotNone(frame)
                collect(frame)
                self.assertTrue(any(entry.get() == "1" and entry.winfo_manager() == "pack" for entry in entries))
                self.assertTrue(any("/ 4" in label.cget("text") and label.winfo_manager() == "pack" for label in labels))
        finally:
            root.destroy()

    def test_pdf_preview_fit_and_zoom_change_render_size(self) -> None:
        class Widget:
            _pdf_preview_zoom = 1.0
            _pdf_preview_fit = PDF_FIT_WIDTH

            def winfo_width(self) -> int:
                return 420

            def winfo_height(self) -> int:
                return 560

        widget = Widget()
        fit_width = _pdf_preview_size(widget)
        set_pdf_preview_fit(widget, PDF_FIT_PAGE)
        fit_page = _pdf_preview_size(widget)
        set_pdf_preview_zoom(widget, 1.5)
        zoomed = _pdf_preview_size(widget)
        clamped = set_pdf_preview_zoom(widget, 99)

        self.assertGreater(fit_width[1], fit_page[1])
        self.assertEqual(PDF_CUSTOM_ZOOM, _pdf_preview_fit(widget))
        self.assertGreater(zoomed[0], fit_page[0])
        self.assertGreater(zoomed[1], fit_page[1])
        self.assertEqual(3.0, clamped)

    def test_ctrl_mousewheel_updates_pdf_zoom(self) -> None:
        calls: list[str] = []

        class ReadText:
            _pdf_preview_zoom = 1.0

        class Harness(EditorMixin):
            preview_path = Path("report.pdf")
            read_text = ReadText()

            def _hide_code_copy_btn(self) -> None:
                calls.append("hide")

            def _render_read_content(self) -> None:
                calls.append("render")

        event = type("Event", (), {"state": 0x0004, "delta": 120})()

        self.assertEqual("break", Harness()._on_read_mousewheel(event))
        self.assertGreater(Harness.read_text._pdf_preview_zoom, 1.0)
        self.assertEqual(["hide", "render"], calls)

    def test_read_preview_configure_skips_rerender_when_layout_is_unchanged(self) -> None:
        class ReadText:
            def __init__(self) -> None:
                self.width = 500
                self.height = 700
                self.options = {"padx": 10}

            def winfo_width(self) -> int:
                return self.width

            def winfo_height(self) -> int:
                return self.height

            def configure(self, **options) -> None:
                self.options.update(options)

            def cget(self, key: str):
                return self.options.get(key, "")

        class Root:
            def __init__(self) -> None:
                self.after_calls = []

            def after(self, delay: int, callback):
                self.after_calls.append((delay, callback))
                return f"after-{len(self.after_calls)}"

            def after_cancel(self, _after_id: str) -> None:
                return None

        class Harness(EditorMixin):
            def __init__(self) -> None:
                self.preview_path = Path("report.pdf")
                self.read_text = ReadText()
                self.root = Root()
                self.config = SimpleNamespace(font_family="Segoe UI", font_size=10)
                self._preview_render_after = None
                self._preview_render_signature = self._preview_layout_signature()

        app = Harness()

        app._on_read_view_configure()
        self.assertEqual([], app.root.after_calls)

        app.read_text.width = 560
        app._on_read_view_configure()
        self.assertEqual(1, len(app.root.after_calls))

    def test_embedded_preview_mousewheel_forwards_to_text_widget(self) -> None:
        class Widget:
            def __init__(self, children=None) -> None:
                self.children = children or []
                self.handler = None

            def bind(self, event_name: str, handler, add: str | None = None) -> None:
                self.event_name = event_name
                self.handler = handler
                self.add = add

            def winfo_children(self):
                return self.children

        class TextWidget:
            def __init__(self) -> None:
                self.generated: list[tuple[str, int]] = []

            def event_generate(self, event_name: str, *, delta: int, x: int, y: int) -> None:
                self.generated.append((event_name, delta))

        child = Widget()
        frame = Widget([child])
        text = TextWidget()
        event = type("Event", (), {"state": 0, "delta": -120})()

        forward_mousewheel_to_text(frame, text)

        self.assertEqual("break", child.handler(event))
        self.assertEqual([("<MouseWheel>", -120)], text.generated)

    def test_new_pdf_resets_previous_page_and_zoom(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                first = Path(temp_dir) / "first.pdf"
                second = Path(temp_dir) / "second.pdf"
                first.write_bytes(b"%PDF-1.7\n")
                second.write_bytes(b"%PDF-1.7\n")
                widget = tk.Text(root, width=60, height=20)
                widget.pack()
                root.update_idletasks()
                widget._pdf_preview_path = str(first.resolve())
                widget._pdf_preview_page = 4
                widget._pdf_preview_zoom = 2.0
                widget._pdf_preview_fit = PDF_FIT_PAGE

                with patch(
                    "writeonside_app.preview._render_pdf_page",
                    return_value=(Image.new("RGB", (80, 100), "white"), 2),
                ) as render_page:
                    render_file_preview(widget, second)

                self.assertEqual(0, widget._pdf_preview_page)
                self.assertEqual(1.0, widget._pdf_preview_zoom)
                self.assertEqual(PDF_FIT_WIDTH, widget._pdf_preview_fit)
                self.assertEqual(0, render_page.call_args.args[1])
        finally:
            root.destroy()

    def test_pdf_preview_error_falls_back_to_info(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf = Path(temp_dir) / "broken.pdf"
                pdf.write_bytes(b"not a pdf")
                widget = tk.Text(root, width=60, height=20)
                widget.pack()
                root.update_idletasks()

                with patch("writeonside_app.preview._render_pdf_page", side_effect=ValueError("broken")):
                    result = render_file_preview(widget, pdf)

                self.assertEqual("info", result)
                self.assertIn("PDF preview unavailable", widget.get("1.0", "end-1c"))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
