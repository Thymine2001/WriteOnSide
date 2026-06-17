from __future__ import annotations

import unittest

from writeonside_app.app import WriteOnSideApp


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


if __name__ == "__main__":
    unittest.main()
