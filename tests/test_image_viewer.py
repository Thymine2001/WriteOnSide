import unittest
from pathlib import Path

from writeonside_app.ui.image_viewer import ImageViewerMixin


class ReadImageClickTests(unittest.TestCase):
    def test_read_image_click_opens_with_system_app(self) -> None:
        calls: list[Path] = []

        class FakeReadText:
            _clickable_images = {"pyimage1": "figure.png"}

            def index(self, _position: str) -> str:
                return "1.0"

            def image_cget(self, _index: str, _option: str) -> str:
                return "pyimage1"

        class Harness(ImageViewerMixin):
            read_text = FakeReadText()

            def _open_external_file(self, path: Path, *, choose_app: bool = False) -> None:
                calls.append(path)

            def _open_image_viewer(self, _path: Path) -> None:
                raise AssertionError("internal image viewer should not be used")

        event = type("Event", (), {"x": 4, "y": 5})()

        self.assertEqual("break", Harness()._on_read_image_click(event))
        self.assertEqual([Path("figure.png")], calls)


if __name__ == "__main__":
    unittest.main()
