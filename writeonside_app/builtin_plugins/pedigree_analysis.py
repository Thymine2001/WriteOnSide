from __future__ import annotations

import csv
import importlib
import math
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from ..i18n import t
from ..storage import safe_write_text
from ..theme import *  # noqa: F401,F403


MISSING_OPTION = "(none)"
DETAIL_INLINE_LIMIT = 20


def run(app) -> None:
    PedigreeAnalysisWindow(app).open()


class PedigreeAnalysisWindow:
    def __init__(self, app) -> None:
        self.app = app
        self.path: Path | None = None
        self.headers: list[str] = []
        self.rows: list[dict[str, str]] = []
        self.delimiter = ","

    def open(self) -> None:
        app = self.app
        if getattr(app, "_pedigree_plugin_open", False):
            return
        app._pedigree_plugin_open = True
        g = globals()
        win = tk.Toplevel(app.root)
        win.withdraw()
        win.title(t("pedigree.window_title"))
        work_width = max(420, app.work_right - app.work_left)
        work_height = max(360, app.work_bottom - app.work_top)
        width = min(780, max(520, work_width - 72))
        height = min(640, max(460, work_height - 96))
        x = app.work_left + max(0, (work_width - width) // 2)
        y = app.work_top + max(0, (work_height - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.minsize(520, 460)
        win.configure(bg=g["BG"])
        win.resizable(True, True)

        footer = tk.Frame(win, bg=g["BG"])
        footer.pack(fill="x", side="bottom", padx=22, pady=(8, 12))
        status = tk.Label(
            footer,
            text=t("pedigree.footer_hint"),
            bg=g["BG"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        status.pack(side="left", fill="x", expand=True, padx=(0, 14))

        content = tk.Frame(win, bg=g["BG"])
        content.pack(fill="both", expand=True, padx=22, pady=(18, 8))

        hero = tk.Frame(content, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"], padx=18, pady=14)
        hero.pack(fill="x", pady=(0, 14))
        icon = tk.Label(hero, text="🧬", bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI Emoji", 28), width=3)
        icon.pack(side="left", padx=(0, 12))
        hero_text = tk.Frame(hero, bg=g["SURFACE"])
        hero_text.pack(side="left", fill="x", expand=True)
        title = tk.Label(hero_text, text=t("pedigree.title"), bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI", 15, "bold"), anchor="w")
        title.pack(fill="x")
        subtitle = tk.Label(
            hero_text,
            text=t("pedigree.footer_hint"),
            bg=g["SURFACE"],
            fg=g["MUTED"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        subtitle.pack(fill="x", pady=(4, 0))

        file_card = tk.Frame(content, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"], padx=14, pady=12)
        file_card.pack(fill="x", pady=(0, 12))
        file_header = tk.Frame(file_card, bg=g["SURFACE"])
        file_header.pack(fill="x")
        file_title = tk.Label(file_header, text=t("pedigree.choose_file"), bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI", 10, "bold"), anchor="w")
        file_title.pack(side="left")
        file_label = tk.Label(file_card, text=t("pedigree.no_file"), bg=g["SURFACE"], fg=g["MUTED"], font=("Segoe UI", 9), anchor="w", justify="left")
        file_label.pack(fill="x", pady=(8, 0))

        form_card = tk.Frame(content, bg=g["SURFACE"], highlightthickness=1, highlightbackground=g["BORDER"], padx=14, pady=12)
        form_card.pack(fill="x", pady=(0, 12))
        form_title = tk.Label(form_card, text=t("pedigree.columns_title"), bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI", 10, "bold"), anchor="w")
        form_title.pack(fill="x", pady=(0, 8))
        form = tk.Frame(form_card, bg=g["SURFACE"])
        form.pack(fill="x")
        variables = {
            "progeny": tk.StringVar(value=""),
            "sire": tk.StringVar(value=""),
            "dam": tk.StringVar(value=""),
            "group": tk.StringVar(value=MISSING_OPTION),
            "sex": tk.StringVar(value=MISSING_OPTION),
            "birthdate": tk.StringVar(value=MISSING_OPTION),
        }
        menus: dict[str, tk.OptionMenu] = {}
        running = {"value": False}
        current_progress: dict[str, object | None] = {"state": None}

        def build_row(index: int, key: str, label_key: str, required: bool = False) -> None:
            label = tk.Label(form, text=t(label_key), bg=g["SURFACE"], fg=g["TEXT"], font=("Segoe UI", 10), anchor="w")
            label.grid(row=index, column=0, sticky="w", pady=5)
            menu = tk.OptionMenu(form, variables[key], MISSING_OPTION)
            menu.configure(
                bg=g["SURFACE_2"],
                fg=g["TEXT"],
                activebackground=g["BORDER"],
                activeforeground=g["TEXT"],
                relief="flat",
                highlightthickness=1,
                highlightbackground=g["BORDER"],
                anchor="w",
            )
            menu.grid(row=index, column=1, sticky="ew", padx=(12, 0), pady=5)
            try:
                menu["menu"].configure(bg=g["SURFACE"], fg=g["TEXT"], activebackground=g["ACCENT"], activeforeground=app._contrast_text(g["ACCENT"]))
            except tk.TclError:
                pass
            if required:
                required_label = tk.Label(form, text="*", bg=g["SURFACE"], fg=g["DANGER"], font=("Segoe UI", 10, "bold"))
                required_label.grid(row=index, column=2, sticky="w", padx=(5, 0))
            menus[key] = menu

        form.grid_columnconfigure(1, weight=1)
        build_row(0, "progeny", "pedigree.column.progeny", True)
        build_row(1, "sire", "pedigree.column.sire", True)
        build_row(2, "dam", "pedigree.column.dam", True)
        build_row(3, "group", "pedigree.column.group")
        build_row(4, "sex", "pedigree.column.sex")
        build_row(5, "birthdate", "pedigree.column.birthdate")

        def close() -> None:
            app._pedigree_plugin_open = False
            if getattr(app, "_refresh_pedigree_plugin_theme", None) is refresh_theme:
                try:
                    delattr(app, "_refresh_pedigree_plugin_theme")
                except AttributeError:
                    pass
            try:
                win.destroy()
            except tk.TclError:
                pass

        def set_status(message: str, danger: bool = False, muted: bool = False) -> None:
            status.configure(text=message, fg=globals()["DANGER"] if danger else (globals()["MUTED"] if muted else globals()["TEXT"]))

        def set_busy(is_busy: bool) -> None:
            running["value"] = is_busy
            state = "disabled" if is_busy else "normal"
            browse_btn.configure(state=state)
            analyze_btn.configure(state=state)
            for menu in menus.values():
                menu.configure(state=state)

        def set_menu_values(key: str, values: list[str], default: str) -> None:
            menu = menus[key]["menu"]
            menu.delete(0, "end")
            choices = values if key in {"progeny", "sire", "dam"} else [MISSING_OPTION, *values]
            for choice in choices:
                menu.add_command(label=choice, command=lambda value=choice, var=variables[key]: var.set(value))
            variables[key].set(default if default in choices else choices[0])

        def guess(name_options: list[str], *names: str, optional: bool = False) -> str:
            lowered = {name.casefold(): name for name in name_options}
            for name in names:
                if name.casefold() in lowered:
                    return lowered[name.casefold()]
            return MISSING_OPTION if optional else (name_options[0] if name_options else "")

        def choose_file() -> None:
            if running["value"]:
                return
            selected = filedialog.askopenfilename(
                parent=win,
                title=t("pedigree.choose_file"),
                filetypes=[
                    (t("pedigree.filetypes"), "*.csv *.tsv *.txt"),
                    (t("dialog.all_files"), "*.*"),
                ],
            )
            if not selected:
                return
            try:
                self.path = Path(selected)
                self.headers, self.rows, self.delimiter = read_table(self.path)
            except Exception as exc:
                set_status(t("pedigree.error.read_failed", exc=exc), True)
                return
            file_label.configure(text=str(self.path))
            headers = list(self.headers)
            set_menu_values("progeny", headers, guess(headers, "progeny", "id", "animal", "individual"))
            set_menu_values("sire", headers, guess(headers, "sire", "father", "dad"))
            set_menu_values("dam", headers, guess(headers, "dam", "mother", "mom"))
            set_menu_values("group", headers, guess(headers, "group", "population", "line", optional=True))
            set_menu_values("sex", headers, guess(headers, "sex", "gender", optional=True))
            set_menu_values("birthdate", headers, guess(headers, "birthdate", "birth_date", "dob", optional=True))
            set_status(t("pedigree.loaded", rows=len(self.rows), columns=len(headers)))

        def open_progress_dialog() -> dict[str, object]:
            dialog = tk.Toplevel(win)
            dialog.withdraw()
            try:
                dialog.attributes("-alpha", 0.0)
            except tk.TclError:
                pass
            dialog.title(t("pedigree.progress.title"))
            dialog.overrideredirect(True)
            dialog_w = 400
            dialog_h = 172
            dialog_x = win.winfo_rootx() + max(0, (win.winfo_width() - dialog_w) // 2)
            dialog_y = win.winfo_rooty() + max(0, (win.winfo_height() - dialog_h) // 2)
            dialog.geometry(f"{dialog_w}x{dialog_h}+{dialog_x}+{dialog_y}")
            dialog.resizable(False, False)
            dialog.transient(win)
            dialog.configure(bg=globals()["BG"])

            bg = globals()["SURFACE"]
            text = globals()["TEXT"]
            muted = globals()["MUTED"]
            border = globals()["BORDER"]
            is_dark = str(globals()["BG"]).lower() not in {"#ffffff", "#f7f7f7", "#f8f9fa", "#fafafa"}
            accent = "#5b8fd8" if is_dark else "#6aa6e8"
            style = ttk.Style(dialog)
            style.configure("PedigreeProgress.TLabel", background=bg, foreground=text, font=("Segoe UI", 10))
            style.configure("PedigreeProgressMuted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
            style.configure(
                "Pedigree.Horizontal.TProgressbar",
                troughcolor=border,
                background=accent,
                lightcolor=accent,
                darkcolor=accent,
                bordercolor=border,
                thickness=8,
            )

            shell = tk.Frame(dialog, bg=globals()["SURFACE"], highlightthickness=1, highlightbackground=globals()["BORDER"], padx=16, pady=14)
            shell.pack(fill="both", expand=True, padx=14, pady=14)
            title_bar = tk.Frame(shell, bg=bg)
            title_bar.pack(fill="x")
            title_label = ttk.Label(
                title_bar,
                text=t("pedigree.progress.title"),
                style="PedigreeProgress.TLabel",
                anchor="w",
            )
            title_label.pack(side="left", fill="x", expand=True)
            close_btn = tk.Button(
                title_bar,
                text="×",
                bg=bg,
                fg=muted,
                activebackground=border,
                activeforeground=text,
                relief="flat",
                borderwidth=0,
                width=3,
                cursor="hand2",
            )
            close_btn.pack(side="right")
            status_row = tk.Frame(shell, bg=bg)
            status_row.pack(fill="x", pady=(8, 10))
            label = ttk.Label(
                status_row,
                text=t("pedigree.progress.running"),
                style="PedigreeProgressMuted.TLabel",
                anchor="w",
            )
            label.pack(side="left", fill="x", expand=True)
            percent = ttk.Label(status_row, text="0%", style="PedigreeProgressMuted.TLabel", anchor="e", width=5)
            percent.pack(side="right")
            progress_value = tk.DoubleVar(value=0)
            bar = ttk.Progressbar(
                shell,
                variable=progress_value,
                maximum=100,
                mode="determinate",
                style="Pedigree.Horizontal.TProgressbar",
            )
            bar.pack(fill="x", pady=(0, 12))
            done_btn = tk.Button(
                shell,
                text=t("pedigree.progress.done"),
                state="disabled",
                bg=globals()["BORDER"],
                fg=globals()["TEXT"],
                relief="flat",
                padx=14,
                pady=5,
            )
            done_btn.pack(side="right")
            state: dict[str, object] = {
                "dialog": dialog,
                "shell": shell,
                "title_bar": title_bar,
                "title_label": title_label,
                "close_btn": close_btn,
                "label": label,
                "bar": bar,
                "value": progress_value,
                "percent": percent,
                "done_btn": done_btn,
                "cancelled": False,
                "completed": False,
            }
            current_progress["state"] = state

            def cancel() -> None:
                if state["completed"]:
                    return
                state["cancelled"] = True
                current_progress["state"] = None
                try:
                    dialog.destroy()
                except tk.TclError:
                    pass
                set_busy(False)
                set_status(t("pedigree.progress.cancelled"), muted=True)

            close_btn.configure(command=cancel)
            dialog.protocol("WM_DELETE_WINDOW", cancel)
            dialog.bind("<Escape>", lambda _event: cancel())
            dialog.update_idletasks()
            try:
                dialog.attributes("-alpha", 1.0)
            except tk.TclError:
                pass
            dialog.deiconify()
            try:
                dialog.attributes("-topmost", True)
                dialog.lift()
                dialog.after(120, lambda: dialog.attributes("-topmost", False))
            except tk.TclError:
                dialog.lift(win)
            return state

        def analyze() -> None:
            if running["value"]:
                return
            if self.path is None:
                set_status(t("pedigree.error.no_file"), True)
                return
            selected = {key: var.get() for key, var in variables.items()}
            if not selected["progeny"] or not selected["sire"] or not selected["dam"]:
                set_status(t("pedigree.error.required_columns"), True)
                return
            start_time = time.monotonic()
            worker_state: dict[str, object] = {"done": False, "report": None, "error": None}
            set_busy(True)
            set_status(t("pedigree.progress.running"), muted=True)
            win.update_idletasks()
            progress = open_progress_dialog()

            def worker() -> None:
                try:
                    result = run_rust_analysis(self.rows, selected)
                    if progress["cancelled"]:
                        return
                    worker_state["report"] = write_report(app, self.path, selected, result)
                except Exception as exc:
                    worker_state["error"] = exc
                finally:
                    worker_state["done"] = True

            def tick() -> None:
                if not win.winfo_exists():
                    return
                if progress["cancelled"]:
                    return
                elapsed = time.monotonic() - start_time
                minimum_progress = min(0.95, elapsed / 3.0 * 0.95)
                value = 1.0 if worker_state["done"] and elapsed >= 3.0 else minimum_progress
                try:
                    progress["value"].set(value * 100)
                    progress["percent"].configure(text=f"{round(value * 100)}%")
                except tk.TclError:
                    progress["cancelled"] = True
                    set_busy(False)
                    set_status(t("pedigree.progress.cancelled"), muted=True)
                    return
                if not worker_state["done"] or elapsed < 3.0:
                    win.after(50, tick)
                    return
                set_busy(False)
                if worker_state["error"] is not None:
                    set_status(t("pedigree.error.analysis_failed", exc=worker_state["error"]), True)
                    def close_progress_dialog() -> None:
                        current_progress["state"] = None
                        progress["dialog"].destroy()
                    try:
                        progress["label"].configure(text=t("pedigree.error.analysis_failed", exc=worker_state["error"]))
                        progress["done_btn"].configure(state="normal", text=t("pedigree.progress.done"), command=close_progress_dialog)
                    except tk.TclError:
                        pass
                    return
                report = worker_state["report"]
                set_status(t("pedigree.report_written", path=report))
                progress["completed"] = True

                def finish() -> None:
                    try:
                        current_progress["state"] = None
                        progress["dialog"].destroy()
                    except tk.TclError:
                        pass
                    if hasattr(app, "_open_file_in_editor") and report is not None:
                        app._open_file_in_editor(report, reveal_panel=True, prefer_split=False)

                try:
                    progress["label"].configure(text=t("pedigree.progress.complete"))
                    progress["done_btn"].configure(state="normal", text=t("pedigree.progress.done"), command=finish)
                    progress["dialog"].protocol("WM_DELETE_WINDOW", finish)
                except tk.TclError:
                    finish()

            threading.Thread(target=worker, daemon=True).start()
            tick()

        browse_btn = tk.Button(
            file_header,
            text=t("pedigree.choose_file"),
            command=choose_file,
            bg=g["BORDER"],
            fg=g["TEXT"],
            activebackground=g["SURFACE_2"],
            activeforeground=g["TEXT"],
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        )
        browse_btn.pack(side="right")
        analyze_btn = tk.Button(
            footer,
            text=t("pedigree.analyze"),
            command=analyze,
            bg=g["ACCENT"],
            fg=app._contrast_text(g["ACCENT"]),
            activebackground=g["ACCENT_2"],
            activeforeground=app._contrast_text(g["ACCENT_2"]),
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
        )
        analyze_btn.pack(side="right")

        def refresh_theme() -> None:
            _g = globals()
            try:
                win.configure(bg=_g["BG"])
                footer.configure(bg=_g["BG"])
                status.configure(bg=_g["BG"], fg=_g["MUTED"])
                content.configure(bg=_g["BG"])
                hero.configure(bg=_g["SURFACE"], highlightbackground=_g["BORDER"])
                icon.configure(bg=_g["SURFACE"], fg=_g["TEXT"])
                hero_text.configure(bg=_g["SURFACE"])
                title.configure(bg=_g["SURFACE"], fg=_g["TEXT"])
                subtitle.configure(bg=_g["SURFACE"], fg=_g["MUTED"])
                file_card.configure(bg=_g["SURFACE"], highlightbackground=_g["BORDER"])
                file_header.configure(bg=_g["SURFACE"])
                file_title.configure(bg=_g["SURFACE"], fg=_g["TEXT"])
                file_label.configure(bg=_g["SURFACE"], fg=_g["MUTED"])
                form_card.configure(bg=_g["SURFACE"], highlightbackground=_g["BORDER"])
                form_title.configure(bg=_g["SURFACE"], fg=_g["TEXT"])
                form.configure(bg=_g["SURFACE"])
                browse_btn.configure(
                    bg=_g["BORDER"],
                    fg=_g["TEXT"],
                    activebackground=_g["SURFACE_2"],
                    activeforeground=_g["TEXT"],
                )
                analyze_btn.configure(
                    bg=_g["ACCENT"],
                    fg=app._contrast_text(_g["ACCENT"]),
                    activebackground=_g["ACCENT_2"],
                    activeforeground=app._contrast_text(_g["ACCENT_2"]),
                )
                for widget in form.winfo_children():
                    try:
                        if isinstance(widget, tk.OptionMenu):
                            widget.configure(
                                bg=_g["SURFACE_2"],
                                fg=_g["TEXT"],
                                activebackground=_g["BORDER"],
                                activeforeground=_g["TEXT"],
                                highlightbackground=_g["BORDER"],
                            )
                            widget["menu"].configure(
                                bg=_g["SURFACE"],
                                fg=_g["TEXT"],
                                activebackground=_g["ACCENT"],
                                activeforeground=app._contrast_text(_g["ACCENT"]),
                            )
                        else:
                            widget.configure(bg=_g["SURFACE"])
                            if "foreground" in widget.keys():
                                widget.configure(fg=_g["DANGER"] if widget.cget("text") == "*" else _g["TEXT"])
                    except (tk.TclError, TypeError):
                        pass
                progress_state = current_progress.get("state")
                if progress_state:
                    is_dark = str(_g["BG"]).lower() not in {"#ffffff", "#f7f7f7", "#f8f9fa", "#fafafa"}
                    progress_accent = "#5b8fd8" if is_dark else "#6aa6e8"
                    style = ttk.Style(progress_state["dialog"])
                    style.configure(
                        "PedigreeProgress.TLabel",
                        background=_g["SURFACE"],
                        foreground=_g["TEXT"],
                        font=("Segoe UI", 10),
                    )
                    style.configure(
                        "PedigreeProgressMuted.TLabel",
                        background=_g["SURFACE"],
                        foreground=_g["MUTED"],
                        font=("Segoe UI", 9),
                    )
                    style.configure(
                        "Pedigree.Horizontal.TProgressbar",
                        troughcolor=_g["BORDER"],
                        background=progress_accent,
                        lightcolor=progress_accent,
                        darkcolor=progress_accent,
                        bordercolor=_g["BORDER"],
                        thickness=8,
                    )
                    progress_state["dialog"].configure(bg=_g["BG"])
                    progress_state["shell"].configure(bg=_g["SURFACE"], highlightbackground=_g["BORDER"])
                    progress_state["title_bar"].configure(bg=_g["SURFACE"])
                    progress_state["close_btn"].configure(
                        bg=_g["SURFACE"],
                        fg=_g["MUTED"],
                        activebackground=_g["BORDER"],
                        activeforeground=_g["TEXT"],
                    )
                    progress_state["done_btn"].configure(bg=_g["BORDER"], fg=_g["TEXT"])
            except tk.TclError:
                pass

        app._refresh_pedigree_plugin_theme = refresh_theme
        refresh_theme()

        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _event: close())
        win.update_idletasks()
        win.deiconify()
        win.lift()
        win.focus_force()


def read_table(path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t; |")
        except csv.Error:
            dialect = csv.excel_tab if path.suffix.casefold() == ".tsv" else csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        headers = [str(header or "").strip() for header in (reader.fieldnames or [])]
        if not headers:
            raise ValueError("No header row found.")
        rows = [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
        return headers, rows, dialect.delimiter


def selected_column(rows: list[dict[str, str]], column: str) -> list[str]:
    if column == MISSING_OPTION:
        return [""] * len(rows)
    return [row.get(column, "") for row in rows]


def run_rust_analysis(rows: list[dict[str, str]], selected: dict[str, str]) -> dict:
    try:
        engine = importlib.import_module("writeonside_pedigree")
    except ImportError as exc:
        raise RuntimeError("Rust pedigree engine is not installed. Build it with maturin before using this plugin.") from exc
    return engine.analyze_pedigree(
        selected_column(rows, selected["progeny"]),
        selected_column(rows, selected["sire"]),
        selected_column(rows, selected["dam"]),
        selected_column(rows, selected["group"]) if selected["group"] != MISSING_OPTION else None,
        selected_column(rows, selected["sex"]) if selected["sex"] != MISSING_OPTION else None,
        selected_column(rows, selected["birthdate"]) if selected["birthdate"] != MISSING_OPTION else None,
    )


def output_root(app) -> Path:
    try:
        root = app._workspace_dir()
    except Exception:
        root = Path.home() / "Documents" / "WriteOnSide"
    target = root / "Plugins" / "PedigreeAnalysis"
    (target / "reports").mkdir(parents=True, exist_ok=True)
    (target / "tables").mkdir(parents=True, exist_ok=True)
    return target


def safe_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("_") or "pedigree"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def table_link(section: str, rows: list[dict], tables_dir: Path, report_dir: Path, base: str) -> tuple[str, list[str]]:
    if not rows:
        return "None.", []
    lines = [f"Found {len(rows):,} records."]
    if len(rows) <= DETAIL_INLINE_LIMIT:
        columns = list(rows[0].keys())
        lines.append("")
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
        return "\n".join(lines), []
    csv_path = tables_dir / f"{base}_{section}.csv"
    write_csv(csv_path, rows)
    relative = Path(os.path.relpath(csv_path, report_dir)).as_posix()
    lines.append(f"[Open full table]({relative})")
    return "\n".join(lines), [str(csv_path)]


def as_id_rows(values: list[str], column: str = "id") -> list[dict[str, str]]:
    return [{column: value} for value in values]


def repaired_value(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.casefold() in {"0", "na", "n/a", "none", "null"}:
        return "0"
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def repaired_pedigree_columns(selected: dict[str, str]) -> list[tuple[str, str]]:
    columns = [("Progeny", "id"), ("Sire", "sire"), ("Dam", "dam")]
    if selected.get("group") != MISSING_OPTION:
        columns.append(("Group", "group"))
    if selected.get("sex") != MISSING_OPTION:
        columns.append(("Sex", "sex"))
    if selected.get("birthdate") != MISSING_OPTION:
        columns.append(("BirthDate", "birthdate"))
    return columns


def write_repaired_pedigree_txt(path: Path, records: list[dict], selected: dict[str, str]) -> str:
    columns = repaired_pedigree_columns(selected)
    lines = [" ".join(header for header, _key in columns)]
    for row in records:
        lines.append(" ".join(repaired_value(row.get(key)) for _header, key in columns))
    content = "\n".join(lines) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return content


def repaired_pedigree_section(repaired_path: Path, report_dir: Path) -> str:
    relative = Path(os.path.relpath(repaired_path, report_dir)).as_posix()
    section = [
        "## Repaired Pedigree",
        "### Repair Rules",
        "- Output format: space-delimited `.txt`.",
        "- Missing values are written as `0`.",
        "- Blank, `NA`, `N/A`, `None`, and `null` are normalized to `0`.",
        "- Progeny, Sire, and Dam values are trimmed before output.",
        "- Optional Group, Sex, and BirthDate columns are included only when selected.",
        "- Rows without a valid Progeny ID are excluded from the repaired pedigree.",
        "",
        f"[Open repaired pedigree TXT]({relative})",
        "",
    ]
    return "\n".join(section)


def yaml_quote(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def report_front_matter(input_path: Path, generated_at: str) -> str:
    title = f"Pedigree QC & Inbreeding Report - {input_path.stem}"
    return "\n".join(
        [
            "---",
            f"title: {yaml_quote(title)}",
            f"created: {yaml_quote(generated_at)}",
            "tags: [pedigree, inbreeding, plugin-report]",
            "aliases: []",
            "writeonside_colors: []",
            "writeonside_pinned: false",
            "plugin: pedigree_analysis",
            f"source_file: {yaml_quote(input_path)}",
            "---",
        ]
    )


def finite_inbreeding(row: dict) -> float | None:
    try:
        value = float(row.get("inbreeding", "nan"))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def values_stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"total": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "sd": 0.0}
    mean = sum(values) / len(values)
    if len(values) > 1:
        sd = math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
    else:
        sd = 0.0
    return {
        "total": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean,
        "sd": sd,
    }


def birthdate_bucket(value: object) -> str | None:
    text = str(value or "").strip()
    if not text or text.casefold() in {"0", "na", "n/a", "none", "null"}:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        return digits[:4]
    return text


def trend_bucket(row: dict, prefer_birthdate: bool) -> tuple[str, str]:
    if prefer_birthdate:
        bucket = birthdate_bucket(row.get("birthdate"))
        if bucket:
            return bucket, "BirthDate"
    return str(row.get("lap_depth", 0)), "LAP"


def trend_rows(records: list[dict], prefer_birthdate: bool) -> tuple[str, list[dict[str, object]]]:
    buckets: dict[str, list[float]] = {}
    trend_type = "BirthDate" if prefer_birthdate else "LAP"
    for row in records:
        value = finite_inbreeding(row)
        if value is None:
            continue
        bucket, trend_type = trend_bucket(row, prefer_birthdate)
        buckets.setdefault(bucket, []).append(value)
    if not buckets and prefer_birthdate:
        return trend_rows(records, False)
    output = []
    for bucket in sorted(buckets, key=trend_sort_key):
        stats = values_stats(buckets[bucket])
        output.append(
            {
                "bucket": bucket,
                "n": stats["total"],
                "mean": stats["mean"],
                "sd": stats["sd"],
            }
        )
    return trend_type, output


def trend_sort_key(value: object) -> tuple[int, int | str]:
    text = str(value)
    if text.isdigit():
        return (0, int(text))
    return (1, text)


def ascii_bar(value: float, max_value: float, width: int = 24) -> str:
    if max_value <= 0:
        return ""
    count = max(0, min(width, round((value / max_value) * width)))
    return "#" * count


def trend_chart(records: list[dict], prefer_birthdate: bool) -> str:
    trend_type, rows = trend_rows(records, prefer_birthdate)
    if not rows:
        return "No valid inbreeding values for trend analysis."
    max_mean = max(float(row["mean"]) for row in rows)
    chart_rows = []
    for row in rows:
        mean = float(row["mean"])
        sd = float(row["sd"])
        chart_rows.append(
            {
                trend_type: row["bucket"],
                "n": row["n"],
                "mean": f"{mean:.8f}",
                "sd": f"{sd:.8f}",
                "mean_plot": ascii_bar(mean, max_mean),
            }
        )
    return markdown_table(chart_rows)


def group_analysis(records: list[dict], prefer_birthdate: bool) -> str:
    groups: dict[str, list[dict]] = {}
    for row in records:
        group = str(row.get("group") or "").strip()
        if group:
            groups.setdefault(group, []).append(row)
    if not groups:
        return "No group column selected."

    lines = []
    for group in sorted(groups):
        rows = groups[group]
        values = [value for row in rows if (value := finite_inbreeding(row)) is not None]
        stats = values_stats(values)
        lines.extend(
            [
                f"### Group: {group}",
                f"- Individuals: {len(rows):,}",
                f"- Evaluated individuals: {stats['total']:,}",
                f"- Inbreds: {sum(1 for value in values if value > 0):,}",
                f"- Mean F: {float(stats['mean']):.8f}",
                f"- SD F: {float(stats['sd']):.8f}",
                f"- Min F: {float(stats['min']):.8g}",
                f"- Max F: {float(stats['max']):.8g}",
                "",
                "#### Inbreeding Trend",
                trend_chart(rows, prefer_birthdate),
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def write_report(app, input_path: Path, selected: dict[str, str], result: dict) -> Path:
    root = output_root(app)
    report_dir = root / "reports"
    tables_dir = root / "tables"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{safe_stem(input_path)}_pedigree_report_{timestamp}"
    report_path = report_dir / f"{base}.md"
    generated_at = datetime.now().isoformat(timespec="seconds")
    meta = result["meta"]
    parent_stats = result.get("parent_stats", {})
    founder_stats = result.get("founder_stats", {})
    non_founder_stats = result.get("non_founder_stats", {})
    full_sib = result.get("full_sib", {})
    lap = result.get("lap", {})
    errors = result["errors"]
    inbreeding = result["inbreeding"]
    generated_tables: list[str] = []

    def linked(section: str, rows: list[dict]) -> str:
        content, paths = table_link(section, rows, tables_dir, report_dir, base)
        generated_tables.extend(paths)
        return content

    missing_parent_rows = [{"type": "sire", "id": value} for value in errors["missing_sires"]]
    missing_parent_rows.extend({"type": "dam", "id": value} for value in errors["missing_dams"])
    loop_rows = [{"cycle": " -> ".join(cycle)} for cycle in errors["loop_cycles"]]
    birth_rows = [{"type": "offspring", "id": value} for value in errors["birthdate_invalid_offspring_ids"]]
    sex_rows = [{"type": "sire", "id": value} for value in errors["sex_mismatch_sire_ids"]]
    sex_rows.extend({"type": "dam", "id": value} for value in errors["sex_mismatch_dam_ids"])
    all_inbreeding_rows = list(inbreeding["records"])
    all_inbreeding_path = tables_dir / f"{base}_inbreeding_all.csv"
    write_csv(all_inbreeding_path, all_inbreeding_rows)
    generated_tables.append(str(all_inbreeding_path))
    repaired_path = tables_dir / f"{base}_repaired_pedigree.txt"
    write_repaired_pedigree_txt(repaired_path, all_inbreeding_rows, selected)
    generated_tables.append(str(repaired_path))

    stats_all = inbreeding["stats_all"]
    stats_inbred = inbreeding["stats_inbred"]
    prefer_birthdate_trend = selected.get("birthdate") != MISSING_OPTION
    lines = [
        report_front_matter(input_path, generated_at),
        "",
        "# Pedigree QC & Inbreeding Report",
        "",
        "## Input",
        f"- File: `{input_path}`",
        f"- Generated at: {generated_at}",
        f"- Progeny column: `{selected['progeny']}`",
        f"- Sire column: `{selected['sire']}`",
        f"- Dam column: `{selected['dam']}`",
        f"- Group column: `{selected['group']}`",
        f"- Sex column: `{selected['sex']}`",
        f"- BirthDate column: `{selected['birthdate']}`",
        "",
        repaired_pedigree_section(repaired_path, report_dir),
        "## Basic Statistics",
        f"- Individuals in total: {meta['total']:,}",
        f"- Founders: {meta.get('founders', 0):,}",
        f"- Non-founders: {meta.get('non_founders', meta['total'] - meta.get('founders', 0)):,}",
        f"- With both parents: {meta.get('with_both_parents', 0):,}",
        f"- Only with known sire: {meta.get('only_sire', 0):,}",
        f"- Only with known dam: {meta.get('only_dam', 0):,}",
        "",
        "## Parent Statistics",
        f"- Sires in total: {parent_stats.get('sires_total', 0):,}",
        f"  - Progeny: {parent_stats.get('sire_progeny', 0):,}",
        f"- Dams in total: {parent_stats.get('dams_total', 0):,}",
        f"  - Progeny: {parent_stats.get('dam_progeny', 0):,}",
        f"- Individuals with progeny: {parent_stats.get('individuals_with_progeny', 0):,}",
        f"- Individuals with no progeny: {parent_stats.get('individuals_without_progeny', 0):,}",
        "",
        "## Founder Statistics",
        f"- Founders: {founder_stats.get('founders', meta.get('founders', 0)):,}",
        f"  - Progeny: {founder_stats.get('progeny', 0):,}",
        f"  - Sires: {founder_stats.get('sires', 0):,}",
        f"    - Progeny: {founder_stats.get('sire_progeny', 0):,}",
        f"  - Dams: {founder_stats.get('dams', 0):,}",
        f"    - Progeny: {founder_stats.get('dam_progeny', 0):,}",
        f"  - With no progeny: {founder_stats.get('with_no_progeny', 0):,}",
        "",
        "## Non-Founder Statistics",
        f"- Non-founders: {non_founder_stats.get('non_founders', meta.get('non_founders', 0)):,}",
        f"  - Sires: {non_founder_stats.get('sires', 0):,}",
        f"    - Progeny: {non_founder_stats.get('sire_progeny', 0):,}",
        f"  - Dams: {non_founder_stats.get('dams', 0):,}",
        f"    - Progeny: {non_founder_stats.get('dam_progeny', 0):,}",
        f"  - Only with known sire: {non_founder_stats.get('only_sire', meta.get('only_sire', 0)):,}",
        f"  - Only with known dam: {non_founder_stats.get('only_dam', meta.get('only_dam', 0)):,}",
        f"  - With known sire and dam: {non_founder_stats.get('with_both_parents', meta.get('with_both_parents', 0)):,}",
        "",
        "## Full-Sib Groups",
        f"- Full-sib groups: {full_sib.get('groups', 0):,}",
        f"- Average family size: {full_sib.get('average_family_size', 0.0):.3f}",
        f"  - Maximum: {full_sib.get('maximum', 0):,}",
        f"  - Minimum: {full_sib.get('minimum', 0):,}",
        "",
        "## Inbreeding Statistics",
        f"- Evaluated individuals: {stats_all.get('total', 0):,}",
        f"- Inbreds in total: {stats_inbred.get('total', 0):,}",
        f"- Inbreds in evaluated: {stats_inbred.get('total', 0):,}",
        "",
        "### Distribution of Inbreeding Coefficients",
        markdown_table(inbreeding["distribution"]),
        "",
        "## Summary Statistics",
        f"- A: Number of individuals: {meta['total']:,}",
        f"- B: Number of inbreds: {stats_inbred.get('total', 0):,}",
        f"- C: Number of founders: {meta.get('founders', 0):,}",
        f"- D: Number of individuals with both known parents: {meta.get('with_both_parents', 0):,}",
        f"- E: Number of individuals with no progeny: {parent_stats.get('individuals_without_progeny', 0):,}",
        f"- G: Average inbreeding coefficients: {stats_all.get('mean', 0.0):.8f}",
        f"- H: Average inbreeding coefficients in the inbreds: {stats_inbred.get('mean', 0.0):.8f}",
        f"- I: Maximum of inbreeding coefficients: {stats_all.get('max', 0.0):.8g}",
        f"- J: Minimum of inbreeding coefficients: {stats_all.get('min', 0.0):.8g}",
        "",
        "## Longest Ancestral Path (LAP)",
        markdown_table(lap.get("distribution", [])),
        "",
        f"Mean generation depth: {lap.get('mean_generation_depth', 0.0):.2f}",
        "",
        "## Inbreeding Trend",
        f"Trend basis: {'BirthDate' if prefer_birthdate_trend else 'LAP'}",
        "",
        trend_chart(all_inbreeding_rows, prefer_birthdate_trend),
        "",
        "## Quality Control Summary",
        f"- Duplicate IDs: {meta.get('duplicate_count', 0):,}",
        f"- Missing sires: {meta.get('missing_sires_count', 0):,}",
        f"- Missing dams: {meta.get('missing_dams_count', 0):,}",
        f"- Self-parent records: {meta.get('self_parent_count', 0):,}",
        f"- Dual-role IDs: {meta.get('dual_role_count', 0):,}",
        f"- Loop count: {meta.get('loop_count', 0):,}",
        "",
        "## Data Quality Checks",
        "### Duplicate IDs",
        linked("duplicate_ids", as_id_rows(errors["duplicate_ids"])),
        "",
        "### Missing Parents",
        linked("missing_parents", missing_parent_rows),
        "",
        "### Self Parent",
        linked("self_parent_ids", as_id_rows(errors["self_parent_ids"])),
        "",
        "### Dual Role IDs",
        linked("dual_role_ids", as_id_rows(errors["dual_role_ids"])),
        "",
        "### Sex Mismatch",
        linked("sex_mismatch", sex_rows),
        "",
        "### BirthDate Order Errors",
        linked("birthdate_errors", birth_rows),
        "",
        "### Loops",
        linked("loops", loop_rows),
        "",
        "### Top High-Inbreeding Individuals",
        markdown_table(inbreeding["top_high"]),
        "",
        "### Full Inbreeding Table",
        f"[Open all inbreeding records]({Path(os.path.relpath(all_inbreeding_path, report_dir)).as_posix()})",
        "",
        "## Group Summary",
        markdown_table(result["group_summary"]) if result["group_summary"] else "No group column selected.",
        "",
        "## Group Analysis",
        group_analysis(all_inbreeding_rows, prefer_birthdate_trend),
        "",
        "## Generated Files",
        *[f"- `{path}`" for path in generated_tables],
        "",
    ]
    safe_write_text(report_path, "\n".join(lines), encoding="utf-8", newline="\n", workspace_root=root)
    return report_path


def stats_text(stats: dict) -> str:
    if not stats or stats.get("total", 0) == 0:
        return "No valid values."
    return "\n".join(
        [
            f"- Total: {stats['total']:,}",
            f"- Min: {stats['min']:.6f}",
            f"- Max: {stats['max']:.6f}",
            f"- Mean: {stats['mean']:.6f}",
            f"- SD: {stats['sd']:.6f}",
        ]
    )


def markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "None."
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows[:DETAIL_INLINE_LIMIT]:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)
