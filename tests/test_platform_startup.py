from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from writeonside_app import platform


class _Key:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        return None


class PlatformStartupTests(unittest.TestCase):
    def test_startup_registered_requires_current_command(self) -> None:
        fake_winreg = SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            OpenKey=MagicMock(return_value=_Key()),
            QueryValueEx=MagicMock(return_value=('"C:\\Apps\\OldWriteOnSide.exe"', 1)),
        )
        with patch.dict(sys.modules, {"winreg": fake_winreg}), patch.object(
            platform, "startup_command", return_value='"C:\\Apps\\WriteOnSide.exe"'
        ):
            self.assertFalse(platform.is_startup_registered())

    def test_startup_enabled_rejects_windows_disabled_record(self) -> None:
        approval_key = _Key()
        fake_winreg = SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            OpenKey=MagicMock(return_value=approval_key),
            QueryValueEx=MagicMock(return_value=(bytes([3, 0, 0, 0]), 3)),
        )
        with patch.dict(sys.modules, {"winreg": fake_winreg}), patch.object(
            platform, "is_startup_registered", return_value=True
        ):
            self.assertFalse(platform.is_startup_enabled())

    def test_startup_enabled_accepts_missing_approval_record(self) -> None:
        fake_winreg = SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            OpenKey=MagicMock(side_effect=FileNotFoundError()),
            QueryValueEx=MagicMock(),
        )
        with patch.dict(sys.modules, {"winreg": fake_winreg}), patch.object(
            platform, "is_startup_registered", return_value=True
        ):
            self.assertTrue(platform.is_startup_enabled())

    def test_enabling_writes_run_value_and_clears_disabled_record(self) -> None:
        run_key = _Key()
        approval_key = _Key()
        fake_winreg = SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            REG_SZ=1,
            KEY_SET_VALUE=2,
            CreateKey=MagicMock(return_value=run_key),
            OpenKey=MagicMock(return_value=approval_key),
            SetValueEx=MagicMock(),
            DeleteValue=MagicMock(),
        )
        command = '"C:\\Apps\\WriteOnSide.exe"'
        with patch.dict(sys.modules, {"winreg": fake_winreg}), patch.object(
            platform, "startup_command", return_value=command
        ), patch.object(platform, "is_startup_enabled", return_value=True):
            platform.set_startup_enabled(True)

        fake_winreg.SetValueEx.assert_called_once_with(
            run_key, platform.APP_REGISTRY_NAME, 0, fake_winreg.REG_SZ, command
        )
        fake_winreg.OpenKey.assert_called_once_with(
            fake_winreg.HKEY_CURRENT_USER,
            platform.STARTUP_APPROVED_RUN_KEY,
            0,
            fake_winreg.KEY_SET_VALUE,
        )
        fake_winreg.DeleteValue.assert_called_once_with(
            approval_key, platform.APP_REGISTRY_NAME
        )

    def test_failed_registry_verification_is_reported(self) -> None:
        fake_winreg = SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            REG_SZ=1,
            KEY_SET_VALUE=2,
            CreateKey=MagicMock(return_value=_Key()),
            OpenKey=MagicMock(side_effect=FileNotFoundError()),
            SetValueEx=MagicMock(),
            DeleteValue=MagicMock(),
        )
        with patch.dict(sys.modules, {"winreg": fake_winreg}), patch.object(
            platform, "startup_command", return_value='"C:\\Apps\\WriteOnSide.exe"'
        ), patch.object(platform, "is_startup_enabled", return_value=False):
            with self.assertRaisesRegex(OSError, "did not retain"):
                platform.set_startup_enabled(True)


if __name__ == "__main__":
    unittest.main()
