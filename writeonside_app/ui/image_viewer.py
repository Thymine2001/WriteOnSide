from __future__ import annotations

import math
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk

from ..image_safety import ImageTooLargeError, open_image_checked
from ..i18n import t
from ..theme import *  # noqa: F401,F403


class ImageViewerMixin:
    def _on_read_image_click(self, event) -> str | None:
        images = getattr(self.read_text, "_clickable_images", {})
        if not images:
            return None
        try:
            index = self.read_text.index(f"@{event.x},{event.y}")
            image_name = str(self.read_text.image_cget(index, "image"))
        except tk.TclError:
            return None
        path = images.get(image_name)
        if path:
            self._open_external_file(Path(path))
            return "break"
        return None

    def _open_image_viewer(self, path: Path) -> None:
        try:
            original = open_image_checked(path).convert("RGBA")
        except (OSError, ValueError, ImageTooLargeError) as exc:
            self._set_error(t("error.image_preview_failed", exc=exc))
            return

        existing = getattr(self, "_image_viewer_window", None)
        if existing is not None:
            try:
                existing.destroy()
            except tk.TclError:
                pass

        g = globals()
        win = tk.Toplevel(self.root)
        win.title(path.name)
        win.configure(bg=g["BG"])
        win.attributes("-topmost", True)
        work_width = max(420, self.work_right - self.work_left)
        work_height = max(320, self.work_bottom - self.work_top)
        width = min(1100, max(620, work_width - 80))
        height = min(820, max(460, work_height - 80))
        x = self.work_left + max(0, (work_width - width) // 2)
        y = self.work_top + max(0, (work_height - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.minsize(420, 320)

        toolbar = tk.Frame(win, bg=g["SURFACE"], height=42)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        title = tk.Label(
            toolbar,
            text=path.name,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        title.pack(side="left", fill="x", expand=True, padx=(12, 8))
        zoom_label = tk.Label(
            toolbar,
            text="100%",
            bg=g["SURFACE"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            width=7,
        )
        zoom_label.pack(side="right", padx=(2, 10))

        canvas_shell = tk.Frame(win, bg=g["BG"])
        canvas_shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(
            canvas_shell,
            bg=g["BG"],
            highlightthickness=0,
            borderwidth=0,
            xscrollincrement=1,
            yscrollincrement=1,
        )
        x_scroll = tk.Scrollbar(canvas_shell, orient="horizontal", command=canvas.xview)
        y_scroll = tk.Scrollbar(canvas_shell, orient="vertical", command=canvas.yview)
        canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        canvas_shell.grid_rowconfigure(0, weight=1)
        canvas_shell.grid_columnconfigure(0, weight=1)

        state = {
            "path": path,
            "original": original,
            "scale": 1.0,
            "photo": None,
            "image_id": None,
            "fit": True,
        }

        def render(scale: float, center: bool = True) -> None:
            source: Image.Image = state["original"]
            pixel_limit_scale = math.sqrt(40_000_000 / max(1, source.width * source.height))
            scale = max(0.05, min(8.0, pixel_limit_scale, float(scale)))
            state["scale"] = scale
            target = (
                max(1, round(source.width * scale)),
                max(1, round(source.height * scale)),
            )
            resized = source.resize(target, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized)
            state["photo"] = photo
            canvas.delete("all")
            canvas_width = max(1, canvas.winfo_width())
            canvas_height = max(1, canvas.winfo_height())
            content_width = max(canvas_width, target[0])
            content_height = max(canvas_height, target[1])
            x = content_width // 2
            y = content_height // 2
            state["image_id"] = canvas.create_image(x, y, image=photo, anchor="center")
            canvas.configure(scrollregion=(0, 0, content_width, content_height))
            zoom_label.configure(text=f"{round(scale * 100)}%")
            if center:
                canvas.xview_moveto(max(0.0, (content_width - canvas_width) / 2 / content_width))
                canvas.yview_moveto(max(0.0, (content_height - canvas_height) / 2 / content_height))

        def fit_image(_event=None) -> str:
            canvas.update_idletasks()
            available_width = max(80, canvas.winfo_width() - 24)
            available_height = max(80, canvas.winfo_height() - 24)
            source: Image.Image = state["original"]
            scale = min(1.0, available_width / source.width, available_height / source.height)
            state["fit"] = True
            render(scale)
            return "break"

        def actual_size(_event=None) -> str:
            state["fit"] = False
            render(1.0)
            return "break"

        def zoom_by(factor: float) -> str:
            state["fit"] = False
            render(float(state["scale"]) * factor)
            return "break"

        def control_wheel(event) -> str:
            return zoom_by(1.12 if event.delta > 0 else 1 / 1.12)

        def viewer_button(text: str, tooltip: str, command) -> tk.Label:
            button = tk.Label(
                toolbar,
                text=text,
                bg=g["SURFACE"],
                fg=g["TEXT_SOFT"],
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                padx=9,
                pady=4,
            )
            button.pack(side="right", padx=1, pady=6)
            button.bind("<Button-1>", lambda _event: command())
            button.bind(
                "<Enter>",
                lambda _event: (
                    button.configure(bg=globals()["SURFACE_2"], fg=globals()["TEXT"]),
                    self._show_tooltip(button, tooltip),
                ),
            )
            button.bind(
                "<Leave>",
                lambda _event: (
                    button.configure(bg=globals()["SURFACE"], fg=globals()["TEXT_SOFT"]),
                    self._hide_tooltip(),
                ),
            )
            return button

        viewer_button("1:1", "Actual size", actual_size)
        viewer_button("Fit", "Fit image to window", fit_image)
        viewer_button("+", "Zoom in", lambda: zoom_by(1.2))
        viewer_button("-", "Zoom out", lambda: zoom_by(1 / 1.2))

        canvas.bind("<Control-MouseWheel>", control_wheel)
        win.bind("<Control-plus>", lambda _event: zoom_by(1.2))
        win.bind("<Control-equal>", lambda _event: zoom_by(1.2))
        win.bind("<Control-minus>", lambda _event: zoom_by(1 / 1.2))
        win.bind("<Control-0>", actual_size)
        win.bind("<Escape>", lambda _event: win.destroy())
        canvas.bind("<ButtonPress-1>", lambda event: canvas.scan_mark(event.x, event.y))
        canvas.bind("<B1-Motion>", lambda event: canvas.scan_dragto(event.x, event.y, gain=1))

        resize_after = None

        def on_resize(_event=None) -> None:
            nonlocal resize_after
            if not state["fit"]:
                return
            if resize_after is not None:
                try:
                    win.after_cancel(resize_after)
                except tk.TclError:
                    pass
            resize_after = win.after(80, fit_image)

        canvas.bind("<Configure>", on_resize)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self._image_viewer_window = win
        win.after_idle(fit_image)
