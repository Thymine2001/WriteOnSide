from __future__ import annotations

import time
from typing import Callable

import tkinter as tk

from ..layout_metrics import (
    clamp_layout_widths,
    explorer_width_limits,
    panel_width_limits,
)
from ..platform import get_work_area, hide_window_from_taskbar, move_windows_atomically, set_timer_resolution
from ..i18n import t
from ..theme import *  # noqa: F401,F403


class WindowMixin:
    _RESIZE_EDGE_HIT_PX = 7

    def _setup_width_resize_handles(self) -> None:
        g = globals()
        self.panel_resize_handle = tk.Frame(
            self.root,
            bg=g["BORDER"],
            width=2,
            cursor="sb_h_double_arrow",
        )
        self.explorer_resize_handle = tk.Frame(
            self.explorer,
            bg=g["SIDEBAR_BORDER"],
            width=2,
            cursor="sb_h_double_arrow",
        )
        for handle, kind in (
            (self.panel_resize_handle, "panel"),
            (self.explorer_resize_handle, "explorer"),
        ):
            handle.bind("<ButtonPress-1>", lambda event, value=kind: self._start_width_resize(event, value))
            handle.bind("<B1-Motion>", self._drag_width_resize)
            handle.bind("<ButtonRelease-1>", self._finish_width_resize)
            handle.bind(
                "<Enter>",
                lambda _event, target=handle, value=kind: self._enter_width_resize_handle(target, value),
            )
            handle.bind(
                "<Leave>",
                lambda _event, target=handle, value=kind: self._leave_width_resize_handle(target, value),
            )
        for host in (self.root, self.explorer):
            host.bind("<ButtonPress-1>", self._start_width_resize_from_edge, add="+")
            host.bind("<B1-Motion>", self._drag_width_resize_from_edge, add="+")
            host.bind("<ButtonRelease-1>", self._finish_width_resize_from_edge, add="+")
        self._update_width_resize_handles()

    def _resize_handle_color(self, kind: str) -> str:
        if getattr(self, "_width_resize_kind", None) == kind:
            return globals()["ACCENT_2"]
        return globals()["BORDER"] if kind == "panel" else globals()["SIDEBAR_BORDER"]

    def _enter_width_resize_handle(self, handle: tk.Frame, kind: str) -> None:
        handle.configure(
            bg=globals()["ACCENT_2"]
            if getattr(self, "_width_resize_kind", None) == kind
            else globals()["ACCENT"]
        )
        self._show_tooltip(
            handle,
            t("tooltip.resize_panel") if kind == "panel" else t("tooltip.resize_explorer"),
        )

    def _leave_width_resize_handle(self, handle: tk.Frame, kind: str) -> None:
        handle.configure(bg=self._resize_handle_color(kind))
        self._hide_tooltip()

    def _resize_kind_at_pointer(self, pointer_x: int) -> str | None:
        if not self.is_open or self.animating:
            return None
        panel_x, explorer_x, _nav_x, explorer_width = self._layout_positions(True)
        if self.config.app_position == "left":
            panel_edge = panel_x + self.panel_w
            explorer_edge = explorer_x + explorer_width
        else:
            panel_edge = panel_x
            explorer_edge = explorer_x
        candidates = [("panel", abs(pointer_x - panel_edge))]
        if self.explorer_visible and explorer_width > 0:
            candidates.append(("explorer", abs(pointer_x - explorer_edge)))
        kind, distance = min(candidates, key=lambda item: item[1])
        return kind if distance <= self._RESIZE_EDGE_HIT_PX else None

    def _start_width_resize_from_edge(self, event) -> None:
        if event.widget in {self.panel_resize_handle, self.explorer_resize_handle}:
            return
        kind = self._resize_kind_at_pointer(int(event.x_root))
        if kind:
            self._start_width_resize(event, kind)

    def _drag_width_resize_from_edge(self, event) -> None:
        if event.widget in {self.panel_resize_handle, self.explorer_resize_handle}:
            return
        if getattr(self, "_width_resize_kind", None):
            self._drag_width_resize(event)

    def _finish_width_resize_from_edge(self, event) -> None:
        if event.widget in {self.panel_resize_handle, self.explorer_resize_handle}:
            return
        if getattr(self, "_width_resize_kind", None):
            self._finish_width_resize(event)

    def _update_width_resize_handles(self) -> None:
        if not hasattr(self, "panel_resize_handle"):
            return
        if self.config.app_position == "left":
            self.panel_resize_handle.place(relx=1.0, x=-2, y=0, width=2, relheight=1.0)
            self.explorer_resize_handle.place(relx=1.0, x=-2, y=0, width=2, relheight=1.0)
        else:
            self.panel_resize_handle.place(x=0, y=0, width=2, relheight=1.0)
            self.explorer_resize_handle.place(x=0, y=0, width=2, relheight=1.0)
        self.panel_resize_handle.lift()
        self.explorer_resize_handle.lift()

    def _start_width_resize(self, _event, kind: str) -> str:
        if self.animating or not self.is_open:
            return "break"
        if getattr(self, "_width_resize_kind", None) == kind:
            return "break"
        self._width_resize_kind = kind
        self._width_pending_x = None
        self._width_last_applied = None
        self._refresh_panel_bounds()
        if not self._width_drag_timer_active:
            set_timer_resolution(True)
            self._width_drag_timer_active = True
        self._hide_tooltip()
        target = self.panel_resize_handle if kind == "panel" else self.explorer_resize_handle
        target.configure(bg=globals()["ACCENT_2"])
        return "break"

    def _drag_width_resize(self, event) -> str:
        if not getattr(self, "_width_resize_kind", None):
            return "break"
        self._width_pending_x = int(event.x_root)
        if self._width_drag_after is None:
            self._width_drag_after = self.root.after(16, self._apply_pending_width_resize)
        return "break"

    def _apply_pending_width_resize(self) -> None:
        self._width_drag_after = None
        kind = getattr(self, "_width_resize_kind", None)
        pointer_x = self._width_pending_x
        self._width_pending_x = None
        if not kind or pointer_x is None:
            return
        side = self.config.app_position
        if kind == "panel":
            width = pointer_x - self.work_left if side == "left" else self.work_right - pointer_x
            panel_min, panel_max = panel_width_limits(self.work_right - self.work_left)
            next_width = max(panel_min, min(panel_max, int(width)))
            if self._width_last_applied == (kind, next_width):
                return
            self.panel_w = next_width
            self.config.width = self.panel_w
        elif self.explorer_visible:
            panel_x = self.work_left if side == "left" else self.work_right - self.panel_w
            panel_edge = panel_x + self.panel_w if side == "left" else panel_x
            width = pointer_x - panel_edge if side == "left" else panel_edge - pointer_x
            explorer_min, explorer_max = explorer_width_limits(self.work_right - self.work_left)
            next_width = max(explorer_min, min(explorer_max, int(width)))
            if self._width_last_applied == (kind, next_width):
                return
            self.explorer_w = next_width
            self.config.explorer_width = self.explorer_w
        else:
            return
        self._width_last_applied = (kind, next_width)
        self._apply_live_width_layout()
        width_sync = getattr(self, "_settings_width_sync", None)
        if width_sync is not None:
            width_sync(self.panel_w, self.explorer_w)

    def _apply_live_width_layout(self) -> None:
        panel_x, explorer_x, nav_x, explorer_width = self._layout_positions(True)
        layouts = [
            (self._window_handle(self.root), panel_x, self.panel_y, self.panel_w, self.panel_h),
            (self._window_handle(self.nav), nav_x, self.panel_y, self.nav_w, self.panel_h),
        ]
        if self.explorer_visible and explorer_width > 0:
            layouts.append(
                (
                    self._window_handle(self.explorer),
                    explorer_x,
                    self.panel_y,
                    max(1, explorer_width),
                    self.panel_h,
                )
            )
        if not move_windows_atomically(layouts):
            self.root.geometry(self._panel_geometry(panel_x))
            self.nav.geometry(f"{self.nav_w}x{self.panel_h}+{int(nav_x)}+{self.panel_y}")
            if self.explorer_visible and explorer_width > 0:
                self._set_explorer_geometry(explorer_x, explorer_width)

    def _refresh_after_width_drag(self) -> None:
        self._width_refresh_after = None
        self.explorer_frame.configure(width=self.explorer_w)
        self._update_width_resize_handles()
        self._relayout_toolbar(force=True)
        if hasattr(self, "_fit_file_tree_width"):
            self._fit_file_tree_width()

    def _finish_width_resize(self, _event=None) -> str:
        if getattr(self, "_width_resize_kind", None):
            kind = self._width_resize_kind
            if self._width_drag_after is not None:
                try:
                    self.root.after_cancel(self._width_drag_after)
                except tk.TclError:
                    pass
                self._width_drag_after = None
            self._apply_pending_width_resize()
            self._width_resize_kind = None
            self._width_pending_x = None
            self._width_last_applied = None
            if self._width_drag_timer_active:
                set_timer_resolution(False)
                self._width_drag_timer_active = False
            target = self.panel_resize_handle if kind == "panel" else self.explorer_resize_handle
            target.configure(bg=self._resize_handle_color(kind))
            self._refresh_after_width_drag()
            from ..config import save_config

            if not self._settings_open:
                save_config(self.config)
                self._set_status_key("status.width_saved")
            else:
                self._set_status_key("status.width_preview")
        return "break"

    def _refresh_panel_bounds(self) -> None:
        left, top, right, bottom = get_work_area()
        if right <= left or bottom <= top:
            left, top, right, bottom = 0, 0, self.screen_w, self.screen_h
        self.work_left, self.work_top, self.work_right, self.work_bottom = left, top, right, bottom
        self.panel_y = top
        self.panel_h = bottom - top
        work_width = right - left
        self.panel_w, self.explorer_w = clamp_layout_widths(self.panel_w, self.explorer_w, work_width)
        self.config.width = self.panel_w
        self.config.explorer_width = self.explorer_w

    def _panel_geometry(self, x: int, width: int | None = None) -> str:
        panel_width = self.panel_w if width is None else max(1, int(width))
        return f"{panel_width}x{self.panel_h}+{x}+{self.panel_y}"

    def _layout_positions(self, opened: bool, position: str | None = None) -> tuple[int, int, int, int]:
        side = position or self.config.app_position
        if not opened:
            if side == "left":
                return self.work_left - self.panel_w, self.work_left - self.explorer_w, self.work_left, self.explorer_w
            return self.work_right, self.work_right, self.work_right - self.nav_w, self.explorer_w

        panel_x = self.work_left if side == "left" else self.work_right - self.panel_w
        if not self.explorer_visible:
            nav_x = panel_x + self.panel_w if side == "left" else panel_x - self.nav_w
            return panel_x, panel_x, nav_x, 0

        if side == "left":
            available = max(0, self.work_right - self.nav_w - (panel_x + self.panel_w))
            explorer_width = min(self.explorer_w, available)
            explorer_x = panel_x + self.panel_w
            nav_x = explorer_x + explorer_width
        else:
            available = max(0, panel_x - self.work_left - self.nav_w)
            explorer_width = min(self.explorer_w, available)
            explorer_x = panel_x - explorer_width
            nav_x = explorer_x - self.nav_w
        return panel_x, explorer_x, nav_x, explorer_width

    def _cancel_layout_animation(self) -> None:
        self._layout_animation_id += 1
        self.animating = False
        if getattr(self, "_timer_res_active", False):
            set_timer_resolution(False)
            self._timer_res_active = False

    def _raise_nav_bar(self) -> None:
        if not hasattr(self, "nav"):
            return
        try:
            self.nav.deiconify()
            self.nav.attributes("-topmost", True)
            self.nav.lift()
        except tk.TclError:
            pass

    def _nav_idle_alpha(self) -> float:
        return 0.72

    def _nav_hover_alpha(self) -> float:
        return 0.96

    def _refresh_nav_bar_visual(self, hover: bool = False) -> None:
        if not hasattr(self, "nav_canvas"):
            return
        canvas = self.nav_canvas
        width = max(self.nav_w, canvas.winfo_width())
        height = max(1, canvas.winfo_height())

        accent = globals()["ACCENT"]
        accent_2 = globals()["ACCENT_2"]
        border = globals()["BORDER"]
        background = accent_2 if hover else accent
        canvas.delete("all")
        canvas.configure(bg=background)
        self.nav.configure(bg=background)

        edge = "right" if self.config.app_position == "right" else "left"
        inner_x = width - 2 if edge == "right" else 2
        canvas.create_rectangle(0, 0, width, height, fill=background, outline=border, width=1)
        canvas.create_line(inner_x, 0, inner_x, height, fill=border, width=1)

    def _bind_nav_bar_events(self) -> None:
        def nav_resize_edge_x() -> int:
            _panel_x, explorer_x, _nav_x, explorer_width = self._layout_positions(True)
            if self.config.app_position == "left":
                return explorer_x + explorer_width
            return explorer_x

        def on_click(event) -> str:
            if self.is_open and self.explorer_visible and not self.animating:
                edge_x = nav_resize_edge_x()
                if abs(int(event.x_root) - edge_x) <= 4:
                    self._start_width_resize(event, "explorer")
                    return "break"
            self.toggle_panel()
            return "break"

        def on_drag(event) -> str | None:
            if getattr(self, "_width_resize_kind", None) == "explorer":
                self._drag_width_resize(event)
                return "break"
            return None

        def on_release(event) -> str | None:
            if getattr(self, "_width_resize_kind", None) == "explorer":
                self._finish_width_resize(event)
                return "break"
            return None

        def on_enter(_event) -> None:
            try:
                self.nav.attributes("-alpha", self._nav_hover_alpha())
            except tk.TclError:
                pass
            self._refresh_nav_bar_visual(hover=True)

        def on_leave(_event) -> None:
            try:
                self.nav.attributes("-alpha", self._nav_idle_alpha())
            except tk.TclError:
                pass
            self._refresh_nav_bar_visual(hover=False)

        # A Toplevel bind receives events from its child canvas through Tk's
        # bindtags. Binding both widgets would run toggle_panel twice.
        self.nav.bind("<ButtonPress-1>", on_click)
        self.nav.bind("<B1-Motion>", on_drag)
        self.nav.bind("<ButtonRelease-1>", on_release)
        self.nav.bind("<Enter>", on_enter)
        self.nav.bind("<Leave>", on_leave)

    def _set_nav_x(self, x: int) -> None:
        self.nav.geometry(f"{self.nav_w}x{self.panel_h}+{int(x)}+{self.panel_y}")
        self._raise_nav_bar()
        self._refresh_nav_bar_visual()

    def _set_explorer_geometry(self, x: int, width: int) -> None:
        self.explorer.geometry(f"{max(1, int(width))}x{self.panel_h}+{int(x)}+{self.panel_y}")

    def _place_layout(self, opened: bool) -> None:
        self._refresh_panel_bounds()
        panel_x, explorer_x, nav_x, explorer_width = self._layout_positions(opened)
        self.root.geometry(self._panel_geometry(panel_x))
        self._set_nav_x(nav_x)
        if opened and self.explorer_visible and explorer_width > 0:
            self._set_explorer_geometry(explorer_x, explorer_width)
            self.explorer.deiconify()
            self._apply_no_taskbar_styles()
        else:
            self.explorer.withdraw()
        self._update_width_resize_handles()

    def _position_nav_bar(self) -> None:
        self._refresh_panel_bounds()
        _panel_x, _explorer_x, nav_x, _explorer_width = self._layout_positions(self.is_open)
        self._set_nav_x(nav_x)

    def _show_nav_bar(self) -> None:
        self._position_nav_bar()

    def _position_explorer(self) -> None:
        if not hasattr(self, "explorer"):
            return
        _panel_x, explorer_x, _nav_x, explorer_width = self._layout_positions(self.is_open)
        if self.is_open and self.explorer_visible and explorer_width > 0:
            self._set_explorer_geometry(explorer_x, explorer_width)
        else:
            self.explorer.withdraw()

    def _open_panel_x(self) -> int:
        return self._layout_positions(True)[0]

    def _closed_panel_x(self) -> int:
        return self._layout_positions(False)[0]

    @staticmethod
    def _window_handle(window: tk.Misc) -> int:
        try:
            return int(window.frame(), 0)
        except (AttributeError, TypeError, ValueError, tk.TclError):
            return int(window.winfo_id())

    def _apply_no_taskbar_styles(self) -> None:
        for window_name in ("root", "explorer", "nav"):
            window = getattr(self, window_name, None)
            if window is None:
                continue
            try:
                window.update_idletasks()
                hide_window_from_taskbar(self._window_handle(window))
            except tk.TclError:
                pass

    def _move_animation_frame(
        self,
        panel_x: int,
        explorer_x: int,
        nav_x: int,
        explorer_width: int,
        include_explorer: bool,
    ) -> None:
        layouts = [
            (self._window_handle(self.root), panel_x, self.panel_y, self.panel_w, self.panel_h),
            (self._window_handle(self.nav), nav_x, self.panel_y, self.nav_w, self.panel_h),
        ]
        if include_explorer:
            layouts.append(
                (self._window_handle(self.explorer), explorer_x, self.panel_y, max(1, explorer_width), self.panel_h)
            )
        if move_windows_atomically(layouts):
            return
        self.root.geometry(self._panel_geometry(panel_x))
        self.nav.geometry(f"{self.nav_w}x{self.panel_h}+{int(nav_x)}+{self.panel_y}")
        if include_explorer:
            self._set_explorer_geometry(explorer_x, explorer_width)

    def _animate_layout(self, opened: bool, callback: Callable[[], None] | None = None, duration_ms: int = 190) -> None:
        self._layout_animation_id += 1
        animation_id = self._layout_animation_id
        self.animating = True
        self._refresh_panel_bounds()
        self.root.update_idletasks()
        self.nav.update_idletasks()
        self.explorer.update_idletasks()
        panel_start = self.root.winfo_x()
        nav_start = self.nav.winfo_x()
        explorer_start = self.explorer.winfo_x()
        explorer_width_start = max(1, self.explorer.winfo_width())
        panel_target, explorer_target, nav_target, explorer_width_target = self._layout_positions(opened)
        animate_explorer = self.explorer_visible and explorer_width_target > 0
        if opened:
            # Only needed when windows are being revealed; on close they are
            # already visible/styled and these Win32 calls would stall frame 1
            self.nav.deiconify()
            self._apply_no_taskbar_styles()
            self.nav.lift()
            if animate_explorer:
                self.explorer.deiconify()
                self._apply_no_taskbar_styles()
                self.explorer.lift()
        frame_ms = 16
        started_at = time.perf_counter()
        if getattr(self, "_timer_res_active", False):
            set_timer_resolution(False)
        set_timer_resolution(True)
        self._timer_res_active = True

        def ease_in_out(progress: float) -> float:
            return progress * progress * (3.0 - 2.0 * progress)

        def interpolate(start: int, target: int, progress: float) -> int:
            return round(start + (target - start) * progress)

        def step_once() -> None:
            if animation_id != self._layout_animation_id:
                return
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            progress = min(1.0, elapsed_ms / max(1, duration_ms))
            eased = ease_in_out(progress)
            self._move_animation_frame(
                interpolate(panel_start, panel_target, eased),
                interpolate(explorer_start, explorer_target, eased),
                interpolate(nav_start, nav_target, eased),
                interpolate(explorer_width_start, explorer_width_target, eased),
                animate_explorer,
            )
            if progress >= 1.0:
                self._move_animation_frame(
                    panel_target, explorer_target, nav_target, explorer_width_target, animate_explorer,
                )
                self.animating = False
                if self._timer_res_active:
                    set_timer_resolution(False)
                    self._timer_res_active = False
                if callback:
                    callback()
                self._raise_nav_bar()
                self._refresh_nav_bar_visual()
                return
            self.root.after(frame_ms, step_once)

        step_once()

    def _animate_side_switch(
        self,
        previous_position: str,
        callback: Callable[[], None] | None = None,
        duration_ms: int = 420,
    ) -> None:
        if getattr(self, "_width_resize_kind", None):
            self._finish_width_resize()
        self._layout_animation_id += 1
        animation_id = self._layout_animation_id
        self.animating = True
        self._refresh_panel_bounds()
        self.root.update_idletasks()
        self.nav.update_idletasks()
        self.explorer.update_idletasks()
        panel_start = self.root.winfo_x()
        nav_start = self.nav.winfo_x()
        explorer_start = self.explorer.winfo_x()
        explorer_width_start = max(1, self.explorer.winfo_width())
        if not self.root.winfo_viewable():
            panel_start, explorer_start, nav_start, explorer_width_start = self._layout_positions(
                True, previous_position
            )
        panel_target, explorer_target, nav_target, explorer_width_target = self._layout_positions(True)
        include_explorer = self.explorer_visible and explorer_width_target > 0

        self.nav.deiconify()
        if include_explorer:
            self.explorer.deiconify()
        self._move_animation_frame(
            panel_start,
            explorer_start,
            nav_start,
            explorer_width_start,
            include_explorer,
        )

        if getattr(self, "_timer_res_active", False):
            set_timer_resolution(False)
        set_timer_resolution(True)
        self._timer_res_active = True
        started_at = time.perf_counter()

        def interpolate(start: int, target: int, progress: float) -> int:
            return round(start + (target - start) * progress)

        def ease_mirror_motion(progress: float) -> float:
            ramp = 0.18
            velocity = 1.0 / (1.0 - ramp)
            if progress < ramp:
                return velocity * progress * progress / (2.0 * ramp)
            if progress > 1.0 - ramp:
                remaining = 1.0 - progress
                return 1.0 - velocity * remaining * remaining / (2.0 * ramp)
            return velocity * (progress - ramp / 2.0)

        def step_once() -> None:
            if animation_id != self._layout_animation_id:
                return
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            progress = min(1.0, elapsed_ms / max(1, duration_ms))
            eased = ease_mirror_motion(progress)
            self._move_animation_frame(
                interpolate(panel_start, panel_target, eased),
                interpolate(explorer_start, explorer_target, eased),
                interpolate(nav_start, nav_target, eased),
                interpolate(explorer_width_start, explorer_width_target, eased),
                include_explorer,
            )
            if progress < 1.0:
                self.root.after(16, step_once)
                return
            self._move_animation_frame(
                panel_target,
                explorer_target,
                nav_target,
                explorer_width_target,
                include_explorer,
            )
            self.animating = False
            if self._timer_res_active:
                set_timer_resolution(False)
                self._timer_res_active = False
            self._update_width_resize_handles()
            if callback:
                callback()
            self._raise_nav_bar()
            self._refresh_nav_bar_visual()

        step_once()

    def open_panel(self) -> None:
        if self.animating or self.is_open:
            return
        self._refresh_panel_bounds()
        alpha = self._preview_alpha if self._preview_alpha is not None else self.config.alpha
        self.root.attributes("-alpha", 0.0)
        self.explorer.attributes("-alpha", 0.0)
        panel_x, explorer_x, nav_x, explorer_width = self._layout_positions(False)
        self.root.geometry(self._panel_geometry(panel_x))
        self._set_nav_x(nav_x)
        if self.explorer_visible:
            self._set_explorer_geometry(explorer_x, max(1, explorer_width))
        self.root.update_idletasks()
        self.explorer.update_idletasks()
        self.root.deiconify()
        if self.explorer_visible:
            self.explorer.deiconify()
        self.root.update_idletasks()
        self.explorer.update_idletasks()
        self._apply_no_taskbar_styles()
        self._apply_content_opacity(alpha)
        self.nav.update_idletasks()
        self.is_open = True

        def done() -> None:
            self._refresh_main_layout()
            if self.explorer_visible:
                self._refresh_explorer()
                self.explorer.lift()
                self.root.lift()
            else:
                self.explorer.withdraw()
            self._raise_nav_bar()
            self._refresh_nav_bar_visual()
            self.text.focus_set() if self.view_mode == "edit" else self.read_text.focus_set()

        self._animate_layout(True, callback=done)

    def close_panel(self) -> None:
        self._hide_quick_format()
        if self.animating or not self.is_open:
            return
        self._hide_code_copy_btn()
        self._hide_tooltip()
        self._save_note(False)
        self.is_open = False

        def done() -> None:
            self.explorer.withdraw()
            self.root.withdraw()
            self._raise_nav_bar()
            self._refresh_nav_bar_visual()

        self._animate_layout(False, callback=done)

    def toggle_panel(self) -> None:
        if self.animating:
            self._cancel_layout_animation()
            self._place_layout(self.is_open)
            self._raise_nav_bar()
        if self.is_open:
            self.close_panel()
        else:
            self.open_panel()

    def _setup_nav_bar(self) -> None:
        self.nav = tk.Toplevel(self.root)
        self.nav.overrideredirect(True)
        self.nav.attributes("-topmost", True)
        self.nav.attributes("-alpha", self._nav_idle_alpha())
        self.nav.configure(bg=globals()["ACCENT"])
        self.nav_canvas = tk.Canvas(
            self.nav,
            highlightthickness=0,
            bd=0,
            bg=globals()["ACCENT"],
            cursor="hand2",
        )
        self.nav_canvas.pack(fill="both", expand=True)
        self._bind_nav_bar_events()
        self.nav.bind("<Configure>", lambda _event: self._refresh_nav_bar_visual(), add="+")

    def _apply_content_opacity(self, alpha: float) -> None:
        alpha = max(0.30, min(1.0, float(alpha)))
        self.root.attributes("-alpha", alpha)
        if hasattr(self, "explorer"):
            self.explorer.attributes("-alpha", alpha)

    def _on_escape(self) -> None:
        if getattr(self, "quick_format_toolbar", None) is not None and self.quick_format_toolbar.winfo_viewable():
            self._hide_quick_format()
            return
        outline = getattr(self, "_outline_popup", None)
        if outline is not None:
            self._close_outline_popup()
            return
        if hasattr(self, "find_panel") and self.find_panel.winfo_ismapped():
            self._hide_find_panel()
            return
        if self.config.auto_close_on_escape:
            self.close_panel()

    def _on_focus_out(self, _event) -> None:
        if not self.config.auto_close_on_blur or self._settings_open:
            return
        self.root.after(120, lambda: self.close_panel() if self.is_open and not self._pointer_in_app() else None)

    def _pointer_in_app(self) -> bool:
        x, y = self.root.winfo_pointerxy()
        return (
            self._point_in_window(self.root, x, y)
            or self._point_in_window(self.nav, x, y)
            or (self.explorer_visible and self._point_in_window(self.explorer, x, y))
        )

    def _point_in_window(self, window: tk.Toplevel | tk.Tk, x: int, y: int) -> bool:
        if not window.winfo_viewable():
            return False
        wx, wy = window.winfo_rootx(), window.winfo_rooty()
        return wx <= x <= wx + window.winfo_width() and wy <= y <= wy + window.winfo_height()
