import unittest
from unittest.mock import patch

from writeonside_app.hotkeys import (
    filter_phantom_hotkey_names,
    is_phantom_hotkey_key,
    normalize_hotkey,
    purge_phantom_pressed_keys,
    read_hotkey_clean,
)


class HotkeyPhantomKeyTests(unittest.TestCase):
    def test_normalize_hotkey_strips_phantom_keys(self) -> None:
        self.assertEqual("ctrl+g", normalize_hotkey("f22+ctrl+g"))
        self.assertEqual("ctrl+shift+enter", normalize_hotkey("ctrl+shift+f23+enter"))

    def test_filter_phantom_hotkey_names(self) -> None:
        self.assertEqual(["ctrl", "g"], filter_phantom_hotkey_names(["f22", "ctrl", "g", "f24"]))

    def test_is_phantom_hotkey_key(self) -> None:
        self.assertTrue(is_phantom_hotkey_key("F22"))
        self.assertFalse(is_phantom_hotkey_key("ctrl"))

    def test_purge_phantom_pressed_keys(self) -> None:
        fake_events = {
            1: type("Event", (), {"name": "f22"})(),
            2: type("Event", (), {"name": "ctrl"})(),
        }
        with patch("writeonside_app.hotkeys.keyboard._pressed_events", fake_events), patch(
            "writeonside_app.hotkeys.keyboard._pressed_events_lock"
        ):
            removed = purge_phantom_pressed_keys()
        self.assertEqual(1, removed)
        self.assertNotIn(1, fake_events)
        self.assertIn(2, fake_events)

    def test_read_hotkey_clean_ignores_stale_pressed_events(self) -> None:
        events = [
            type("Event", (), {"event_type": "down", "name": "ctrl", "scan_code": 29})(),
            type("Event", (), {"event_type": "down", "name": "g", "scan_code": 34})(),
            type("Event", (), {"event_type": "up", "name": "g", "scan_code": 34})(),
        ]

        class FakeQueue:
            def __init__(self):
                self._items = []

            def put(self, item):
                self._items.append(item)

            def get(self):
                return self._items.pop(0)

        def fake_hook(callback, suppress=False):
            for event in events:
                callback(event)
            return "hooked"

        with patch("writeonside_app.hotkeys.purge_phantom_pressed_keys"), patch(
            "writeonside_app.hotkeys.queue.Queue",
            FakeQueue,
        ), patch("writeonside_app.hotkeys.hook", fake_hook), patch(
            "writeonside_app.hotkeys.unhook"
        ), patch(
            "writeonside_app.hotkeys.get_hotkey_name",
            lambda names: "+".join(names),
        ):
            recorded = read_hotkey_clean(suppress=False)

        self.assertEqual("ctrl+g", recorded)


if __name__ == "__main__":
    unittest.main()
