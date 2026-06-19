from __future__ import annotations

import unittest

from writeonside_app.app import WriteOnSideApp
from writeonside_app.ui.tray_manager import TrayMixin


class _InterruptedRoot:
    def mainloop(self) -> None:
        raise KeyboardInterrupt


class AppLifecycleTests(unittest.TestCase):
    def test_keyboard_interrupt_uses_normal_quit_path(self) -> None:
        app = object.__new__(WriteOnSideApp)
        app.root = _InterruptedRoot()
        quit_calls: list[bool] = []
        app._quit = lambda: quit_calls.append(True)

        app.run()

        self.assertEqual([True], quit_calls)

    def test_shutdown_saves_main_and_split_notes(self) -> None:
        class Root:
            def quit(self) -> None:
                calls.append("quit")

        class Window:
            def destroy(self) -> None:
                calls.append("destroy")

        class Tray:
            def stop(self) -> None:
                calls.append("tray")

        class Harness(TrayMixin):
            def _save_note(self, _show_indicator: bool) -> None:
                calls.append("main")

            def _save_all_split_notes(self) -> None:
                calls.append("split")

            def _stop_vault_watcher(self) -> None:
                calls.append("watcher")

            def _unregister_command_shortcuts(self) -> None:
                calls.append("commands")

            def _unregister_hotkey(self) -> None:
                calls.append("hotkey")

        calls: list[str] = []
        app = Harness()
        app.root = Root()
        app.nav = Window()
        app.explorer = Window()
        app.tray = Tray()
        app._instance_poll_after = None
        app._instance_guard = None
        app._icon_poll_after = None
        app._image_viewer_window = None

        app._shutdown()

        self.assertEqual(["main", "split"], calls[:2])
        self.assertIn("quit", calls)


if __name__ == "__main__":
    unittest.main()
