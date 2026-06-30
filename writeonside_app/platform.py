from __future__ import annotations

import ctypes
import json
import os
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

APP_REGISTRY_NAME = "WriteOnSide"
FILE_PROG_ID = "WriteOnSide.TextFile"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APPROVED_RUN_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
)
MUTEX_NAME = r"Local\WriteOnSide.SingleInstance"
ACTIVATE_EVENT_NAME = r"Local\WriteOnSide.Activate"
OPEN_REQUEST_PATH = Path(tempfile.gettempdir()) / "WriteOnSide-open-request.json"
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
WM_SETREDRAW = 0x000B
RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100
VREFRESH = 116
_CACHED_DISPLAY_REFRESH_HZ: int | None = None


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
        if self.is_primary:
            try:
                OPEN_REQUEST_PATH.unlink(missing_ok=True)
            except OSError:
                pass

    def signal_existing(self, file_path: Path | None = None) -> None:
        if file_path is not None:
            temporary = OPEN_REQUEST_PATH.with_suffix(".tmp")
            try:
                temporary.write_text(json.dumps(str(file_path.resolve())), encoding="utf-8")
                os.replace(temporary, OPEN_REQUEST_PATH)
            except OSError:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        if self._event:
            self._kernel32.SetEvent(self._event)

    def consume_open_request(self) -> Path | None:
        try:
            value = json.loads(OPEN_REQUEST_PATH.read_text(encoding="utf-8"))
            OPEN_REQUEST_PATH.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None
        path = Path(str(value)).expanduser()
        return path.resolve() if path.exists() and path.is_file() else None

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


def window_clip_rect(
    x: int,
    y: int,
    width: int,
    height: int,
    bounds: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Return the visible bounds relative to a window, suitable for SetWindowRgn."""
    left, top, right, bottom = bounds
    relative_left = max(0, left - x)
    relative_top = max(0, top - y)
    relative_right = min(max(0, width), right - x)
    relative_bottom = min(max(0, height), bottom - y)
    if relative_right <= relative_left or relative_bottom <= relative_top:
        return 0, 0, 0, 0
    return relative_left, relative_top, relative_right, relative_bottom


def clip_window_to_bounds(
    hwnd: int,
    x: int,
    y: int,
    width: int,
    height: int,
    bounds: tuple[int, int, int, int],
    *,
    redraw: bool = True,
) -> bool:
    """Clip a native window to one monitor so animation cannot leak next door."""
    if not hwnd:
        return False
    try:
        clip = window_clip_rect(x, y, width, height, bounds)
        gdi32 = ctypes.windll.gdi32
        user32 = ctypes.windll.user32
        create_region = gdi32.CreateRectRgn
        create_region.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        create_region.restype = wintypes.HANDLE
        set_window_region = user32.SetWindowRgn
        set_window_region.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
        set_window_region.restype = ctypes.c_int
        region = create_region(*clip)
        if not region:
            return False
        if set_window_region(wintypes.HWND(hwnd), region, redraw):
            # Windows owns the region after a successful SetWindowRgn call.
            return True
        delete_object = gdi32.DeleteObject
        delete_object.argtypes = [wintypes.HANDLE]
        delete_object.restype = wintypes.BOOL
        delete_object(region)
    except (AttributeError, OSError):
        pass
    return False


def clear_window_clip(hwnd: int) -> None:
    if not hwnd:
        return
    try:
        set_window_region = ctypes.windll.user32.SetWindowRgn
        set_window_region.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
        set_window_region.restype = ctypes.c_int
        set_window_region(wintypes.HWND(hwnd), None, True)
    except (AttributeError, OSError):
        pass


def enable_per_monitor_dpi() -> None:
    """Enable per-monitor DPI awareness so Tk text renders sharply on HiDPI displays."""
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def reveal_in_file_explorer(path: Path) -> None:
    """Open the system file manager and select the given path."""
    import subprocess

    target = path.resolve()
    if not target.exists():
        raise FileNotFoundError(target)
    if target.is_dir():
        subprocess.Popen(["explorer", str(target)])
        return
    subprocess.Popen(["explorer", "/select,", str(target)])


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


def show_window_in_taskbar(hwnd: int) -> bool:
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
    updated = (style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
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


def file_open_command() -> str:
    return f'{startup_command()} "%1"'


def normalize_file_association_extensions(extensions) -> tuple[str, ...]:
    normalized: set[str] = set()
    for value in extensions:
        text = str(value).strip().casefold()
        if text:
            normalized.add(text if text.startswith(".") else f".{text}")
    return tuple(sorted(normalized))


def register_file_open_support(extensions) -> bool:
    try:
        import winreg

        supported = normalize_file_association_extensions(extensions)
        command = file_open_command()
        if getattr(sys, "frozen", False):
            icon_path = Path(sys.executable).resolve()
        else:
            icon_path = Path(__file__).resolve().parents[1] / "assets" / "WriteOnSide.ico"
        icon_value = f'"{icon_path}",0'

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{FILE_PROG_ID}") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "WriteOnSide text or code file")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{FILE_PROG_ID}\DefaultIcon") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_value)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{FILE_PROG_ID}\shell\open\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

        application_key = rf"Software\Classes\Applications\{APP_REGISTRY_NAME}.exe"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, application_key) as key:
            winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, APP_REGISTRY_NAME)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, application_key + r"\DefaultIcon") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_value)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, application_key + r"\shell\open\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, application_key + r"\SupportedTypes") as key:
            for extension in supported:
                winreg.SetValueEx(key, extension, 0, winreg.REG_SZ, "")

        capabilities_path = rf"Software\{APP_REGISTRY_NAME}\Capabilities"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, capabilities_path) as key:
            winreg.SetValueEx(key, "ApplicationName", 0, winreg.REG_SZ, APP_REGISTRY_NAME)
            winreg.SetValueEx(
                key,
                "ApplicationDescription",
                0,
                winreg.REG_SZ,
                "Edit Markdown, text, and source code files.",
            )
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, capabilities_path + r"\FileAssociations") as key:
            for extension in supported:
                winreg.SetValueEx(key, extension, 0, winreg.REG_SZ, FILE_PROG_ID)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as key:
            winreg.SetValueEx(key, APP_REGISTRY_NAME, 0, winreg.REG_SZ, capabilities_path)

        for extension in supported:
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{extension}\OpenWithProgids",
            ) as key:
                winreg.SetValueEx(key, FILE_PROG_ID, 0, winreg.REG_SZ, "")
        try:
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass
        return True
    except (OSError, AttributeError):
        return False


def is_startup_registered() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _value_type = winreg.QueryValueEx(key, APP_REGISTRY_NAME)
        registered = str(value).strip()
        return bool(registered) and registered.casefold() == startup_command().casefold()
    except OSError:
        return False


def is_startup_enabled() -> bool:
    if not is_startup_registered():
        return False
    try:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_RUN_KEY) as key:
                approval, _value_type = winreg.QueryValueEx(key, APP_REGISTRY_NAME)
        except OSError:
            return True
        # Windows Startup Apps stores 0x03 as disabled and 0x02 as enabled.
        # Removing the value lets Windows recreate an enabled approval record.
        return not (
            isinstance(approval, (bytes, bytearray))
            and len(approval) > 0
            and approval[0] == 0x03
        )
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

    # A Run value can still be blocked when Task Manager's Startup Apps page
    # has a stale disabled record. An explicit choice in WriteOnSide should
    # reset that record for both enable and disable transitions.
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_APPROVED_RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            try:
                winreg.DeleteValue(key, APP_REGISTRY_NAME)
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass

    if is_startup_enabled() != bool(enabled):
        raise OSError("Windows did not retain the WriteOnSide startup setting")

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


def get_display_refresh_rate_hz() -> int:
    """Return the primary display refresh rate, clamped to a sane animation range."""
    global _CACHED_DISPLAY_REFRESH_HZ
    if _CACHED_DISPLAY_REFRESH_HZ is not None:
        return _CACHED_DISPLAY_REFRESH_HZ
    refresh = 0
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        if hdc:
            refresh = int(gdi32.GetDeviceCaps(hdc, VREFRESH))
            user32.ReleaseDC(0, hdc)
    except Exception:
        refresh = 0
    if refresh <= 1:
        refresh = 60
    _CACHED_DISPLAY_REFRESH_HZ = max(60, min(240, refresh))
    return _CACHED_DISPLAY_REFRESH_HZ


def animation_frame_interval_ms(refresh_hz: int | None = None) -> int:
    """Schedule animation frames to match the display refresh rate."""
    hz = refresh_hz if refresh_hz is not None else get_display_refresh_rate_hz()
    hz = max(60, min(240, int(hz)))
    return max(4, int(1000 / hz))


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


def set_window_redraw(hwnd: int, enabled: bool) -> bool:
    """Pause or resume painting for a native window and all of its children."""
    if not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.SendMessageW(
            wintypes.HWND(hwnd),
            WM_SETREDRAW,
            wintypes.WPARAM(1 if enabled else 0),
            wintypes.LPARAM(0),
        )
        return True
    except (AttributeError, OSError):
        return False


def redraw_window(hwnd: int) -> None:
    """Invalidate a resumed window once, including every child control."""
    if not hwnd:
        return
    try:
        ctypes.windll.user32.RedrawWindow(
            wintypes.HWND(hwnd),
            None,
            None,
            RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW,
        )
    except (AttributeError, OSError):
        pass


def invalidate_window(hwnd: int) -> None:
    """Queue a child-inclusive repaint without blocking for WM_PAINT completion."""
    if not hwnd:
        return
    try:
        ctypes.windll.user32.RedrawWindow(
            wintypes.HWND(hwnd),
            None,
            None,
            RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN,
        )
    except (AttributeError, OSError):
        pass
