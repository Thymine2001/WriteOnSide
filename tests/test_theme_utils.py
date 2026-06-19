from __future__ import annotations

import unittest
from unittest.mock import patch

from writeonside_app.ui.theme_utils import ThemeMixin


class WidgetSpy:
    def __init__(self) -> None:
        self.options: dict[str, str] = {}

    def configure(self, **kwargs) -> None:
        self.options.update(kwargs)

    def cget(self, option: str) -> str:
        return self.options.get(option, "")

    def tag_configure(self, *_args, **_kwargs) -> None:
        return None


class RootSpy(WidgetSpy):
    def __init__(self) -> None:
        super().__init__()
        self.idle_callbacks: list[object] = []

    def winfo_children(self) -> list[object]:
        return []

    def update_idletasks(self) -> None:
        return None

    def after_idle(self, callback):
        self.idle_callbacks.append(callback)
        return "idle-1"


class ThemeUtilsTests(unittest.TestCase):
    def test_lightweight_theme_apply_skips_read_rerender(self) -> None:
        class Harness(ThemeMixin):
            def __init__(self) -> None:
                self._active_theme = "graphite"
                self.read_text = WidgetSpy()
                self.render_count = 0

            def _set_theme_globals(self, name: str) -> dict[str, str]:
                from writeonside_app.theme import get_theme

                self._active_theme = name
                return get_theme(name)

            def _contrast_text(self, _color: str) -> str:
                return "white"

            def _render_read_content(self) -> None:
                self.render_count += 1

        app = Harness()
        app._apply_theme("nord", rerender_read=False, flush=False)
        self.assertEqual(0, app.render_count)
        self.assertEqual("nord", app._active_theme)

    def test_lightweight_theme_apply_skips_split_rerender_and_toolbar_layout(self) -> None:
        class Harness(ThemeMixin):
            def __init__(self) -> None:
                self._active_theme = "graphite"
                self.root = RootSpy()
                self.view_toggle_btn = WidgetSpy()
                self.split_rerender: bool | None = None
                self.toolbar_relayout: bool | None = None

            def _set_theme_globals(self, name: str) -> dict[str, str]:
                from writeonside_app.theme import get_theme

                self._active_theme = name
                return get_theme(name)

            def _refresh_split_note_panes(self, *, rerender: bool = True) -> None:
                self.split_rerender = rerender

            def _update_view_buttons(self, *, relayout: bool = True) -> None:
                self.toolbar_relayout = relayout

        app = Harness()
        app._apply_theme("nord", rerender_read=False, flush=False)
        self.assertFalse(app.split_rerender)
        self.assertFalse(app.toolbar_relayout)

    @patch("writeonside_app.ui.theme_utils.redraw_window")
    @patch("writeonside_app.ui.theme_utils.set_window_redraw", return_value=True)
    def test_theme_apply_resumes_native_redraw_after_batch(self, set_redraw, redraw) -> None:
        class Harness(ThemeMixin):
            def __init__(self) -> None:
                self._active_theme = "graphite"
                self.root = RootSpy()

            def _set_theme_globals(self, name: str) -> dict[str, str]:
                from writeonside_app.theme import get_theme

                self._active_theme = name
                return get_theme(name)

            @staticmethod
            def _window_handle(_window) -> int:
                return 101

        app = Harness()
        app._apply_theme("nord", rerender_read=False, flush=False)
        set_redraw.assert_called_once_with(101, False)
        self.assertEqual(1, len(app.root.idle_callbacks))
        app.root.idle_callbacks[0]()
        set_redraw.assert_called_with(101, True)
        redraw.assert_called_once_with(101)


if __name__ == "__main__":
    unittest.main()
