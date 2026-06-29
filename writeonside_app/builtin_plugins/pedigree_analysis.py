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

from ..i18n import get_language, t
from ..storage import safe_write_text
from ..theme import *  # noqa: F401,F403


MISSING_OPTION = "(none)"
DETAIL_INLINE_LIMIT = 20
AUTOFIX_AFFECTED_INLINE_LIMIT = 20


REPORT_TEXT = {
    "en": {
        "none": "None.",
        "no_valid_values": "No valid values.",
        "found_records": "Found {count:,} records.",
        "open_full_table": "Open full table",
        "report_title": "Pedigree QC & Inbreeding Report",
        "report_title_with_source": "Pedigree QC & Inbreeding Report - {source}",
        "input": "Input",
        "file": "File",
        "generated_at": "Generated at",
        "progeny_column": "Progeny column",
        "sire_column": "Sire column",
        "dam_column": "Dam column",
        "group_column": "Group column",
        "sex_column": "Sex column",
        "birthdate_column": "BirthDate column",
        "repaired_pedigree": "Repaired Pedigree",
        "repair_rules": "Repair Rules",
        "repair_output": "Output format: space-delimited `.txt`.",
        "repair_missing": "Missing values are written as `0`.",
        "repair_normalized": "Blank, `NA`, `N/A`, `None`, and `null` are normalized to `0`.",
        "repair_trimmed": "Progeny, Sire, and Dam values are trimmed before output.",
        "repair_optional": "Optional Group, Sex, and BirthDate columns are included only when selected.",
        "repair_excluded": "Rows without a valid Progeny ID are excluded from the repaired pedigree.",
        "open_repaired": "Open repaired pedigree TXT",
        "basic_statistics": "Basic Statistics",
        "individuals_total": "Individuals in total",
        "founders": "Founders",
        "non_founders": "Non-founders",
        "with_both_parents": "With both parents",
        "only_known_sire": "Only with known sire",
        "only_known_dam": "Only with known dam",
        "parent_statistics": "Parent Statistics",
        "sires_total": "Sires in total",
        "dams_total": "Dams in total",
        "progeny": "Progeny",
        "individuals_with_progeny": "Individuals with progeny",
        "individuals_without_progeny": "Individuals with no progeny",
        "founder_statistics": "Founder Statistics",
        "sires": "Sires",
        "dams": "Dams",
        "with_no_progeny": "With no progeny",
        "non_founder_statistics": "Non-Founder Statistics",
        "known_sire_and_dam": "With known sire and dam",
        "full_sib_groups": "Full-Sib Groups",
        "full_sib_groups_count": "Full-sib groups",
        "average_family_size": "Average family size",
        "maximum": "Maximum",
        "minimum": "Minimum",
        "inbreeding_statistics": "Inbreeding Statistics",
        "evaluated_individuals": "Evaluated individuals",
        "inbreds_total": "Inbreds in total",
        "inbreds_evaluated": "Inbreds in evaluated",
        "distribution_inbreeding": "Distribution of Inbreeding Coefficients",
        "summary_statistics": "Summary Statistics",
        "summary_a": "A: Number of individuals",
        "summary_b": "B: Number of inbreds",
        "summary_c": "C: Number of founders",
        "summary_d": "D: Number of individuals with both known parents",
        "summary_e": "E: Number of individuals with no progeny",
        "summary_g": "G: Average inbreeding coefficients",
        "summary_h": "H: Average inbreeding coefficients in the inbreds",
        "summary_i": "I: Maximum of inbreeding coefficients",
        "summary_j": "J: Minimum of inbreeding coefficients",
        "lap": "Longest Ancestral Path (LAP)",
        "mean_generation_depth": "Mean generation depth",
        "inbreeding_trend": "Inbreeding Trend",
        "trend_basis": "Trend basis",
        "no_trend_values": "No valid inbreeding values for trend analysis.",
        "quality_control_summary": "Quality Control Summary",
        "duplicate_ids": "Duplicate IDs",
        "missing_sires": "Missing sires",
        "missing_dams": "Missing dams",
        "self_parent_records": "Self-parent records",
        "dual_role_ids": "Dual-role IDs",
        "loop_count": "Loop count",
        "data_quality_checks": "Data Quality Checks",
        "missing_parents": "Missing Parents",
        "self_parent": "Self Parent",
        "sex_mismatch": "Sex Mismatch",
        "birthdate_order_errors": "BirthDate Order Errors",
        "loops": "Loops",
        "top_high_inbreeding": "Top High-Inbreeding Individuals",
        "full_inbreeding_table": "Full Inbreeding Table",
        "open_all_inbreeding": "Open all inbreeding records",
        "group_summary": "Group Summary",
        "group_analysis": "Group Analysis",
        "no_group_column": "No group column selected.",
        "group": "Group",
        "inbreds": "Inbreds",
        "mean_f": "Mean F",
        "sd_f": "SD F",
        "min_f": "Min F",
        "max_f": "Max F",
        "generated_files": "Generated Files",
        "total": "Total",
        "min": "Min",
        "max": "Max",
        "mean": "Mean",
        "sd": "SD",
        "autofix_summary": "Auto-fix summary",
        "autofix_action": "Action",
        "autofix_result": "Result",
        "autofix_no_changes": "No automatic fixes were needed.",
        "autofix_missing_ids": "Removed {count:,} row(s) with missing or empty ID",
        "autofix_duplicates": "Removed {count:,} duplicate record(s) (kept most complete row per ID)",
        "autofix_missing_parents": "Added {count:,} missing parent founder row(s) with Sire=0 and Dam=0",
        "autofix_self_parent": "Cleared {count:,} self-parent field(s)",
        "autofix_birthdate": "Set {count:,} offspring birth date value(s) to 0",
        "autofix_loops": "Broke {count:,} circular reference(s)",
        "pass": "✔ Pass",
        "autofix_method": "Auto-fix method",
        "method_duplicates": "The software removes duplicate rows and keeps the row with the most complete information per ID (most non-empty fields); ties keep the first. Other rows with the same ID are deleted.",
        "method_self_parent": "The software sets Sire or Dam to 0 where an individual is listed as their own sire or dam. The affected parent field is cleared so the individual is treated as having that parent unknown.",
        "method_missing_parents": "The software adds each missing Sire/Dam reference as a new founder row (ID=<missing_parent>, Sire=0 and Dam=0). Existing offspring links are preserved.",
        "method_birthdate": "The software sets the offspring's birth date to 0 for cases where the offspring's date is not after the parent's. This only applies when a birthdate column is mapped; Sire/Dam links are left unchanged.",
        "method_loops": "The software breaks each cycle by clearing one parent link in the loop: the link from the second-to-last individual in the cycle to the last is set to 0 (Sire or Dam, whichever points to that parent).",
        "autofix_details": "Affected records",
        "qc_after_autofix": "QC status after auto-fix",
        "removed_rows": "Removed rows",
        "kept_record": "Kept record",
        "removed_duplicates": "Removed duplicate records",
        "added_founders": "Added founder rows",
        "cleared_self_parent": "Cleared self-parent fields",
        "cleared_birthdates": "Cleared birth dates",
        "broken_loops": "Broken loops",
        "autofix_applied_fixes": "Applied fixes",
        "autofix_issue": "Issue",
        "autofix_status": "Status",
        "autofix_count": "Count",
        "autofix_affected": "Affected records",
        "autofix_method_short": "Method",
        "not_applicable": "Not applicable",
        "pass_no_fix": "Pass; no fix needed",
        "open_autofix_affected": "Open affected records TXT",
        "autofix_affected_file_title": "Auto-fix affected records",
        "method_missing_ids_short": "Remove rows without a valid Progeny ID.",
        "method_duplicates_short": "Keep the most complete row for each ID; remove the rest.",
        "method_missing_parents_short": "Add missing parents as founder rows.",
        "method_self_parent_short": "Clear the Sire/Dam field that points to the same individual.",
        "method_birthdate_short": "Set invalid offspring birth dates to 0.",
        "method_loops_short": "Clear one parent link in each detected loop.",
    },
    "zh": {
        "none": "无。",
        "no_valid_values": "没有有效值。",
        "found_records": "找到 {count:,} 条记录。",
        "open_full_table": "打开完整表格",
        "report_title": "系谱质控与近交分析报告",
        "report_title_with_source": "系谱质控与近交分析报告 - {source}",
        "input": "输入信息",
        "file": "文件",
        "generated_at": "生成时间",
        "progeny_column": "后代列",
        "sire_column": "父本列",
        "dam_column": "母本列",
        "group_column": "分组列",
        "sex_column": "性别列",
        "birthdate_column": "出生日期列",
        "repaired_pedigree": "修复后的系谱",
        "repair_rules": "修复规则",
        "repair_output": "输出格式：空格分隔的 `.txt`。",
        "repair_missing": "缺失值写为 `0`。",
        "repair_normalized": "空白、`NA`、`N/A`、`None` 和 `null` 会规范化为 `0`。",
        "repair_trimmed": "输出前会清理后代、父本和母本值两侧空白。",
        "repair_optional": "仅在已选择时包含可选的分组、性别和出生日期列。",
        "repair_excluded": "没有有效后代 ID 的行会从修复系谱中排除。",
        "open_repaired": "打开修复后的系谱 TXT",
        "basic_statistics": "基础统计",
        "individuals_total": "个体总数",
        "founders": "奠基个体",
        "non_founders": "非奠基个体",
        "with_both_parents": "父母均已知",
        "only_known_sire": "仅父本已知",
        "only_known_dam": "仅母本已知",
        "parent_statistics": "亲本统计",
        "sires_total": "父本总数",
        "dams_total": "母本总数",
        "progeny": "后代数",
        "individuals_with_progeny": "有后代的个体",
        "individuals_without_progeny": "无后代的个体",
        "founder_statistics": "奠基个体统计",
        "sires": "父本",
        "dams": "母本",
        "with_no_progeny": "无后代",
        "non_founder_statistics": "非奠基个体统计",
        "known_sire_and_dam": "父本和母本均已知",
        "full_sib_groups": "全同胞组",
        "full_sib_groups_count": "全同胞组数",
        "average_family_size": "平均家系大小",
        "maximum": "最大值",
        "minimum": "最小值",
        "inbreeding_statistics": "近交统计",
        "evaluated_individuals": "已评估个体",
        "inbreds_total": "近交个体总数",
        "inbreds_evaluated": "已评估中的近交个体",
        "distribution_inbreeding": "近交系数分布",
        "summary_statistics": "摘要统计",
        "summary_a": "A：个体数量",
        "summary_b": "B：近交个体数量",
        "summary_c": "C：奠基个体数量",
        "summary_d": "D：父母均已知的个体数量",
        "summary_e": "E：无后代个体数量",
        "summary_g": "G：平均近交系数",
        "summary_h": "H：近交个体中的平均近交系数",
        "summary_i": "I：近交系数最大值",
        "summary_j": "J：近交系数最小值",
        "lap": "最长祖先路径（LAP）",
        "mean_generation_depth": "平均世代深度",
        "inbreeding_trend": "近交趋势",
        "trend_basis": "趋势依据",
        "no_trend_values": "没有可用于趋势分析的有效近交值。",
        "quality_control_summary": "质量控制摘要",
        "duplicate_ids": "重复 ID",
        "missing_sires": "缺失父本",
        "missing_dams": "缺失母本",
        "self_parent_records": "自交亲本记录",
        "dual_role_ids": "双重角色 ID",
        "loop_count": "环路数量",
        "data_quality_checks": "数据质量检查",
        "missing_parents": "缺失亲本",
        "self_parent": "自交亲本",
        "sex_mismatch": "性别不匹配",
        "birthdate_order_errors": "出生日期顺序错误",
        "loops": "环路",
        "top_high_inbreeding": "高近交个体排行",
        "full_inbreeding_table": "完整近交表",
        "open_all_inbreeding": "打开全部近交记录",
        "group_summary": "分组摘要",
        "group_analysis": "分组分析",
        "no_group_column": "未选择分组列。",
        "group": "分组",
        "inbreds": "近交个体",
        "mean_f": "平均 F",
        "sd_f": "F 标准差",
        "min_f": "最小 F",
        "max_f": "最大 F",
        "generated_files": "生成的文件",
        "total": "总数",
        "min": "最小值",
        "max": "最大值",
        "mean": "平均值",
        "sd": "标准差",
        "autofix_summary": "自动修复摘要",
        "autofix_action": "操作",
        "autofix_result": "结果",
        "autofix_no_changes": "无需自动修复。",
        "autofix_missing_ids": "移除了 {count:,} 行缺失或空 ID 记录",
        "autofix_duplicates": "移除了 {count:,} 条重复记录（每个 ID 保留信息最完整的一行）",
        "autofix_missing_parents": "新增了 {count:,} 个缺失亲本奠基行，Sire=0 且 Dam=0",
        "autofix_self_parent": "清除了 {count:,} 个自我亲本字段",
        "autofix_birthdate": "将 {count:,} 个后代出生日期设为 0",
        "autofix_loops": "断开了 {count:,} 个循环引用",
        "pass": "✔ 通过",
        "autofix_method": "自动修复方法",
        "method_duplicates": "软件会删除重复行，并为每个 ID 保留信息最完整的一行（非空字段最多）；若并列则保留第一行。同一 ID 的其它行会被删除。",
        "method_self_parent": "当个体被列为自己的父本或母本时，软件会将对应的 Sire 或 Dam 设为 0，使其被视为该亲本未知。",
        "method_missing_parents": "软件会把每个缺失的 Sire/Dam 引用新增为奠基个体行（ID=<缺失亲本>，Sire=0，Dam=0），原有后代连接保持不变。",
        "method_birthdate": "当后代出生日期不晚于亲本日期时，软件会将该后代的出生日期设为 0。仅在映射了出生日期列时生效，Sire/Dam 连接不变。",
        "method_loops": "软件会通过清除循环中的一个亲本连接来断开每个环路：将循环倒数第二个个体指向最后一个个体的 Sire 或 Dam 设为 0。",
        "autofix_details": "影响到的记录",
        "qc_after_autofix": "自动修复后的质控状态",
        "removed_rows": "移除的行",
        "kept_record": "保留的记录",
        "removed_duplicates": "移除的重复记录",
        "added_founders": "新增奠基行",
        "cleared_self_parent": "清除的自我亲本字段",
        "cleared_birthdates": "清除的出生日期",
        "broken_loops": "断开的环路",
        "autofix_applied_fixes": "已应用的修复",
        "autofix_issue": "问题",
        "autofix_status": "状态",
        "autofix_count": "数量",
        "autofix_affected": "影响记录",
        "autofix_method_short": "修复方法",
        "not_applicable": "不适用",
        "pass_no_fix": "通过；无需修复",
        "open_autofix_affected": "打开影响记录 TXT",
        "autofix_affected_file_title": "自动修复影响记录",
        "method_missing_ids_short": "移除没有有效 Progeny ID 的行。",
        "method_duplicates_short": "每个 ID 保留信息最完整的一行，删除其余重复行。",
        "method_missing_parents_short": "将缺失亲本新增为奠基个体行。",
        "method_self_parent_short": "清空指向自身的 Sire/Dam 字段。",
        "method_birthdate_short": "将无效的后代出生日期设为 0。",
        "method_loops_short": "清空每个环路中的一个亲本连接。",
    },
}


def report_language(app=None) -> str:
    configured = getattr(getattr(app, "config", None), "language", None)
    language = str(configured or get_language()).strip().lower()
    return "zh" if language.startswith("zh") else "en"


def report_text(key: str, app=None, **kwargs: object) -> str:
    catalog = REPORT_TEXT.get(report_language(app), REPORT_TEXT["en"])
    text = catalog.get(key) or REPORT_TEXT["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text


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
            existing = getattr(app, "_pedigree_plugin_window", None)
            try:
                if existing is not None and existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return
            except tk.TclError:
                pass
            app._pedigree_plugin_open = False
            if getattr(app, "_pedigree_plugin_window", None) is existing:
                try:
                    delattr(app, "_pedigree_plugin_window")
                except AttributeError:
                    pass
        g = globals()
        parent = getattr(app, "_plugin_parent_window", None)
        try:
            if parent is None or not parent.winfo_exists():
                parent = app.root
        except tk.TclError:
            parent = app.root
        win = tk.Toplevel(parent)
        app._pedigree_plugin_open = True
        app._pedigree_plugin_window = win
        win.withdraw()
        win.title(t("pedigree.window_title"))
        work_width = max(420, app.work_right - app.work_left)
        work_height = max(360, app.work_bottom - app.work_top)
        width = min(780, max(420, work_width - 48))
        height = min(640, max(360, work_height - 72))
        x = app.work_left + max(0, (work_width - width) // 2)
        y = app.work_top + max(0, (work_height - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.minsize(min(420, width), min(340, height))
        win.configure(bg=g["BG"])
        try:
            win.transient(parent)
        except tk.TclError:
            pass
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

        content_shell = tk.Frame(win, bg=g["BG"])
        content_shell.pack(fill="both", expand=True)
        content_canvas = tk.Canvas(content_shell, bg=g["BG"], highlightthickness=0, bd=0)
        content_scroll_track = tk.Frame(content_shell, bg=g["BG"], width=12, cursor="sb_v_double_arrow")
        content_scroll_thumb = tk.Frame(content_scroll_track, bg=g["BORDER"], width=5, cursor="sb_v_double_arrow")
        content_canvas.configure(
            yscrollcommand=lambda first, last: update_content_scroll_thumb(first, last)
        )
        content_canvas.pack(side="left", fill="both", expand=True)
        content_scroll_track.pack(side="right", fill="y", padx=(0, 5), pady=10)
        content_scroll_track.pack_propagate(False)
        content = tk.Frame(content_canvas, bg=g["BG"])
        content_window = content_canvas.create_window((0, 0), window=content, anchor="nw")

        def update_content_scroll_thumb(first: str, last: str) -> None:
            start = float(first)
            end = float(last)
            if start <= 0 and end >= 1:
                content_scroll_thumb.place_forget()
                return
            content_scroll_thumb.place(
                relx=0.5,
                rely=start,
                relheight=max(0.08, end - start),
                width=5,
                anchor="n",
            )

        def scroll_content_to_pointer(event) -> None:
            height = max(1, content_scroll_track.winfo_height())
            content_canvas.yview_moveto(max(0.0, min(1.0, event.y / height)))

        content_drag_state = {"y": 0, "first": 0.0}

        def start_content_thumb_drag(event) -> None:
            first, _last = content_canvas.yview()
            content_drag_state["y"] = event.y_root
            content_drag_state["first"] = first
            content_scroll_thumb.config(bg=globals()["ACCENT"])

        def drag_content_thumb(event) -> None:
            height = max(1, content_scroll_track.winfo_height())
            delta = (event.y_root - content_drag_state["y"]) / height
            content_canvas.yview_moveto(max(0.0, min(1.0, content_drag_state["first"] + delta)))

        def end_content_thumb_drag(_event) -> None:
            content_scroll_thumb.config(bg=globals()["BORDER"])

        def sync_scroll_region(_event=None) -> None:
            try:
                content_canvas.configure(scrollregion=content_canvas.bbox("all"))
                first, last = content_canvas.yview()
                update_content_scroll_thumb(str(first), str(last))
            except tk.TclError:
                pass

        def sync_content_width(event) -> None:
            try:
                content_canvas.itemconfigure(content_window, width=max(1, event.width))
            except tk.TclError:
                pass

        def scroll_content(event) -> str:
            delta = -1 if event.delta > 0 else 1
            content_canvas.yview_scroll(delta * 3, "units")
            return "break"

        content.bind("<Configure>", sync_scroll_region)
        content_canvas.bind("<Configure>", sync_content_width)
        content_scroll_track.bind("<Button-1>", scroll_content_to_pointer)
        content_scroll_thumb.bind("<ButtonPress-1>", start_content_thumb_drag)
        content_scroll_thumb.bind("<B1-Motion>", drag_content_thumb)
        content_scroll_thumb.bind("<ButtonRelease-1>", end_content_thumb_drag)
        content_scroll_thumb.bind("<Enter>", lambda _event: content_scroll_thumb.config(bg=globals()["ACCENT_2"]))
        content_scroll_thumb.bind("<Leave>", lambda _event: content_scroll_thumb.config(bg=globals()["BORDER"]))
        content_canvas.bind("<Enter>", lambda _event: content_canvas.bind_all("<MouseWheel>", scroll_content))
        content_canvas.bind("<Leave>", lambda _event: content_canvas.unbind_all("<MouseWheel>"))
        content.configure(padx=22, pady=18)

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

        release_state_done = {"value": False}

        def release_plugin_state() -> None:
            if release_state_done["value"]:
                return
            release_state_done["value"] = True
            app._pedigree_plugin_open = False
            if getattr(app, "_pedigree_plugin_window", None) is win:
                try:
                    delattr(app, "_pedigree_plugin_window")
                except AttributeError:
                    pass
            try:
                content_canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            if getattr(app, "_refresh_pedigree_plugin_theme", None) is refresh_theme:
                try:
                    delattr(app, "_refresh_pedigree_plugin_theme")
                except AttributeError:
                    pass

        def close() -> None:
            release_plugin_state()
            try:
                win.destroy()
            except tk.TclError:
                pass

        def on_window_destroy(event) -> None:
            if event.widget is win:
                release_plugin_state()

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
            target_path = Path(selected)
            load_state: dict[str, object] = {
                "done": False,
                "error": None,
                "headers": None,
                "rows": None,
                "delimiter": None,
            }
            set_busy(True)
            file_label.configure(text=str(target_path))
            set_status(t("pedigree.loading", path=target_path), muted=True)

            def load_worker() -> None:
                try:
                    headers, rows, delimiter = read_table(target_path)
                    load_state["headers"] = headers
                    load_state["rows"] = rows
                    load_state["delimiter"] = delimiter
                except Exception as exc:
                    load_state["error"] = exc
                finally:
                    load_state["done"] = True

            def finish_load() -> None:
                if not win.winfo_exists():
                    return
                if not load_state["done"]:
                    win.after(50, finish_load)
                    return
                set_busy(False)
                if load_state["error"] is not None:
                    set_status(t("pedigree.error.read_failed", exc=load_state["error"]), True)
                    return
                self.path = target_path
                self.headers = list(load_state["headers"] or [])
                self.rows = list(load_state["rows"] or [])
                self.delimiter = str(load_state["delimiter"] or "")
                headers = list(self.headers)
                set_menu_values("progeny", headers, guess(headers, "progeny", "id", "animal", "individual", "product_id"))
                set_menu_values("sire", headers, guess(headers, "sire", "father", "dad"))
                set_menu_values("dam", headers, guess(headers, "dam", "mother", "mom"))
                set_menu_values("group", headers, guess(headers, "group", "population", "line", optional=True))
                set_menu_values("sex", headers, guess(headers, "sex", "gender", optional=True))
                set_menu_values("birthdate", headers, guess(headers, "birthdate", "birth_date", "dob", optional=True))
                set_status(t("pedigree.loaded", rows=len(self.rows), columns=len(headers)))

            threading.Thread(target=load_worker, daemon=True).start()
            finish_load()

        def configure_progress_style(window: tk.Misc) -> None:
            bg = globals()["SURFACE"]
            text = globals()["TEXT"]
            muted = globals()["MUTED"]
            border = globals()["BORDER"]
            accent = globals()["ACCENT"]
            accent_2 = globals()["ACCENT_2"]
            style = ttk.Style(window)
            style.configure("PedigreeProgress.TLabel", background=bg, foreground=text, font=("Segoe UI", 10, "bold"))
            style.configure("PedigreeProgressMuted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
            style.configure(
                "Pedigree.Horizontal.TProgressbar",
                troughcolor=border,
                background=accent,
                lightcolor=accent_2,
                darkcolor=accent,
                bordercolor=border,
                thickness=10,
            )

        def center_progress_dialog(dialog: tk.Toplevel) -> None:
            try:
                dialog.update_idletasks()
                popup_width = max(320, min(420, dialog.winfo_reqwidth()))
                popup_height = max(140, dialog.winfo_reqheight())
                parent_x = win.winfo_rootx()
                parent_y = win.winfo_rooty()
                parent_w = max(1, win.winfo_width())
                parent_h = max(1, win.winfo_height())
                popup_x = parent_x + max(0, (parent_w - popup_width) // 2)
                popup_y = parent_y + max(0, (parent_h - popup_height) // 2)
                popup_x = max(app.work_left + 8, min(popup_x, app.work_right - popup_width - 8))
                popup_y = max(app.work_top + 8, min(popup_y, app.work_bottom - popup_height - 8))
                dialog.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
            except tk.TclError:
                pass

        def open_progress_panel() -> dict[str, object]:
            progress_dialog = tk.Toplevel(win)
            progress_dialog.withdraw()
            try:
                progress_dialog.attributes("-alpha", 0.0)
            except tk.TclError:
                pass
            progress_dialog.title(t("pedigree.progress.title"))
            progress_dialog.transient(win)
            progress_dialog.resizable(False, False)
            progress_dialog.configure(bg=globals()["BG"])
            shell = tk.Frame(
                progress_dialog,
                bg=globals()["SURFACE"],
                highlightthickness=1,
                highlightbackground=globals()["BORDER"],
                padx=16,
                pady=14,
            )
            shell.pack(fill="both", expand=True, padx=12, pady=12)
            progress_header = tk.Frame(shell, bg=globals()["SURFACE"])
            progress_header.pack(fill="x")
            progress_title = ttk.Label(
                progress_header,
                text=t("pedigree.progress.title"),
                style="PedigreeProgress.TLabel",
                anchor="w",
            )
            progress_title.pack(side="left", fill="x", expand=True)
            progress_percent = ttk.Label(
                progress_header,
                text="0%",
                style="PedigreeProgressMuted.TLabel",
                anchor="e",
                width=5,
            )
            progress_percent.pack(side="right")
            progress_label = ttk.Label(
                shell,
                text=t("pedigree.progress.running"),
                style="PedigreeProgressMuted.TLabel",
                anchor="w",
                wraplength=360,
            )
            progress_label.pack(fill="x", pady=(10, 12))
            progress_value = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(
                shell,
                variable=progress_value,
                maximum=100,
                mode="determinate",
                style="Pedigree.Horizontal.TProgressbar",
            )
            progress_bar.pack(fill="x", pady=(0, 12))
            progress_actions = tk.Frame(shell, bg=globals()["SURFACE"])
            progress_actions.pack(fill="x")
            cancel_btn = tk.Button(
                progress_actions,
                text=t("dialog.cancel"),
                bg=globals()["BORDER"],
                fg=globals()["TEXT"],
                activebackground=globals()["SURFACE_2"],
                activeforeground=globals()["TEXT"],
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
            )
            cancel_btn.pack(side="right", padx=(8, 0))
            close_btn = tk.Button(
                progress_actions,
                text=t("pedigree.progress.done"),
                state="disabled",
                bg=globals()["BORDER"],
                fg=globals()["TEXT"],
                activebackground=globals()["SURFACE_2"],
                activeforeground=globals()["TEXT"],
                relief="flat",
                padx=14,
                pady=5,
            )

            configure_progress_style(progress_dialog)
            progress_value.set(0)
            progress_percent.configure(text="0%")
            progress_label.configure(text=t("pedigree.progress.running"))
            close_btn.configure(state="disabled", command=lambda: None)
            cancel_btn.configure(state="normal")
            state: dict[str, object] = {
                "dialog": progress_dialog,
                "shell": shell,
                "header": progress_header,
                "actions": progress_actions,
                "title": progress_title,
                "label": progress_label,
                "bar": progress_bar,
                "value": progress_value,
                "percent": progress_percent,
                "done_btn": close_btn,
                "cancel_btn": cancel_btn,
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
                    progress_dialog.destroy()
                except tk.TclError:
                    pass
                set_busy(False)
                set_status(t("pedigree.progress.cancelled"), muted=True)

            cancel_btn.configure(command=cancel)
            progress_dialog.protocol("WM_DELETE_WINDOW", cancel)
            progress_dialog.bind("<Escape>", lambda _event: cancel())
            center_progress_dialog(progress_dialog)
            progress_dialog.update_idletasks()
            progress_dialog.deiconify()
            try:
                progress_dialog.lift(win)
            except tk.TclError:
                progress_dialog.lift()
            progress_dialog.focus_force()
            progress_dialog.update_idletasks()
            try:
                progress_dialog.attributes("-alpha", 1.0)
            except tk.TclError:
                pass
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
            worker_state: dict[str, object] = {
                "done": False,
                "report": None,
                "error": None,
                "stage": t("pedigree.progress.running"),
            }
            progress_animation = {
                "display": 0.0,
                "completion_started": None,
                "completion_from": 0.0,
            }
            set_busy(True)
            set_status(t("pedigree.progress.running"), muted=True)
            win.update_idletasks()
            progress = open_progress_panel()

            def worker() -> None:
                try:
                    result = run_rust_autofix_analysis(
                        self.rows,
                        selected,
                        stage_callback=lambda message: worker_state.__setitem__("stage", message),
                    )
                    if progress["cancelled"]:
                        return
                    worker_state["stage"] = t("pedigree.progress.writing")
                    worker_state["report"] = write_report(app, self.path, selected, result)
                except Exception as exc:
                    worker_state["error"] = exc
                finally:
                    worker_state["done"] = True

            def ease_out_cubic(value: float) -> float:
                value = max(0.0, min(1.0, value))
                return 1.0 - pow(1.0 - value, 3)

            def running_progress_target(elapsed: float) -> float:
                # Smoothly approaches 94% while the Rust worker is still busy.
                # This avoids both a static bar and a fake linear countdown that
                # reaches the end before the report is actually ready.
                return min(0.94, 0.94 * (1.0 - math.exp(-elapsed / 2.2)))

            def set_progress_value(value: float) -> None:
                value = max(0.0, min(1.0, value))
                progress["value"].set(value * 100)
                progress["percent"].configure(text=f"{round(value * 100)}%")

            def tick() -> None:
                if not win.winfo_exists():
                    return
                if progress["cancelled"]:
                    return
                now = time.monotonic()
                elapsed = now - start_time
                display = float(progress_animation["display"])
                if worker_state["done"]:
                    if progress_animation["completion_started"] is None:
                        progress_animation["completion_started"] = now
                        progress_animation["completion_from"] = display
                    completion_elapsed = now - float(progress_animation["completion_started"])
                    completion_ratio = ease_out_cubic(completion_elapsed / 0.45)
                    completion_from = float(progress_animation["completion_from"])
                    value = completion_from + (1.0 - completion_from) * completion_ratio
                else:
                    target = running_progress_target(elapsed)
                    value = display + (target - display) * 0.18
                    value = max(display, min(value, 0.94))
                progress_animation["display"] = value
                try:
                    set_progress_value(value)
                    current_stage = str(worker_state.get("stage") or t("pedigree.progress.running"))
                    progress["label"].configure(text=current_stage)
                except tk.TclError:
                    progress["cancelled"] = True
                    set_busy(False)
                    set_status(t("pedigree.progress.cancelled"), muted=True)
                    return
                if not worker_state["done"] or value < 0.999:
                    win.after(16, tick)
                    return
                set_busy(False)
                if worker_state["error"] is not None:
                    set_status(t("pedigree.error.analysis_failed", exc=worker_state["error"]), True)
                    def close_progress_panel() -> None:
                        current_progress["state"] = None
                        try:
                            progress["dialog"].destroy()
                        except tk.TclError:
                            pass
                    try:
                        progress["label"].configure(text=t("pedigree.error.analysis_failed", exc=worker_state["error"]))
                        progress["cancel_btn"].pack_forget()
                        progress["done_btn"].pack(side="right")
                        progress["done_btn"].configure(state="normal", text=t("pedigree.progress.done"), command=close_progress_panel)
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
                    set_progress_value(1.0)
                    progress["label"].configure(text=t("pedigree.progress.complete"))
                    progress["cancel_btn"].pack_forget()
                    progress["done_btn"].configure(state="disabled")
                    win.after(650, finish)
                except tk.TclError:
                    finish()

            def start_worker() -> None:
                threading.Thread(target=worker, daemon=True).start()

            win.after(50, start_worker)
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
                content_shell.configure(bg=_g["BG"])
                content_canvas.configure(bg=_g["BG"])
                content_scroll_track.configure(bg=_g["BG"])
                content_scroll_thumb.configure(bg=_g["BORDER"])
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
                    configure_progress_style(progress_state["dialog"])
                    progress_state["dialog"].configure(bg=_g["BG"])
                    progress_state["shell"].configure(bg=_g["SURFACE"], highlightbackground=_g["BORDER"])
                    progress_state["header"].configure(bg=_g["SURFACE"])
                    progress_state["actions"].configure(bg=_g["SURFACE"])
                    progress_state["done_btn"].configure(bg=_g["BORDER"], fg=_g["TEXT"])
                    progress_state["cancel_btn"].configure(bg=_g["BORDER"], fg=_g["TEXT"])
            except tk.TclError:
                pass

        app._refresh_pedigree_plugin_theme = refresh_theme
        refresh_theme()

        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _event: close())
        win.bind("<Destroy>", on_window_destroy, add="+")
        win.update_idletasks()
        win.deiconify()
        try:
            win.lift(parent)
        except tk.TclError:
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


def selected_columns_for_rust(
    rows: list[dict[str, str]],
    selected: dict[str, str],
) -> tuple[list[str], list[str], list[str], list[str] | None, list[str] | None, list[str] | None]:
    progeny_col = selected["progeny"]
    sire_col = selected["sire"]
    dam_col = selected["dam"]
    group_col = selected.get("group", MISSING_OPTION)
    sex_col = selected.get("sex", MISSING_OPTION)
    birth_col = selected.get("birthdate", MISSING_OPTION)
    ids: list[str] = []
    sires: list[str] = []
    dams: list[str] = []
    groups: list[str] | None = [] if group_col != MISSING_OPTION else None
    sexes: list[str] | None = [] if sex_col != MISSING_OPTION else None
    birthdates: list[str] | None = [] if birth_col != MISSING_OPTION else None
    for row in rows:
        ids.append(row.get(progeny_col, ""))
        sires.append(row.get(sire_col, ""))
        dams.append(row.get(dam_col, ""))
        if groups is not None:
            groups.append(row.get(group_col, ""))
        if sexes is not None:
            sexes.append(row.get(sex_col, ""))
        if birthdates is not None:
            birthdates.append(row.get(birth_col, ""))
    return ids, sires, dams, groups, sexes, birthdates


def pedigree_is_missing(value: object) -> bool:
    text = str(value or "").strip()
    return not text or text.casefold() in {"0", "na", "n/a", "none", "null"}


def normalized_parent_value(value: object) -> str:
    text = str(value or "").strip()
    return "0" if pedigree_is_missing(text) else text


def row_completeness(row: dict[str, str]) -> int:
    return sum(1 for value in row.values() if not pedigree_is_missing(value))


def parsed_birthdate_value(value: object) -> int | None:
    text = str(value or "").strip()
    if pedigree_is_missing(text):
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        try:
            return int(digits[:8])
        except ValueError:
            return None
    try:
        return int(float(text) * 1000.0)
    except ValueError:
        return None


def detect_parent_cycles(rows: list[dict[str, str]], selected: dict[str, str]) -> list[list[str]]:
    id_col = selected["progeny"]
    sire_col = selected["sire"]
    dam_col = selected["dam"]
    ids = {str(row.get(id_col, "")).strip() for row in rows}
    parent_map: dict[str, list[str]] = {}
    for row in rows:
        child = str(row.get(id_col, "")).strip()
        parents = []
        for column in (sire_col, dam_col):
            parent = normalized_parent_value(row.get(column, ""))
            if parent != "0" and parent in ids:
                parents.append(parent)
        parent_map[child] = parents

    cycles: list[list[str]] = []
    visited: set[str] = set()
    stack: set[str] = set()
    path: list[str] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def remember_cycle(cycle: list[str]) -> None:
        if len(cycle) < 3:
            return
        body = cycle[:-1]
        rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
        key = min(rotations)
        if key in seen_cycles:
            return
        seen_cycles.add(key)
        cycles.append(cycle)

    def visit(node: str) -> None:
        if node in stack:
            try:
                start = path.index(node)
            except ValueError:
                return
            remember_cycle([*path[start:], node])
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        path.append(node)
        for parent in parent_map.get(node, []):
            visit(parent)
        path.pop()
        stack.remove(node)

    for item in list(parent_map):
        visit(item)
    return cycles


def break_parent_cycles(
    rows: list[dict[str, str]],
    selected: dict[str, str],
    details: list[dict[str, object]] | None = None,
) -> int:
    id_col = selected["progeny"]
    sire_col = selected["sire"]
    dam_col = selected["dam"]
    row_by_id = {str(row.get(id_col, "")).strip(): row for row in rows}
    broken = 0
    for _attempt in range(max(1, len(rows) * 2)):
        cycles = detect_parent_cycles(rows, selected)
        if not cycles:
            break
        changed = False
        for cycle in cycles:
            if len(cycle) < 3:
                continue
            child_id = cycle[-2]
            parent_id = cycle[-1]
            row = row_by_id.get(child_id)
            if row is None:
                continue
            if normalized_parent_value(row.get(sire_col, "")) == parent_id:
                row[sire_col] = "0"
                if details is not None:
                    details.append({"child": child_id, "parent": parent_id, "field": "Sire", "cycle": cycle})
                changed = True
                broken += 1
            elif normalized_parent_value(row.get(dam_col, "")) == parent_id:
                row[dam_col] = "0"
                if details is not None:
                    details.append({"child": child_id, "parent": parent_id, "field": "Dam", "cycle": cycle})
                changed = True
                broken += 1
        if not changed:
            break
    return broken


def auto_fix_pedigree_rows(
    rows: list[dict[str, str]],
    selected: dict[str, str],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    try:
        engine = importlib.import_module("writeonside_pedigree")
        rust_autofix = getattr(engine, "auto_fix_pedigree", None)
    except ImportError:
        rust_autofix = None
    if rust_autofix is not None:
        result = rust_autofix(
            selected_column(rows, selected["progeny"]),
            selected_column(rows, selected["sire"]),
            selected_column(rows, selected["dam"]),
            selected_column(rows, selected["group"]) if selected["group"] != MISSING_OPTION else None,
            selected_column(rows, selected["sex"]) if selected["sex"] != MISSING_OPTION else None,
            selected_column(rows, selected["birthdate"]) if selected["birthdate"] != MISSING_OPTION else None,
        )
        fixed_rows = rust_autofix_rows(result, selected)
        return fixed_rows, dict(result.get("autofix", {}))
    return auto_fix_pedigree_rows_python(rows, selected)


def rust_autofix_rows(result: dict, selected: dict[str, str]) -> list[dict[str, str]]:
    ids = list(result.get("ids", []))
    sires = list(result.get("sires", []))
    dams = list(result.get("dams", []))
    groups = list(result.get("groups", []))
    sexes = list(result.get("sex", []))
    birthdates = list(result.get("birthdates", []))
    rows = []
    for index, item_id in enumerate(ids):
        row = {
            selected["progeny"]: str(item_id),
            selected["sire"]: str(sires[index]) if index < len(sires) else "0",
            selected["dam"]: str(dams[index]) if index < len(dams) else "0",
        }
        if selected.get("group") != MISSING_OPTION:
            row[selected["group"]] = str(groups[index]) if index < len(groups) else ""
        if selected.get("sex") != MISSING_OPTION:
            row[selected["sex"]] = str(sexes[index]) if index < len(sexes) else ""
        if selected.get("birthdate") != MISSING_OPTION:
            row[selected["birthdate"]] = str(birthdates[index]) if index < len(birthdates) else ""
        rows.append(row)
    return rows


def run_rust_autofix_analysis(rows: list[dict[str, str]], selected: dict[str, str], stage_callback=None) -> dict:
    engine = require_rust_pedigree_engine(require_autofix=True)
    if stage_callback is not None:
        stage_callback(t("pedigree.progress.autofix"))
    ids, sires, dams, groups, sexes, birthdates = selected_columns_for_rust(rows, selected)
    autofix_result = engine.auto_fix_pedigree(
        ids,
        sires,
        dams,
        groups,
        sexes,
        birthdates,
    )
    ids = autofix_result.get("ids", [])
    sires = autofix_result.get("sires", [])
    dams = autofix_result.get("dams", [])
    groups = autofix_result.get("groups", [])
    sexes = autofix_result.get("sex", [])
    birthdates = autofix_result.get("birthdates", [])
    if stage_callback is not None:
        stage_callback(t("pedigree.progress.analyzing"))
    result = engine.analyze_pedigree(
        ids,
        sires,
        dams,
        groups if selected.get("group") != MISSING_OPTION else None,
        sexes if selected.get("sex") != MISSING_OPTION else None,
        birthdates if selected.get("birthdate") != MISSING_OPTION else None,
    )
    autofix = dict(autofix_result.get("autofix", {}))
    autofix["post_qc"] = post_autofix_qc(result)
    result["autofix"] = autofix
    return result


def require_rust_pedigree_engine(*, require_autofix: bool = False) -> object:
    try:
        engine = importlib.import_module("writeonside_pedigree")
    except ImportError as exc:
        raise RuntimeError("Rust pedigree engine is not installed. Build it with maturin before using this plugin.") from exc
    if require_autofix and not hasattr(engine, "auto_fix_pedigree"):
        raise RuntimeError("Rust pedigree engine is outdated. Rebuild it with maturin before using this plugin.")
    return engine


def auto_fix_pedigree_rows_python(
    rows: list[dict[str, str]],
    selected: dict[str, str],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    id_col = selected["progeny"]
    sire_col = selected["sire"]
    dam_col = selected["dam"]
    birth_col = selected.get("birthdate", MISSING_OPTION)
    has_birthdate = birth_col != MISSING_OPTION

    summary: dict[str, object] = {
        "missing_ids": 0,
        "duplicates": 0,
        "missing_parents": 0,
        "self_parent": 0,
        "birthdate": 0,
        "loops": 0,
        "missing_id_rows": [],
        "duplicate_records": [],
        "kept_duplicate_records": [],
        "missing_parent_ids": [],
        "self_parent_records": [],
        "birthdate_records": [],
        "loop_breaks": [],
    }

    valid_rows: list[dict[str, str]] = []
    for row_index, row in enumerate(rows, start=1):
        fixed = dict(row)
        fixed[id_col] = str(fixed.get(id_col, "")).strip()
        if pedigree_is_missing(fixed[id_col]):
            summary["missing_ids"] = int(summary["missing_ids"]) + 1
            summary["missing_id_rows"].append({"row": row_index})
            continue
        fixed[sire_col] = normalized_parent_value(fixed.get(sire_col, ""))
        fixed[dam_col] = normalized_parent_value(fixed.get(dam_col, ""))
        valid_rows.append(fixed)

    best_by_id: dict[str, tuple[int, dict[str, str]]] = {}
    id_counts: dict[str, int] = {}
    for index, row in enumerate(valid_rows):
        item_id = str(row.get(id_col, "")).strip()
        id_counts[item_id] = id_counts.get(item_id, 0) + 1
        score = row_completeness(row)
        current = best_by_id.get(item_id)
        if current is None or score > row_completeness(current[1]):
            best_by_id[item_id] = (index, row)
    summary["duplicates"] = len(valid_rows) - len(best_by_id)
    duplicate_ids = {item_id for item_id, count_value in id_counts.items() if count_value > 1}
    for item_id in sorted(duplicate_ids):
        kept_index, kept_row = best_by_id[item_id]
        summary["kept_duplicate_records"].append({"id": item_id, "row": kept_index + 1})
        for index, row in enumerate(valid_rows):
            if str(row.get(id_col, "")).strip() == item_id and index != kept_index:
                summary["duplicate_records"].append({"id": item_id, "row": index + 1})
    kept_indices = {index for index, _row in best_by_id.values()}
    fixed_rows = [row for index, row in enumerate(valid_rows) if index in kept_indices]

    id_set = {str(row.get(id_col, "")).strip() for row in fixed_rows}
    for row in fixed_rows:
        item_id = str(row.get(id_col, "")).strip()
        if normalized_parent_value(row.get(sire_col, "")) == item_id:
            row[sire_col] = "0"
            summary["self_parent"] = int(summary["self_parent"]) + 1
            summary["self_parent_records"].append({"id": item_id, "field": "Sire"})
        if normalized_parent_value(row.get(dam_col, "")) == item_id:
            row[dam_col] = "0"
            summary["self_parent"] = int(summary["self_parent"]) + 1
            summary["self_parent_records"].append({"id": item_id, "field": "Dam"})

    missing_parent_ids: set[str] = set()
    for row in fixed_rows:
        for column in (sire_col, dam_col):
            parent = normalized_parent_value(row.get(column, ""))
            if parent != "0" and parent not in id_set:
                missing_parent_ids.add(parent)
    template_keys: list[str] = []
    for row in fixed_rows:
        for key in row:
            if key not in template_keys:
                template_keys.append(key)
    for parent in sorted(missing_parent_ids):
        founder = {key: "" for key in template_keys}
        founder[id_col] = parent
        founder[sire_col] = "0"
        founder[dam_col] = "0"
        fixed_rows.append(founder)
        id_set.add(parent)
    summary["missing_parents"] = len(missing_parent_ids)
    summary["missing_parent_ids"] = sorted(missing_parent_ids)

    if has_birthdate:
        birth_map: dict[str, int] = {}
        for row in fixed_rows:
            value = parsed_birthdate_value(row.get(birth_col, ""))
            if value is not None:
                birth_map[str(row.get(id_col, "")).strip()] = value
        invalid_birthdate_ids: set[str] = set()
        for row in fixed_rows:
            child_id = str(row.get(id_col, "")).strip()
            child_date = birth_map.get(child_id)
            if child_date is None:
                continue
            for column in (sire_col, dam_col):
                parent_id = normalized_parent_value(row.get(column, ""))
                parent_date = birth_map.get(parent_id)
                if parent_date is not None and parent_date >= child_date:
                    invalid_birthdate_ids.add(child_id)
        for row in fixed_rows:
            if str(row.get(id_col, "")).strip() in invalid_birthdate_ids:
                row[birth_col] = "0"
        summary["birthdate"] = len(invalid_birthdate_ids)
        summary["birthdate_records"] = [{"id": item_id, "field": "BirthDate"} for item_id in sorted(invalid_birthdate_ids)]

    summary["loops"] = break_parent_cycles(fixed_rows, selected, summary["loop_breaks"])
    summary["total_actions"] = sum(int(summary[key]) for key in (
        "missing_ids",
        "duplicates",
        "missing_parents",
        "self_parent",
        "birthdate",
        "loops",
    ))
    return fixed_rows, summary


def run_rust_analysis(rows: list[dict[str, str]], selected: dict[str, str]) -> dict:
    engine = require_rust_pedigree_engine()
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


def table_link(section: str, rows: list[dict], tables_dir: Path, report_dir: Path, base: str, app=None) -> tuple[str, list[str]]:
    if not rows:
        return report_text("none", app), []
    lines = [report_text("found_records", app, count=len(rows))]
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
    lines.append(f"[{report_text('open_full_table', app)}]({relative})")
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


def repaired_pedigree_section(repaired_path: Path, report_dir: Path, app=None) -> str:
    relative = Path(os.path.relpath(repaired_path, report_dir)).as_posix()
    section = [
        f"## {report_text('repaired_pedigree', app)}",
        f"### {report_text('repair_rules', app)}",
        f"- {report_text('repair_output', app)}",
        f"- {report_text('repair_missing', app)}",
        f"- {report_text('repair_normalized', app)}",
        f"- {report_text('repair_trimmed', app)}",
        f"- {report_text('repair_optional', app)}",
        f"- {report_text('repair_excluded', app)}",
        "",
        f"[{report_text('open_repaired', app)}]({relative})",
        "",
    ]
    return "\n".join(section)


def post_autofix_qc(result: dict) -> dict[str, int]:
    meta = result.get("meta", {})
    errors = result.get("errors", {})
    return {
        "duplicate_ids": int(meta.get("duplicate_count", len(errors.get("duplicate_ids", [])))),
        "missing_sires": int(meta.get("missing_sires_count", len(errors.get("missing_sires", [])))),
        "missing_dams": int(meta.get("missing_dams_count", len(errors.get("missing_dams", [])))),
        "self_parent_ids": int(meta.get("self_parent_count", len(errors.get("self_parent_ids", [])))),
        "dual_role_ids": int(meta.get("dual_role_count", len(errors.get("dual_role_ids", [])))),
        "sex_mismatch": len(errors.get("sex_mismatch_sire_ids", [])) + len(errors.get("sex_mismatch_dam_ids", [])),
        "birthdate_order_errors": len(errors.get("birthdate_invalid_offspring_ids", [])),
        "loop_cycles": int(meta.get("loop_count", len(errors.get("loop_cycles", [])))),
    }


def autofix_summary_section(
    autofix: dict[str, object] | None,
    app=None,
    *,
    affected_path: Path | None = None,
    report_dir: Path | None = None,
    generated_paths: list[str] | None = None,
) -> str:
    data = autofix or {}

    def count(key: str) -> int:
        try:
            return int(data.get(key, 0))
        except (TypeError, ValueError):
            return 0

    def value_list(key: str) -> list:
        value = data.get(key, [])
        return value if isinstance(value, list) else []

    def sample(items: list[str], *, limit: int = 6) -> str:
        if not items:
            return report_text("none", app)
        shown = items[:limit]
        suffix = f"; +{len(items) - limit} more" if len(items) > limit else ""
        return "; ".join(shown) + suffix

    def row_text(item: object) -> str:
        return f"row {item.get('row')}" if isinstance(item, dict) else str(item)

    def duplicate_text(item: object) -> str:
        if isinstance(item, dict):
            return f"{item.get('id')} (row {item.get('row')})"
        return str(item)

    def field_text(item: object) -> str:
        if isinstance(item, dict):
            return f"{item.get('id')} {item.get('field')}"
        return str(item)

    def loop_text(item: object) -> str:
        if not isinstance(item, dict):
            return str(item)
        cycle = " -> ".join(str(part) for part in item.get("cycle", []))
        return f"{item.get('child')} {item.get('field')} -> {item.get('parent')} ({cycle})"

    lines = [f"## {report_text('autofix_summary', app)}", ""]

    lines.append(f"### {report_text('qc_after_autofix', app)}")
    post_qc = data.get("post_qc", {})
    qc_rows = [
        ("duplicate_ids", "duplicate_ids"),
        ("missing_sires", "missing_sires"),
        ("missing_dams", "missing_dams"),
        ("self_parent_records", "self_parent_ids"),
        ("dual_role_ids", "dual_role_ids"),
        ("sex_mismatch", "sex_mismatch"),
        ("birthdate_order_errors", "birthdate_order_errors"),
        ("loop_count", "loop_cycles"),
    ]
    for label_key, detail_key in qc_rows:
        try:
            count_value = int(post_qc.get(detail_key, 0))
        except (AttributeError, TypeError, ValueError):
            count_value = 0
        lines.append(f"- {report_text(label_key, app)}: {count_value:,}")

    detail_groups = [
        ("removed_rows", [row_text(item) for item in value_list("missing_id_rows")]),
        (
            "duplicate_ids",
            [
                f"{report_text('kept_record', app)}: {duplicate_text(item)}"
                for item in value_list("kept_duplicate_records")
            ]
            + [
                f"{report_text('removed_duplicates', app)}: {duplicate_text(item)}"
                for item in value_list("duplicate_records")
            ],
        ),
        ("missing_parents", [str(item) for item in value_list("missing_parent_ids")]),
        ("self_parent", [field_text(item) for item in value_list("self_parent_records")]),
        ("birthdate_order_errors", [field_text(item) for item in value_list("birthdate_records")]),
        ("loops", [loop_text(item) for item in value_list("loop_breaks")]),
    ]
    affected_relative = ""
    if affected_path is not None and report_dir is not None:
        needs_file = any(len(items) > AUTOFIX_AFFECTED_INLINE_LIMIT for _title_key, items in detail_groups)
        if needs_file:
            detail_lines = [
                report_text("autofix_affected_file_title", app),
                "",
            ]
            for title_key, items in detail_groups:
                detail_lines.append(f"## {report_text(title_key, app)}")
                if items:
                    detail_lines.extend(f"- {item}" for item in items)
                else:
                    detail_lines.append(f"- {report_text('none', app)}")
                detail_lines.append("")
            affected_path.parent.mkdir(parents=True, exist_ok=True)
            affected_path.write_text("\n".join(detail_lines).rstrip() + "\n", encoding="utf-8", newline="\n")
            if generated_paths is not None:
                generated_paths.append(str(affected_path))
            affected_relative = Path(os.path.relpath(affected_path, report_dir)).as_posix()

    def affected_cell(items: list[str]) -> str:
        if affected_relative and len(items) > AUTOFIX_AFFECTED_INLINE_LIMIT:
            return f"[{report_text('open_autofix_affected', app)}]({affected_relative})"
        return sample(items)

    detail_by_key = {title_key: items for title_key, items in detail_groups}
    fix_rows = [
        (
            "missing_ids",
            "removed_rows",
            count("missing_ids"),
            affected_cell(detail_by_key["removed_rows"]),
            report_text("method_missing_ids_short", app),
        ),
        (
            "duplicates",
            "duplicate_ids",
            count("duplicates"),
            affected_cell(detail_by_key["duplicate_ids"]),
            report_text("method_duplicates_short", app),
        ),
        (
            "missing_parents",
            "missing_parents",
            count("missing_parents"),
            affected_cell(detail_by_key["missing_parents"]),
            report_text("method_missing_parents_short", app),
        ),
        (
            "self_parent",
            "self_parent",
            count("self_parent"),
            affected_cell(detail_by_key["self_parent"]),
            report_text("method_self_parent_short", app),
        ),
        (
            "birthdate",
            "birthdate_order_errors",
            count("birthdate"),
            affected_cell(detail_by_key["birthdate_order_errors"]),
            report_text("method_birthdate_short", app),
        ),
        (
            "loops",
            "loops",
            count("loops"),
            affected_cell(detail_by_key["loops"]),
            report_text("method_loops_short", app),
        ),
    ]
    lines.extend(
        [
            "",
            f"### {report_text('autofix_applied_fixes', app)}",
            (
                f"| {report_text('autofix_issue', app)} | {report_text('autofix_status', app)} | "
                f"{report_text('autofix_count', app)} | {report_text('autofix_affected', app)} | "
                f"{report_text('autofix_method_short', app)} |"
            ),
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for action_key, issue_key, action_count, affected, method in fix_rows:
        status = report_text("pass", app) if action_count > 0 else report_text("pass_no_fix", app)
        method_text = method if action_count > 0 else report_text("not_applicable", app)
        affected_text = affected if action_count > 0 else report_text("none", app)
        lines.append(
            f"| {report_text(issue_key, app)} | {status} | {action_count:,} | {affected_text} | {method_text} |"
        )
    return "\n".join(lines)


def yaml_quote(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def report_front_matter(input_path: Path, generated_at: str, app=None) -> str:
    title = report_text("report_title_with_source", app, source=input_path.stem)
    return "\n".join(
        [
            "---",
            f"title: {yaml_quote(title)}",
            f"created: {yaml_quote(generated_at)}",
            "tags: [pedigree, inbreeding, plugin-report, plugin-pedigree-analysis, pedigree-analysis]",
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


def trend_chart(records: list[dict], prefer_birthdate: bool, app=None) -> str:
    trend_type, rows = trend_rows(records, prefer_birthdate)
    if not rows:
        return report_text("no_trend_values", app)
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
    return markdown_table(chart_rows, app)


def group_analysis(records: list[dict], prefer_birthdate: bool, app=None) -> str:
    groups: dict[str, list[dict]] = {}
    for row in records:
        group = str(row.get("group") or "").strip()
        if group:
            groups.setdefault(group, []).append(row)
    if not groups:
        return report_text("no_group_column", app)

    lines = []
    for group in sorted(groups):
        rows = groups[group]
        values = [value for row in rows if (value := finite_inbreeding(row)) is not None]
        stats = values_stats(values)
        lines.extend(
            [
                f"### {report_text('group', app)}: {group}",
                f"- {report_text('individuals_total', app)}: {len(rows):,}",
                f"- {report_text('evaluated_individuals', app)}: {stats['total']:,}",
                f"- {report_text('inbreds', app)}: {sum(1 for value in values if value > 0):,}",
                f"- {report_text('mean_f', app)}: {float(stats['mean']):.8f}",
                f"- {report_text('sd_f', app)}: {float(stats['sd']):.8f}",
                f"- {report_text('min_f', app)}: {float(stats['min']):.8g}",
                f"- {report_text('max_f', app)}: {float(stats['max']):.8g}",
                "",
                f"#### {report_text('inbreeding_trend', app)}",
                trend_chart(rows, prefer_birthdate, app),
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def write_report(app, input_path: Path, selected: dict[str, str], result: dict) -> Path:
    def r(key: str, **kwargs: object) -> str:
        return report_text(key, app, **kwargs)

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
    autofix = result.get("autofix", {})
    if not isinstance(autofix, dict):
        autofix = {}
    autofix.setdefault("post_qc", post_autofix_qc(result))
    generated_tables: list[str] = []

    def linked(section: str, rows: list[dict]) -> str:
        content, paths = table_link(section, rows, tables_dir, report_dir, base, app)
        generated_tables.extend(paths)
        return content

    all_inbreeding_rows = list(inbreeding["records"])
    all_inbreeding_path = tables_dir / f"{base}_inbreeding_all.csv"
    write_csv(all_inbreeding_path, all_inbreeding_rows)
    generated_tables.append(str(all_inbreeding_path))
    affected_path = tables_dir / f"{base}_autofix_affected_records.txt"
    repaired_path = tables_dir / f"{base}_repaired_pedigree.txt"
    write_repaired_pedigree_txt(repaired_path, all_inbreeding_rows, selected)
    generated_tables.append(str(repaired_path))

    stats_all = inbreeding["stats_all"]
    stats_inbred = inbreeding["stats_inbred"]
    prefer_birthdate_trend = selected.get("birthdate") != MISSING_OPTION
    lines = [
        report_front_matter(input_path, generated_at, app),
        "",
        f"# {r('report_title')}",
        "",
        f"## {r('input')}",
        f"- {r('file')}: `{input_path}`",
        f"- {r('generated_at')}: {generated_at}",
        f"- {r('progeny_column')}: `{selected['progeny']}`",
        f"- {r('sire_column')}: `{selected['sire']}`",
        f"- {r('dam_column')}: `{selected['dam']}`",
        f"- {r('group_column')}: `{selected['group']}`",
        f"- {r('sex_column')}: `{selected['sex']}`",
        f"- {r('birthdate_column')}: `{selected['birthdate']}`",
        "",
        autofix_summary_section(
            autofix,
            app,
            affected_path=affected_path,
            report_dir=report_dir,
            generated_paths=generated_tables,
        ),
        "",
        repaired_pedigree_section(repaired_path, report_dir, app),
        f"## {r('basic_statistics')}",
        f"- {r('individuals_total')}: {meta['total']:,}",
        f"- {r('founders')}: {meta.get('founders', 0):,}",
        f"- {r('non_founders')}: {meta.get('non_founders', meta['total'] - meta.get('founders', 0)):,}",
        f"- {r('with_both_parents')}: {meta.get('with_both_parents', 0):,}",
        f"- {r('only_known_sire')}: {meta.get('only_sire', 0):,}",
        f"- {r('only_known_dam')}: {meta.get('only_dam', 0):,}",
        "",
        f"## {r('parent_statistics')}",
        f"- {r('sires_total')}: {parent_stats.get('sires_total', 0):,}",
        f"  - {r('progeny')}: {parent_stats.get('sire_progeny', 0):,}",
        f"- {r('dams_total')}: {parent_stats.get('dams_total', 0):,}",
        f"  - {r('progeny')}: {parent_stats.get('dam_progeny', 0):,}",
        f"- {r('individuals_with_progeny')}: {parent_stats.get('individuals_with_progeny', 0):,}",
        f"- {r('individuals_without_progeny')}: {parent_stats.get('individuals_without_progeny', 0):,}",
        "",
        f"## {r('founder_statistics')}",
        f"- {r('founders')}: {founder_stats.get('founders', meta.get('founders', 0)):,}",
        f"  - {r('progeny')}: {founder_stats.get('progeny', 0):,}",
        f"  - {r('sires')}: {founder_stats.get('sires', 0):,}",
        f"    - {r('progeny')}: {founder_stats.get('sire_progeny', 0):,}",
        f"  - {r('dams')}: {founder_stats.get('dams', 0):,}",
        f"    - {r('progeny')}: {founder_stats.get('dam_progeny', 0):,}",
        f"  - {r('with_no_progeny')}: {founder_stats.get('with_no_progeny', 0):,}",
        "",
        f"## {r('non_founder_statistics')}",
        f"- {r('non_founders')}: {non_founder_stats.get('non_founders', meta.get('non_founders', 0)):,}",
        f"  - {r('sires')}: {non_founder_stats.get('sires', 0):,}",
        f"    - {r('progeny')}: {non_founder_stats.get('sire_progeny', 0):,}",
        f"  - {r('dams')}: {non_founder_stats.get('dams', 0):,}",
        f"    - {r('progeny')}: {non_founder_stats.get('dam_progeny', 0):,}",
        f"  - {r('only_known_sire')}: {non_founder_stats.get('only_sire', meta.get('only_sire', 0)):,}",
        f"  - {r('only_known_dam')}: {non_founder_stats.get('only_dam', meta.get('only_dam', 0)):,}",
        f"  - {r('known_sire_and_dam')}: {non_founder_stats.get('with_both_parents', meta.get('with_both_parents', 0)):,}",
        "",
        f"## {r('full_sib_groups')}",
        f"- {r('full_sib_groups_count')}: {full_sib.get('groups', 0):,}",
        f"- {r('average_family_size')}: {full_sib.get('average_family_size', 0.0):.3f}",
        f"  - {r('maximum')}: {full_sib.get('maximum', 0):,}",
        f"  - {r('minimum')}: {full_sib.get('minimum', 0):,}",
        "",
        f"## {r('inbreeding_statistics')}",
        f"- {r('evaluated_individuals')}: {stats_all.get('total', 0):,}",
        f"- {r('inbreds_total')}: {stats_inbred.get('total', 0):,}",
        f"- {r('inbreds_evaluated')}: {stats_inbred.get('total', 0):,}",
        "",
        f"### {r('distribution_inbreeding')}",
        markdown_table(inbreeding["distribution"], app),
        "",
        f"## {r('summary_statistics')}",
        f"- {r('summary_a')}: {meta['total']:,}",
        f"- {r('summary_b')}: {stats_inbred.get('total', 0):,}",
        f"- {r('summary_c')}: {meta.get('founders', 0):,}",
        f"- {r('summary_d')}: {meta.get('with_both_parents', 0):,}",
        f"- {r('summary_e')}: {parent_stats.get('individuals_without_progeny', 0):,}",
        f"- {r('summary_g')}: {stats_all.get('mean', 0.0):.8f}",
        f"- {r('summary_h')}: {stats_inbred.get('mean', 0.0):.8f}",
        f"- {r('summary_i')}: {stats_all.get('max', 0.0):.8g}",
        f"- {r('summary_j')}: {stats_all.get('min', 0.0):.8g}",
        "",
        f"## {r('lap')}",
        markdown_table(lap.get("distribution", []), app),
        "",
        f"{r('mean_generation_depth')}: {lap.get('mean_generation_depth', 0.0):.2f}",
        "",
        f"## {r('inbreeding_trend')}",
        f"{r('trend_basis')}: {'BirthDate' if prefer_birthdate_trend else 'LAP'}",
        "",
        trend_chart(all_inbreeding_rows, prefer_birthdate_trend, app),
        "",
        f"### {r('top_high_inbreeding')}",
        markdown_table(inbreeding["top_high"], app),
        "",
        f"### {r('full_inbreeding_table')}",
        f"[{r('open_all_inbreeding')}]({Path(os.path.relpath(all_inbreeding_path, report_dir)).as_posix()})",
        "",
        f"## {r('group_summary')}",
        markdown_table(result["group_summary"], app) if result["group_summary"] else r("no_group_column"),
        "",
        f"## {r('group_analysis')}",
        group_analysis(all_inbreeding_rows, prefer_birthdate_trend, app),
        "",
        f"## {r('generated_files')}",
        *[f"- `{path}`" for path in generated_tables],
        "",
    ]
    safe_write_text(report_path, "\n".join(lines), encoding="utf-8", newline="\n", workspace_root=root)
    return report_path


def stats_text(stats: dict, app=None) -> str:
    if not stats or stats.get("total", 0) == 0:
        return report_text("no_valid_values", app)
    return "\n".join(
        [
            f"- {report_text('total', app)}: {stats['total']:,}",
            f"- {report_text('min', app)}: {stats['min']:.6f}",
            f"- {report_text('max', app)}: {stats['max']:.6f}",
            f"- {report_text('mean', app)}: {stats['mean']:.6f}",
            f"- {report_text('sd', app)}: {stats['sd']:.6f}",
        ]
    )


def markdown_table(rows: list[dict], app=None) -> str:
    if not rows:
        return report_text("none", app)
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
