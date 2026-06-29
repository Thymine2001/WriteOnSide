from __future__ import annotations

import tkinter as tk

from ..frontmatter import split_front_matter
from ..theme import *  # noqa: F401,F403


def frontmatter_prefix_line_count(content: str) -> int:
    header, body = split_front_matter(content)
    if header is None:
        return 0
    return content[: len(content) - len(body)].count("\n")


def body_display_line_number(line: int, frontmatter_lines: int) -> int | None:
    value = int(line) - max(0, int(frontmatter_lines))
    return value if value >= 1 else None


def line_number_center_y(
    line_info: tuple[int, int, int, int, int],
    *,
    single_line_height: int | None = None,
) -> int:
    y = int(line_info[1])
    block_height = max(1, int(line_info[3]))
    if single_line_height is None or single_line_height >= block_height:
        return y + max(1, block_height // 2)
    return y + max(1, single_line_height // 2)


class EditorStructureMixin:
    def _setup_editor_structure(self) -> None:
        self._folded_heading_keys: set[tuple[int, str, int]] = set()
        self._fold_tags: set[str] = set()
        self._editor_structure_after: str | None = None
        self._fold_layout_dirty = True
        self._sticky_heading_rows: list[tk.Frame] = []
        self.line_number_canvas.bind("<Button-1>", self._on_line_number_click)
        self.line_number_canvas.bind("<MouseWheel>", self._forward_gutter_wheel)
        self.text.bind(
            "<Configure>",
            lambda _event: (self._schedule_editor_structure_refresh(), self._schedule_editor_image_width_refresh()),
            add="+",
        )
        self.text.bind(
            "<KeyRelease>",
            lambda _event: self._schedule_editor_structure_refresh(reapply_folds=True),
            add="+",
        )
        self.text.bind("<ButtonRelease-1>", lambda _event: self._schedule_editor_structure_refresh(), add="+")
        self._schedule_editor_structure_refresh()

    def _forward_gutter_wheel(self, event) -> str:
        self.text.event_generate("<MouseWheel>", delta=event.delta)
        return "break"

    def _on_editor_scroll(self) -> None:
        self._schedule_editor_structure_refresh()
        if getattr(self, "_should_refresh_live_render_on_scroll", lambda: False)():
            self._schedule_live_render()

    def _schedule_editor_structure_refresh(self, reapply_folds: bool = False) -> None:
        if reapply_folds:
            self._fold_layout_dirty = True
        if self._editor_structure_after is not None:
            return
        self._editor_structure_after = self.root.after_idle(self._refresh_editor_structure)

    def _refresh_editor_structure(self) -> None:
        self._editor_structure_after = None
        if not hasattr(self, "line_number_canvas"):
            return
        if self._fold_layout_dirty:
            self._fold_layout_dirty = False
            self._apply_heading_folds()
        self._redraw_line_numbers()
        self._refresh_sticky_headings()

    def _reset_editor_structure(self) -> None:
        self._folded_heading_keys.clear()
        for tag in self._fold_tags:
            try:
                self.text.tag_delete(tag)
            except tk.TclError:
                pass
        self._fold_tags.clear()
        self._schedule_editor_structure_refresh(reapply_folds=True)

    def _heading_key(self, heading: dict[str, int | str]) -> tuple[int, str, int]:
        return (
            int(heading["level"]),
            str(heading["title"]),
            int(heading.get("occurrence", 1)),
        )

    def _heading_sections(self) -> list[dict[str, int | str]]:
        return self._parse_outline() if self._is_markdown_document() else []

    def _apply_heading_folds(self) -> None:
        for tag in self._fold_tags:
            try:
                self.text.tag_delete(tag)
            except tk.TclError:
                pass
        self._fold_tags.clear()
        if not self._folded_heading_keys or not self._is_markdown_document():
            return
        for heading in self._heading_sections():
            if self._heading_key(heading) not in self._folded_heading_keys:
                continue
            line = int(heading["line"])
            end_line = int(heading["end_line"])
            if end_line <= line:
                continue
            tag = f"heading_fold_{line}"
            self.text.tag_configure(tag, elide=True)
            self.text.tag_add(tag, f"{line + 1}.0", f"{end_line}.end+1c")
            self._fold_tags.add(tag)

    def _toggle_heading_fold(self, line: int) -> None:
        heading = next((item for item in self._heading_sections() if int(item["line"]) == line), None)
        if heading is None:
            return
        key = self._heading_key(heading)
        if key in self._folded_heading_keys:
            self._folded_heading_keys.remove(key)
        else:
            self._folded_heading_keys.add(key)
        self._fold_layout_dirty = True
        self._refresh_editor_structure()
        self.text.see(f"{line}.0")

    def _redraw_line_numbers(self) -> None:
        canvas = self.line_number_canvas
        canvas.delete("all")
        if not self.text.winfo_viewable():
            return
        g = globals()
        canvas.configure(bg=g["SURFACE"])
        frontmatter_lines = self._editor_frontmatter_line_offset()
        self._fit_line_number_gutter(frontmatter_lines)
        headings = {int(item["line"]): item for item in self._heading_sections()}
        single_line_height = self._editor_single_line_height()
        top_line = int(self.text.index("@0,0").split(".")[0])
        bottom_line = int(self.text.index(f"@0,{max(1, self.text.winfo_height())}").split(".")[0]) + 1
        for line in range(max(1, top_line - 1), bottom_line + 1):
            info = self.text.dlineinfo(f"{line}.0")
            if not info:
                continue
            y = int(info[1])
            height = int(info[3])
            if height <= 1 or y < 0 or y >= self.text.winfo_height():
                continue
            try:
                visible_line = int(self.text.index(f"@0,{y}").split(".")[0])
            except (ValueError, tk.TclError):
                continue
            if visible_line != line:
                continue
            display_line = body_display_line_number(line, frontmatter_lines)
            if display_line is None:
                continue
            center_y = line_number_center_y(info, single_line_height=single_line_height)
            canvas_width = max(1, canvas.winfo_width())
            canvas.create_text(
                canvas_width - 9,
                center_y,
                anchor="e",
                text=str(display_line),
                fill=g["TEXT_SOFT"],
                font=("Consolas", max(8, self.config.font_size - 1)),
            )
            heading = headings.get(line)
            if heading is not None:
                collapsed = self._heading_key(heading) in self._folded_heading_keys
                marker = "\u25b8" if collapsed else "\u25be"
                canvas.create_text(
                    8,
                    center_y,
                    anchor="w",
                    text=marker,
                    fill=g["ACCENT"] if collapsed else g["TEXT_SOFT"],
                    font=("Segoe UI", 11, "bold"),
                    tags=(f"fold:{line}", "fold_marker"),
                )
        canvas.create_line(
            canvas.winfo_width() - 1,
            0,
            canvas.winfo_width() - 1,
            max(1, canvas.winfo_height()),
            fill=g["BORDER"],
        )

    def _editor_single_line_height(self) -> int:
        try:
            import tkinter.font as tkfont

            font = tkfont.Font(font=self.text.cget("font"))
            spacing1 = int(self.text.cget("spacing1") or 0)
            spacing3 = int(self.text.cget("spacing3") or 0)
            return max(1, font.metrics("linespace") + spacing1 + spacing3)
        except (AttributeError, tk.TclError, TypeError, ValueError):
            return max(12, self.config.font_size + 6)

    def _editor_frontmatter_line_offset(self) -> int:
        try:
            if not self._is_markdown_document():
                return 0
            content = self._get_editor_content()
        except (AttributeError, tk.TclError):
            return 0
        return frontmatter_prefix_line_count(content)

    def _fit_line_number_gutter(self, frontmatter_lines: int | None = None) -> None:
        try:
            total_lines = int(str(self.text.index("end-1c")).split(".")[0])
        except (ValueError, tk.TclError):
            total_lines = 1
        if frontmatter_lines is None:
            frontmatter_lines = self._editor_frontmatter_line_offset()
        body_lines = max(1, total_lines - max(0, int(frontmatter_lines)))
        digits = max(2, len(str(body_lines)))
        font_size = max(8, self.config.font_size - 1)
        try:
            import tkinter.font as tkfont

            font = tkfont.Font(self.line_number_canvas, font=("Consolas", font_size))
            digit_width = max(7, font.measure("0"))
        except (AttributeError, tk.TclError):
            digit_width = 8
        desired = max(52, 18 + digits * digit_width)
        if abs(int(self.line_number_canvas.winfo_width()) - desired) > 1:
            self.line_number_canvas.configure(width=desired)

    def _on_line_number_click(self, event) -> str:
        tags = self.line_number_canvas.gettags("current")
        for tag in tags:
            if tag.startswith("fold:"):
                self._toggle_heading_fold(int(tag.split(":", 1)[1]))
                return "break"
        try:
            line = int(self.text.index(f"@0,{event.y}").split(".")[0])
        except (ValueError, tk.TclError):
            return "break"
        self.text.mark_set(tk.INSERT, f"{line}.0")
        self.text.focus_set()
        return "break"

    def _active_heading_stack(self) -> list[dict[str, int | str]]:
        if not self._is_markdown_document():
            return []
        top_line = int(self.text.index("@0,0").split(".")[0])
        return self._cached_active_heading_stack(top_line)

    def _sticky_heading_stack(self) -> list[dict[str, int | str]]:
        sticky: list[dict[str, int | str]] = []
        for heading in self._active_heading_stack():
            try:
                info = self.text.dlineinfo(f"{int(heading['line'])}.0")
            except (ValueError, tk.TclError):
                info = None
            if info is None or int(info[1]) < 0:
                sticky.append(heading)
        return sticky

    def _refresh_sticky_headings(self) -> None:
        for row in self._sticky_heading_rows:
            row.destroy()
        self._sticky_heading_rows.clear()
        stack = self._sticky_heading_stack()
        if not stack:
            self.sticky_heading_frame.place_forget()
            return
        g = globals()
        self.sticky_heading_frame.configure(bg=g["SURFACE_2"])
        self.sticky_heading_frame.place(
            x=self.line_number_canvas.winfo_width(),
            y=0,
            relwidth=1.0,
            width=-self.line_number_canvas.winfo_width() - 12,
        )
        for heading in stack:
            line = int(heading["line"])
            level = int(heading["level"])
            title = str(heading["title"])
            collapsed = self._heading_key(heading) in self._folded_heading_keys
            row = tk.Frame(self.sticky_heading_frame, bg=g["SURFACE_2"], height=25)
            row.pack(fill="x")
            row.pack_propagate(False)
            marker = tk.Label(
                row,
                text="\u25b8" if collapsed else "\u25be",
                bg=g["SURFACE_2"],
                fg=g["ACCENT"] if collapsed else g["MUTED"],
                font=("Segoe UI", 10, "bold"),
                width=2,
                cursor="hand2",
            )
            marker.pack(side="left", padx=(3 + (level - 1) * 9, 0))
            label = tk.Label(
                row,
                text=title,
                bg=g["SURFACE_2"],
                fg=g["TEXT"] if level <= 2 else g["TEXT_SOFT"],
                font=(self.config.font_family, max(9, self.config.font_size), "bold"),
                anchor="w",
                cursor="hand2",
            )
            label.pack(side="left", fill="x", expand=True)
            marker.bind("<Button-1>", lambda _event, target=line: self._toggle_heading_fold(target))
            label.bind("<Button-1>", lambda _event, target=line: self._jump_to_sticky_heading(target))
            self._sticky_heading_rows.append(row)
        self.sticky_heading_frame.lift()

    def _jump_to_sticky_heading(self, line: int) -> None:
        self.text.mark_set(tk.INSERT, f"{line}.0")
        self.text.see(f"{line}.0")
        self.text.focus_set()
        self._schedule_editor_structure_refresh()
