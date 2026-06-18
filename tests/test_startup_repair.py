from __future__ import annotations

import unittest
from unittest.mock import patch

from writeonside_app.app import WriteOnSideApp
from writeonside_app.config import AppConfig


class _StopAfterStartupRepair(RuntimeError):
    pass


class StartupRepairTests(unittest.TestCase):
    def test_saved_startup_preference_repairs_missing_registration(self) -> None:
        config = AppConfig(start_on_boot=True)
        with patch("writeonside_app.app.load_config", return_value=config), patch(
            "writeonside_app.app.is_startup_registered", return_value=False
        ), patch("writeonside_app.app.set_startup_enabled") as set_enabled, patch.object(
            WriteOnSideApp, "_init_i18n", side_effect=_StopAfterStartupRepair
        ):
            with self.assertRaises(_StopAfterStartupRepair):
                WriteOnSideApp()

        set_enabled.assert_called_once_with(True)
        self.assertTrue(config.start_on_boot)

    def test_task_manager_disable_is_respected(self) -> None:
        config = AppConfig(start_on_boot=True)
        with patch("writeonside_app.app.load_config", return_value=config), patch(
            "writeonside_app.app.is_startup_registered", return_value=True
        ), patch("writeonside_app.app.is_startup_enabled", return_value=False), patch(
            "writeonside_app.app.set_startup_enabled"
        ) as set_enabled, patch.object(
            WriteOnSideApp, "_init_i18n", side_effect=_StopAfterStartupRepair
        ):
            with self.assertRaises(_StopAfterStartupRepair):
                WriteOnSideApp()

        set_enabled.assert_not_called()
        self.assertFalse(config.start_on_boot)


if __name__ == "__main__":
    unittest.main()
