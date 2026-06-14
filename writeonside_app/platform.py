from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

APP_REGISTRY_NAME = "WriteOnSide"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
MUTEX_NAME = r"Local\WriteOnSide.SingleInstance"
ACTIVATE_EVENT_NAME = r"Local\WriteOnSide.Activate"
ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class SingleInstanceGuard:
    def __init__(self) -> None:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateEventW.restype = wintypes.HANDLE
        self._kernel32 = kernel32
        self._mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        self.is_primary = bool(self._mutex) and kernel32.GetLastError() != ERROR_ALREADY_EXISTS
        self._event = kernel32.CreateEventW(None, True, False, ACTIVATE_EVENT_NAME)

    def signal_existing(self) -> None:
        if self._event:
            self._kernel32.SetEvent(self._event)

    def consume_activation(self) -> bool:
        if not self._event:
            return False
        if self._kernel32.WaitForSingleObject(self._event, 0) != WAIT_OBJECT_0:
            return False
        self._kernel32.ResetEvent(self._event)
        return True

    def close(self) -> None:
        for handle_name in ("_event", "_mutex"):
            handle = getattr(self, handle_name, None)
            if handle:
                self._kernel32.CloseHandle(handle)
                setattr(self, handle_name, None)


def get_work_area() -> tuple[int, int, int, int]:
    rect = _RECT()
    ok = ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
    if ok:
        return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, 0, 0


def hide_window_from_taskbar(hwnd: int) -> bool:
    if not hwnd:
        return False
    user32 = ctypes.windll.user32
    get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    set_style.restype = ctypes.c_ssize_t
    style = int(get_style(wintypes.HWND(hwnd), GWL_EXSTYLE))
    updated = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
    if updated != style:
        set_style(wintypes.HWND(hwnd), GWL_EXSTYLE, updated)
    flags = SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
    return bool(user32.SetWindowPos(wintypes.HWND(hwnd), None, 0, 0, 0, 0, flags))


def get_system_color_mode() -> str | None:
    """Return the Windows app color mode, or None when it cannot be detected."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            use_light_theme, _value_type = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if int(use_light_theme) else "dark"
    except (OSError, TypeError, ValueError):
        return None


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    entry = Path(__file__).resolve().parents[1] / "writeonside.py"
    python = Path(sys.executable).resolve()
    pythonw = python.with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else python
    return f'"{launcher}" "{entry}"'


def is_startup_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _value_type = winreg.QueryValueEx(key, APP_REGISTRY_NAME)
        registered = str(value).strip()
        return bool(registered) and registered.casefold() == startup_command().casefold()
    except OSError:
        return False


def set_startup_enabled(enabled: bool) -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, APP_REGISTRY_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, APP_REGISTRY_NAME)
            except FileNotFoundError:
                pass

def set_timer_resolution(enabled: bool) -> None:
    """Raise the Windows timer resolution to 1 ms while animating.

    Tk's after() otherwise fires on the default ~15.6 ms tick, which makes
    a 10 ms animation frame schedule visibly uneven.
    """
    try:
        winmm = ctypes.windll.winmm
        if enabled:
            winmm.timeBeginPeriod(1)
        else:
            winmm.timeEndPeriod(1)
    except Exception:
        pass


def move_windows_atomically(layouts: list[tuple[int, int, int, int, int]]) -> bool:
    """Move top-level HWNDs in one compositor update to avoid animation flicker."""
    if not layouts:
        return True
    user32 = ctypes.windll.user32
    user32.BeginDeferWindowPos.argtypes = [ctypes.c_int]
    user32.BeginDeferWindowPos.restype = wintypes.HANDLE
    user32.DeferWindowPos.argtypes = [
        wintypes.HANDLE, wintypes.HWND, wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.DeferWindowPos.restype = wintypes.HANDLE
    user32.EndDeferWindowPos.argtypes = [wintypes.HANDLE]
    user32.EndDeferWindowPos.restype = wintypes.BOOL
    batch = user32.BeginDeferWindowPos(len(layouts))
    if not batch:
        return False
    flags = 0x0004 | 0x0010  # SWP_NOZORDER | SWP_NOACTIVATE
    for hwnd, x, y, width, height in layouts:
        batch = user32.DeferWindowPos(
            batch,
            wintypes.HWND(hwnd),
            None,
            int(x),
            int(y),
            max(1, int(width)),
            max(1, int(height)),
            flags,
        )
        if not batch:
            return False
    return bool(user32.EndDeferWindowPos(batch))
