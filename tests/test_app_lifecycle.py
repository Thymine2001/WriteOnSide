from __future__ import annotations

import unittest
from unittest.mock import patch

from writeonside_app.config import AppConfig
from writeonside_app.app import WriteOnSideApp
from writeonside_app.ui.tray_manager import TrayMixin


class _InterruptedRoot:
    def mainloop(self) -> None:
        raise KeyboardInterrupt


class AppLifecycleTests(unittest.TestCase):
    def test_expensive_startup_work_is_scheduled_after_first_idle_frame(self) -> None:
        scheduled: list[tuple[int, object]] = []

        class Root:
            def after(self, delay: int, callback):
                scheduled.append((delay, callback))
                return f"after-{delay}"

        app = object.__new__(WriteOnSideApp)
        app.root = Root()
        app._finish_startup_content = lambda: None
        app._register_hotkey = lambda: None
        app._register_sticky_notes_hotkey = lambda: None
        app._register_plugin_shortcuts = lambda: None
        app._finish_startup_services = lambda: None

        app._schedule_deferred_startup()

        self.assertEqual([1, 35, 55, 70, 120], [delay for delay, _callback in scheduled])

    def test_startup_content_defers_full_explorer_index(self) -> None:
        calls: list[object] = []

        class Root:
            def after(self, delay: int, callback):
                calls.append((delay, callback))
                return "explorer-after"

        app = object.__new__(WriteOnSideApp)
        app.root = Root()
        app._initial_file = None
        app._apply_typography = lambda: calls.append("typography")
        app._load_initial_note = lambda **kwargs: calls.append(("note", kwargs))
        app._show_initial_panel = lambda: calls.append("show")
        app._refresh_explorer = lambda: None

        app._finish_startup_content()

        self.assertEqual("typography", calls[0])
        self.assertEqual(("note", {"refresh_explorer": False}), calls[1])
        self.assertEqual("show", calls[2])
        self.assertEqual(80, calls[3][0])

    def test_keyboard_interrupt_uses_normal_quit_path(self) -> None:
        app = object.__new__(WriteOnSideApp)
        app.root = _InterruptedRoot()
        quit_calls: list[bool] = []
        app._quit = lambda: quit_calls.append(True)

        app.run()

        self.assertEqual([True], quit_calls)

    def test_sticky_notes_plugin_shortcut_opens_new_hotkey_window(self) -> None:
        callbacks = []
        calls: list[str] = []

        class Harness(TrayMixin):
            config = AppConfig(plugin_shortcuts={"sticky_notes": "ctrl+alt+s"}, sticky_notes_double_ctrl=False)

            def _post_ui(self, callback) -> None:
                callback()

            def _open_sticky_notes(self) -> None:
                calls.append("sticky-hotkey")

            def _run_plugin_entrypoint(self, _entrypoint: str) -> None:
                calls.append("plugin-entrypoint")

        def fake_add_hotkey(_hotkey, callback):
            callbacks.append(callback)
            return "handle"

        app = Harness()
        app._active_plugin_shortcuts = {}
        with patch("writeonside_app.ui.tray_manager.keyboard.add_hotkey", fake_add_hotkey):
            app._register_plugin_shortcuts()

        callbacks[0]()

        self.assertEqual(["sticky-hotkey"], calls)

    def test_disabled_sticky_notes_plugin_shortcut_is_not_registered(self) -> None:
        callbacks = []

        class Harness(TrayMixin):
            config = AppConfig(
                plugin_shortcuts={"sticky_notes": "ctrl+alt+s"},
                sticky_notes_double_ctrl=False,
                disabled_plugins=["sticky_notes"],
            )

        def fake_add_hotkey(_hotkey, callback):
            callbacks.append(callback)
            return "handle"

        app = Harness()
        app._active_plugin_shortcuts = {}
        with patch("writeonside_app.ui.tray_manager.keyboard.add_hotkey", fake_add_hotkey):
            app._register_plugin_shortcuts()

        self.assertEqual([], callbacks)
        self.assertEqual({}, app._active_plugin_shortcuts)

    def test_stale_sticky_notes_plugin_shortcut_rechecks_plugin_status(self) -> None:
        callbacks = []
        calls: list[str] = []

        class Harness(TrayMixin):
            config = AppConfig(plugin_shortcuts={"sticky_notes": "ctrl+alt+s"}, sticky_notes_double_ctrl=False)

            def _post_ui(self, callback) -> None:
                callback()

            def _open_sticky_notes(self) -> None:
                calls.append("sticky-hotkey")

        def fake_add_hotkey(_hotkey, callback):
            callbacks.append(callback)
            return "handle"

        app = Harness()
        app._active_plugin_shortcuts = {}
        with patch("writeonside_app.ui.tray_manager.keyboard.add_hotkey", fake_add_hotkey):
            app._register_plugin_shortcuts()

        app.config.disabled_plugins = ["sticky_notes"]
        callbacks[0]()

        self.assertEqual([], calls)

    def test_disabled_sticky_notes_double_ctrl_hook_does_not_open(self) -> None:
        hooks = []
        calls: list[str] = []

        class Harness(TrayMixin):
            config = AppConfig(sticky_notes_double_ctrl=True)

            def _post_ui(self, callback) -> None:
                callback()

            def _open_sticky_notes(self) -> None:
                calls.append("sticky-hotkey")

        def fake_hook(callback, suppress=False):
            hooks.append(callback)
            return "hook"

        app = Harness()
        app._active_sticky_notes_hook = None
        with patch("writeonside_app.ui.tray_manager.keyboard.hook", fake_hook):
            app._register_sticky_notes_hotkey()

        app.config.removed_plugins = ["sticky_notes"]
        event = type("Event", (), {"event_type": "down", "name": "ctrl"})()
        hooks[0](event)
        hooks[0](event)

        self.assertEqual([], calls)

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
