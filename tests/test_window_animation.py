from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from writeonside_app.ui.window import WindowMixin


class _WindowSpy:
    def __init__(self, events: list[object], name: str) -> None:
        self.events = events
        self.name = name

    def attributes(self, key: str, value: float) -> None:
        self.events.append((self.name, key, value))

    def geometry(self, value: str) -> None:
        self.events.append((self.name, "geometry", value))

    def update_idletasks(self) -> None:
        self.events.append((self.name, "idle"))

    def deiconify(self) -> None:
        self.events.append((self.name, "deiconify"))

    def withdraw(self) -> None:
        self.events.append((self.name, "withdraw"))

    def lift(self) -> None:
        self.events.append((self.name, "lift"))


class WindowAnimationTests(unittest.TestCase):
    def test_initial_panel_keeps_navigation_transparent_until_content_is_ready(self) -> None:
        events: list[object] = []

        class Harness(WindowMixin):
            def _clear_animation_clips(self) -> None:
                events.append("clips")

            def _refresh_panel_bounds(self) -> None:
                events.append("bounds")

            def _layout_positions(self, _opened: bool):
                return 1190, 980, 964, 210

            def _panel_geometry(self, _x: int) -> str:
                return "520x1080+1190+0"

            def _set_explorer_geometry(self, _x: int, _width: int) -> None:
                events.append("explorer_geometry")

            def _apply_no_taskbar_styles(self) -> None:
                events.append("styles")

            def _apply_content_opacity(self, _alpha: float) -> None:
                events.append("content_visible")

            def _update_width_resize_handles(self) -> None:
                events.append("handles")

            def _raise_nav_bar(self) -> None:
                events.append("nav_raised")

            def _refresh_nav_bar_visual(self) -> None:
                events.append("nav_visual")

        class FocusSpy:
            def focus_set(self) -> None:
                events.append("focus")

        app = Harness()
        app.animating = False
        app.is_open = False
        app._preview_alpha = None
        app.config = SimpleNamespace(alpha=0.98)
        app.explorer_visible = True
        app.panel_h = 1080
        app.panel_y = 0
        app.nav_w = 16
        app.view_mode = "edit"
        app.text = FocusSpy()
        app.read_text = FocusSpy()
        app.root = _WindowSpy(events, "root")
        app.explorer = _WindowSpy(events, "explorer")
        app.nav = _WindowSpy(events, "nav")

        app._show_initial_panel()

        self.assertLess(events.index(("nav", "-alpha", 0.0)), events.index(("nav", "deiconify")))
        self.assertLess(events.index(("nav", "deiconify")), events.index("styles"))
        self.assertLess(events.index("styles"), events.index("content_visible"))
        self.assertEqual(("nav", "-alpha", 0.72), events[events.index("content_visible") + 1])
        self.assertTrue(app.is_open)

    def test_frame_moves_navigation_before_repainting_clipped_content(self) -> None:
        events: list[object] = []

        class Harness(WindowMixin):
            @staticmethod
            def _window_handle(window) -> int:
                return {"root": 1, "nav": 2, "explorer": 3}[window]

            def _safe_animation_layout(self, panel_x, explorer_x, nav_x, explorer_width, include_explorer):
                bounds = (0, 0, 1920, 1080)
                return panel_x, explorer_x, nav_x, explorer_width, bounds, bounds

        app = Harness()
        app.root = "root"
        app.nav = "nav"
        app.explorer = "explorer"
        app.panel_y = 0
        app.panel_w = 520
        app.panel_h = 1080
        app.nav_w = 16
        app.work_left = 0
        app.work_top = 0
        app.work_right = 1920
        app.work_bottom = 1080

        def record_clip(*_args, **kwargs):
            events.append(("clip", kwargs.get("redraw")))
            return True

        with patch("writeonside_app.ui.window.clip_window_to_bounds", side_effect=record_clip), patch(
            "writeonside_app.ui.window.move_windows_atomically",
            side_effect=lambda _layouts: events.append(("move",)) or True,
        ), patch(
            "writeonside_app.ui.window.invalidate_window",
            side_effect=lambda handle: events.append(("invalidate", handle)),
        ):
            app._move_animation_frame(1700, 1490, 1474, 210, True)
            app._move_animation_frame(1700, 1490, 1474, 210, True, repaint=False)

        self.assertEqual([("clip", False), ("clip", False)], events[:2])
        self.assertEqual(("move",), events[2])
        self.assertEqual([("invalidate", 1), ("invalidate", 3)], events[3:])

    def test_open_reapplies_clip_after_native_styles_before_restoring_alpha(self) -> None:
        events: list[object] = []

        class Harness(WindowMixin):
            def _refresh_panel_bounds(self) -> None:
                events.append("bounds")

            def _layout_positions(self, _opened: bool):
                return 1920, 1920, 1904, 210

            def _panel_geometry(self, _x: int) -> str:
                return "520x1080+1920+0"

            def _set_nav_x(self, _x: int) -> None:
                events.append("nav")

            def _set_explorer_geometry(self, _x: int, _width: int) -> None:
                events.append("explorer_geometry")

            def _apply_animation_clips(self, *_args) -> None:
                events.append("initial_clip")

            def _apply_no_taskbar_styles(self) -> None:
                events.append("styles")

            def _move_animation_frame(self, *_args) -> None:
                events.append("final_closed_clip")

            def _apply_content_opacity(self, _alpha: float) -> None:
                events.append("visible")

            def _animate_layout(self, _opened: bool, callback=None, duration_ms: int = 190) -> None:
                events.append("animate")

        app = Harness()
        app.animating = False
        app.is_open = False
        app._preview_alpha = None
        app.config = SimpleNamespace(alpha=0.98)
        app.explorer_visible = True
        app.root = _WindowSpy(events, "root")
        app.explorer = _WindowSpy(events, "explorer")
        app.nav = _WindowSpy(events, "nav_window")

        app.open_panel()

        self.assertLess(events.index("styles"), events.index("final_closed_clip"))
        self.assertLess(events.index("final_closed_clip"), events.index("visible"))
        self.assertLess(events.index("visible"), events.index("animate"))

    def test_right_edge_animation_moves_windows_as_one_contiguous_group(self) -> None:
        app = WindowMixin()
        app.config = SimpleNamespace(app_position="right")
        app.work_left = 0
        app.work_top = 0
        app.work_right = 1920
        app.work_bottom = 1080
        app.panel_w = 520
        app.panel_h = 1080
        app.explorer_w = 210
        app.nav_w = 16
        app.explorer_visible = True

        panel_x, explorer_x, nav_x, explorer_width, panel_clip, explorer_clip = app._safe_animation_layout(
            panel_x=1920,
            explorer_x=1920,
            nav_x=1904,
            explorer_width=210,
            include_explorer=True,
        )

        self.assertEqual(2130, panel_x)
        self.assertEqual(1920, explorer_x)
        self.assertEqual(1904, nav_x)
        self.assertEqual(210, explorer_width)
        self.assertEqual((0, 0, 1920, 1080), panel_clip)
        self.assertEqual((0, 0, 1920, 1080), explorer_clip)

        _panel_x, _explorer_x, nav_x, _explorer_width, panel_clip, explorer_clip = app._safe_animation_layout(
            panel_x=1800,
            explorer_x=1800,
            nav_x=1784,
            explorer_width=210,
            include_explorer=True,
        )
        self.assertEqual(1784, nav_x)
        self.assertEqual(1800, _explorer_x)
        self.assertEqual(2010, _panel_x)
        self.assertEqual(_explorer_x + _explorer_width, _panel_x)
        self.assertEqual((0, 0, 1920, 1080), panel_clip)
        self.assertEqual((0, 0, 1920, 1080), explorer_clip)

    def test_left_edge_animation_moves_windows_as_one_contiguous_group(self) -> None:
        app = WindowMixin()
        app.config = SimpleNamespace(app_position="left")
        app.work_left = 0
        app.work_top = 0
        app.work_right = 1920
        app.work_bottom = 1080
        app.panel_w = 520
        app.panel_h = 1080
        app.explorer_w = 210
        app.nav_w = 16
        app.explorer_visible = True

        panel_x, explorer_x, nav_x, explorer_width, _panel_clip, _explorer_clip = app._safe_animation_layout(
            panel_x=-520,
            explorer_x=-210,
            nav_x=0,
            explorer_width=210,
            include_explorer=True,
        )

        self.assertEqual(-730, panel_x)
        self.assertEqual(-210, explorer_x)
        self.assertEqual(0, nav_x)
        self.assertEqual(panel_x + app.panel_w, explorer_x)
        self.assertEqual(explorer_x + explorer_width, nav_x)

    def test_screen_edge_anchor_keeps_nav_at_monitor_edge_when_open(self) -> None:
        app = WindowMixin()
        app.config = SimpleNamespace(app_position="right", nav_bar_anchor="screen_edge")
        app.work_left = 0
        app.work_top = 0
        app.work_right = 1920
        app.work_bottom = 1080
        app.panel_w = 520
        app.explorer_w = 210
        app.nav_w = 16
        app.explorer_visible = True

        panel_x, explorer_x, nav_x, explorer_width = app._layout_positions(True)

        self.assertEqual(1904, nav_x)
        self.assertEqual(1384, panel_x)
        self.assertEqual(1174, explorer_x)
        self.assertEqual(210, explorer_width)

    def test_screen_edge_animation_uses_layout_positions_directly(self) -> None:
        app = WindowMixin()
        app.config = SimpleNamespace(app_position="right", nav_bar_anchor="screen_edge")
        app.work_left = 0
        app.work_top = 0
        app.work_right = 1920
        app.work_bottom = 1080
        app.panel_w = 520
        app.nav_w = 16

        panel_x, explorer_x, nav_x, explorer_width, _panel_clip, _explorer_clip = app._safe_animation_layout(
            1384,
            1174,
            1904,
            210,
            True,
        )

        self.assertEqual(1384, panel_x)
        self.assertEqual(1174, explorer_x)
        self.assertEqual(1904, nav_x)
        self.assertEqual(210, explorer_width)


if __name__ == "__main__":
    unittest.main()
