from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence

from ..config import APP_NAME
from ..i18n import t
from ..theme import *  # noqa: F401,F403


class DialogMixin:
    """Application-themed modal dialogs used instead of legacy Tk message boxes."""

    def _dialog_window(
        self,
        title: str,
        message: str,
        *,
        parent: tk.Misc | None = None,
        height: int = 196,
    ) -> tuple[tk.Toplevel, tk.Frame, tk.Misc]:
        g = globals()
        owner = parent or self.root
        win = tk.Toplevel(owner)
        win.withdraw()
        win.title(title)
        win.configure(bg=g["BG"])
        win.transient(owner)
        win.attributes("-topmost", True)
        win.resizable(False, False)

        width = 410
        try:
            owner.update_idletasks()
            x = owner.winfo_rootx() + max(0, (owner.winfo_width() - width) // 2)
            y = owner.winfo_rooty() + max(0, (owner.winfo_height() - height) // 2)
        except tk.TclError:
            x = self.work_left + max(0, (self.work_right - self.work_left - width) // 2)
            y = self.work_top + max(0, (self.work_bottom - self.work_top - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

        shell = tk.Frame(win, bg=g["BG"], padx=18, pady=16)
        shell.pack(fill="both", expand=True)
        tk.Label(
            shell,
            text=title,
            bg=g["BG"],
            fg=g["TEXT"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            shell,
            text=message,
            bg=g["BG"],
            fg=g["TEXT_SOFT"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=370,
        ).pack(fill="x", pady=(5, 12))
        return win, shell, owner

    def _dialog_button(
        self,
        parent: tk.Misc,
        text: str,
        command,
        *,
        role: str = "normal",
    ) -> tk.Label:
        g = globals()
        if role == "primary":
            background, foreground = g["ACCENT"], self._contrast_text(g["ACCENT"])
        elif role == "danger":
            background, foreground = g["DANGER"], self._contrast_text(g["DANGER"])
        else:
            background, foreground = g["SURFACE"], g["TEXT_SOFT"]
        button = tk.Label(
            parent,
            text=text,
            bg=background,
            fg=foreground,
            font=("Segoe UI", 10, "bold" if role != "normal" else "normal"),
            padx=15,
            pady=7,
            cursor="hand2",
        )
        button._normal_bg = background
        button._normal_fg = foreground
        button.bind("<Button-1>", lambda _event: command())
        button.bind("<Enter>", lambda _event: button.configure(bg=globals()["BORDER"], fg=globals()["TEXT"]))
        button.bind(
            "<Leave>",
            lambda _event: button.configure(bg=button._normal_bg, fg=button._normal_fg),
        )
        return button

    @staticmethod
    def _close_dialog(win: tk.Toplevel) -> None:
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    def _show_dialog_and_wait(self, win: tk.Toplevel, owner: tk.Misc, focus: tk.Misc) -> None:
        win.update_idletasks()
        win.deiconify()
        win.lift(owner)
        win.grab_set()
        focus.focus_set()
        owner.wait_window(win)

    def _ask_text_dialog(
        self,
        title: str,
        prompt: str,
        initial_value: str = "",
        *,
        confirm_text: str | None = None,
        parent: tk.Misc | None = None,
    ) -> str | None:
        g = globals()
        win, shell, owner = self._dialog_window(title, prompt, parent=parent, height=188)
        entry_wrap = tk.Frame(shell, bg=g["ACCENT"], padx=1, pady=1)
        entry_wrap.pack(fill="x")
        entry = tk.Entry(
            entry_wrap,
            bg=g["SURFACE"],
            fg=g["TEXT"],
            insertbackground=g["TEXT"],
            selectbackground=g["ACCENT"],
            selectforeground=self._contrast_text(g["ACCENT"]),
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 11),
        )
        entry.insert(0, initial_value)
        entry.pack(fill="x", ipady=7)
        entry.selection_range(0, tk.END)

        result: dict[str, str | None] = {"value": None}
        actions = tk.Frame(shell, bg=g["BG"])
        actions.pack(fill="x", pady=(16, 0))

        def close(value: str | None) -> None:
            result["value"] = value
            self._close_dialog(win)

        def submit(_event=None) -> str:
            value = entry.get().strip()
            if value:
                close(value)
            else:
                entry.focus_set()
            return "break"

        confirm = self._dialog_button(
            actions,
            confirm_text or t("dialog.create"),
            submit,
            role="primary",
        )
        cancel = self._dialog_button(actions, t("dialog.cancel"), lambda: close(None))
        confirm.pack(side="right")
        cancel.pack(side="right", padx=(0, 8))
        entry.bind("<Return>", submit)
        entry.bind("<Escape>", lambda _event: close(None) or "break")
        win.protocol("WM_DELETE_WINDOW", lambda: close(None))
        self._show_dialog_and_wait(win, owner, entry)
        return result["value"]

    def _ask_choice_dialog(
        self,
        title: str,
        message: str,
        choices: Sequence[tuple[object, str, str]],
        *,
        parent: tk.Misc | None = None,
    ) -> object:
        g = globals()
        height = 176 if len(message) < 100 else 196
        win, shell, owner = self._dialog_window(title, message, parent=parent, height=height)
        result: dict[str, object] = {"value": None}
        actions = tk.Frame(shell, bg=g["BG"])
        actions.pack(side="bottom", fill="x", pady=(10, 0))

        def choose(value: object) -> None:
            result["value"] = value
            self._close_dialog(win)

        first_button: tk.Label | None = None
        for value, label, role in choices:
            button = self._dialog_button(actions, label, lambda item=value: choose(item), role=role)
            button.pack(side="right", padx=(8, 0))
            if first_button is None:
                first_button = button
        win.bind("<Escape>", lambda _event: choose(None) or "break")
        win.protocol("WM_DELETE_WINDOW", lambda: choose(None))
        self._show_dialog_and_wait(win, owner, first_button or win)
        return result["value"]

    def _ask_confirmation_dialog(
        self,
        message: str,
        *,
        title: str = APP_NAME,
        confirm_text: str | None = None,
        danger: bool = False,
        parent: tk.Misc | None = None,
    ) -> bool:
        return self._ask_choice_dialog(
            title,
            message,
            (
                (True, confirm_text or t("dialog.ok"), "danger" if danger else "primary"),
                (False, t("dialog.cancel"), "normal"),
            ),
            parent=parent,
        ) is True

    def _show_message_dialog(
        self,
        message: str,
        *,
        title: str = APP_NAME,
        danger: bool = False,
        parent: tk.Misc | None = None,
    ) -> None:
        self._ask_choice_dialog(
            title,
            message,
            ((True, t("dialog.ok"), "danger" if danger else "primary"),),
            parent=parent,
        )

    def _ask_save_discard_dialog(self, message: str, *, parent: tk.Misc | None = None) -> str | None:
        value = self._ask_choice_dialog(
            APP_NAME,
            message,
            (
                ("save", t("dialog.save"), "primary"),
                ("discard", t("dialog.discard"), "normal"),
                (None, t("dialog.cancel"), "normal"),
            ),
            parent=parent,
        )
        return value if value in {"save", "discard"} else None
