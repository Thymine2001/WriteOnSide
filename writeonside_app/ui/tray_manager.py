from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path
from typing import Callable

import keyboard
import pystray
import tkinter as tk
from PIL import Image

from ..config import APP_NAME
from ..hotkeys import format_hotkey_display, normalize_hotkey, purge_phantom_pressed_keys, validate_hotkey
from ..i18n import t
from ..platform import SingleInstanceGuard, get_system_color_mode
from ..theme import *  # noqa: F401,F403


class TrayMixin:
    def _post_ui(self, func: Callable[[], None]) -> None:
        self._ui_queue.put(func)

    def _poll_ui_queue(self) -> None:
        while True:
            try:
                func = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func()
            except tk.TclError:
                pass
        self.root.after(50, self._poll_ui_queue)

    def _activate_existing_window(self) -> None:
        if self.animating:
            self.root.after(180, self._activate_existing_window)
            return
        if not self.is_open:
            self.open_panel()
            return
        self.root.deiconify()
        if self.explorer_visible:
            self.explorer.deiconify()
            self.explorer.lift()
        self._apply_no_taskbar_styles()
        self.root.lift()
        self.root.focus_force()

    def _poll_instance_activation(self) -> None:
        guard = self._instance_guard
        if guard is not None and guard.consume_activation():
            self._activate_existing_window()
        try:
            self._instance_poll_after = self.root.after(200, self._poll_instance_activation)
        except tk.TclError:
            self._instance_poll_after = None

    def _unregister_hotkey(self) -> None:
        if self._active_hotkey is not None:
            try:
                keyboard.remove_hotkey(self._active_hotkey)
            except Exception:
                pass
            self._active_hotkey = None

    def _register_hotkey(self) -> None:
        self._unregister_hotkey()
        purge_phantom_pressed_keys()
        hotkey = normalize_hotkey(self.config.hotkey)

        def trigger() -> None:
            self._post_ui(self.toggle_panel)

        try:
            self._active_hotkey = keyboard.add_hotkey(hotkey, trigger)
            self._set_status_key("status.ready")
        except Exception as exc:
            self._active_hotkey = None
            self._set_error(t("error.hotkey_unavailable", exc=exc))

    def _resource_path(self, *parts: str) -> Path:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        return base.joinpath(*parts)

    def _preferred_icon_asset(self) -> str:
        mode = get_system_color_mode()
        if mode == "light":
            return "icon_dark.png"
        return "icon_light.png"

    def _set_window_icon(self, asset_name: str | None = None) -> None:
        asset_name = asset_name or self._preferred_icon_asset()
        try:
            icon_path = self._resource_path("assets", asset_name)
            self._window_icon = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self._window_icon)
            self._active_icon_asset = asset_name
        except (OSError, tk.TclError):
            self._window_icon = None

    def _make_tray_icon(self, asset_name: str | None = None) -> Image.Image:
        asset_name = asset_name or self._preferred_icon_asset()
        icon_path = self._resource_path("assets", asset_name)
        try:
            with Image.open(icon_path) as source:
                icon = source.convert("RGBA")
                icon.thumbnail((256, 256), Image.LANCZOS)
                return icon.copy()
        except OSError:
            return Image.new("RGBA", (64, 64), globals()["ACCENT"])

    def _poll_system_icon(self) -> None:
        asset_name = self._preferred_icon_asset()
        if asset_name != self._active_icon_asset:
            self._set_window_icon(asset_name)
            tray = getattr(self, "tray", None)
            if tray is not None:
                try:
                    tray.icon = self._make_tray_icon(asset_name)
                except Exception:
                    pass
        try:
            self._icon_poll_after = self.root.after(2000, self._poll_system_icon)
        except tk.TclError:
            self._icon_poll_after = None

    def _setup_tray(self) -> None:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem(t("tray.toggle"), lambda: self._post_ui(self.toggle_panel)),
            pystray.MenuItem(t("tray.new_note"), lambda: self._post_ui(self._create_new_note)),
            pystray.MenuItem(t("tray.settings"), lambda: self._post_ui(self._open_settings)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.quit"), lambda: self._post_ui(self._quit)),
        )
        self.tray = pystray.Icon(APP_NAME, self._make_tray_icon(), APP_NAME, menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _quit(self) -> None:
        self._save_note(False)
        self._unregister_command_shortcuts()
        self._unregister_hotkey()
        if self._instance_poll_after is not None:
            try:
                self.root.after_cancel(self._instance_poll_after)
            except tk.TclError:
                pass
            self._instance_poll_after = None
        if self._instance_guard is not None:
            self._instance_guard.close()
        if self._icon_poll_after is not None:
            try:
                self.root.after_cancel(self._icon_poll_after)
            except tk.TclError:
                pass
            self._icon_poll_after = None
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.nav.destroy()
        except tk.TclError:
            pass
        try:
            self.explorer.destroy()
        except tk.TclError:
            pass
        viewer = getattr(self, "_image_viewer_window", None)
        if viewer is not None:
            try:
                viewer.destroy()
            except tk.TclError:
                pass
        self.root.quit()
