import tempfile
import unittest
from pathlib import Path

from writeonside_app.builtin_plugins.pedigree_analysis import (
    auto_fix_pedigree_rows,
    detect_parent_cycles,
    read_table,
    trend_rows,
    write_report,
)


class DummyApp:
    def __init__(self, workspace: Path, language: str = "en") -> None:
        self.workspace = workspace
        self.config = type("Config", (), {"language": language})()

    def _workspace_dir(self) -> Path:
        return self.workspace


class PedigreePluginTests(unittest.TestCase):
    def test_read_table_detects_csv_headers_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pedigree.csv"
            path.write_text("Progeny,Sire,Dam\nA,0,0\nB,A,0\n", encoding="utf-8")

            headers, rows, delimiter = read_table(path)

        self.assertEqual(["Progeny", "Sire", "Dam"], headers)
        self.assertEqual(",", delimiter)
        self.assertEqual("B", rows[1]["Progeny"])

    def test_write_report_creates_markdown_and_detail_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "pedigree.csv"
            input_path.write_text("Progeny,Sire,Dam\nA,0,0\nB,A,0\n", encoding="utf-8")
            result = {
                "meta": {
                    "total": 2,
                    "founders": 1,
                    "non_founders": 1,
                    "with_both_parents": 0,
                    "only_sire": 1,
                    "only_dam": 0,
                    "duplicate_count": 0,
                    "missing_sires_count": 0,
                    "missing_dams_count": 0,
                    "self_parent_count": 0,
                    "loop_count": 0,
                },
                "parent_stats": {
                    "sires_total": 1,
                    "sire_progeny": 1,
                    "dams_total": 0,
                    "dam_progeny": 0,
                    "individuals_with_progeny": 1,
                    "individuals_without_progeny": 1,
                },
                "founder_stats": {
                    "founders": 1,
                    "progeny": 1,
                    "sires": 1,
                    "sire_progeny": 1,
                    "dams": 0,
                    "dam_progeny": 0,
                    "with_no_progeny": 0,
                },
                "non_founder_stats": {
                    "non_founders": 1,
                    "sires": 0,
                    "sire_progeny": 0,
                    "dams": 0,
                    "dam_progeny": 0,
                    "only_sire": 1,
                    "only_dam": 0,
                    "with_both_parents": 0,
                },
                "full_sib": {"groups": 0, "average_family_size": 0.0, "maximum": 0, "minimum": 0},
                "lap": {
                    "mean_generation_depth": 0.5,
                    "distribution": [{"depth": 0, "count": 1}, {"depth": 1, "count": 1}],
                },
                "errors": {
                    "duplicate_ids": [],
                    "missing_sires": [],
                    "missing_dams": [],
                    "self_parent_ids": [],
                    "dual_role_ids": [],
                    "sex_mismatch_sire_ids": [],
                    "sex_mismatch_dam_ids": [],
                    "birthdate_invalid_offspring_ids": [],
                    "birthdate_invalid_sire_ids": [],
                    "birthdate_invalid_dam_ids": [],
                    "loop_cycles": [],
                },
                "inbreeding": {
                    "records": [
                        {
                            "id": "A",
                            "sire": "0",
                            "dam": "0",
                            "group": "G1",
                            "birthdate": "2020-01-01",
                            "lap_depth": 0,
                            "inbreeding": 0.0,
                        },
                        {
                            "id": "B",
                            "sire": "A",
                            "dam": "0",
                            "group": "G2",
                            "birthdate": "",
                            "lap_depth": 1,
                            "inbreeding": 0.0,
                        },
                    ],
                    "stats_all": {"total": 2, "min": 0.0, "max": 0.0, "mean": 0.0, "sd": 0.0},
                    "stats_inbred": {"total": 0},
                    "distribution": [{"range": "F = 0", "count": 2}],
                    "top_high": [{"id": "A", "inbreeding": 0.0}],
                },
                "group_summary": [
                    {"group": "G1", "total": 1, "mean": 0.0, "max": 0.0},
                    {"group": "G2", "total": 1, "mean": 0.0, "max": 0.0},
                ],
                "autofix": {
                    "missing_ids": 1,
                    "duplicates": 1,
                    "missing_parents": 1,
                    "self_parent": 1,
                    "birthdate": 1,
                    "loops": 1,
                    "missing_id_rows": [{"row": 3}],
                    "kept_duplicate_records": [{"id": "A", "row": 1}],
                    "duplicate_records": [{"id": "A", "row": 2}],
                    "missing_parent_ids": ["P"],
                    "self_parent_records": [{"id": "B", "field": "Sire"}],
                    "birthdate_records": [{"id": "B", "field": "BirthDate"}],
                    "loop_breaks": [{"child": "C", "parent": "D", "field": "Dam", "cycle": ["C", "D", "C"]}],
                },
            }
            selected = {
                "progeny": "Progeny",
                "sire": "Sire",
                "dam": "Dam",
                "group": "Group",
                "sex": "(none)",
                "birthdate": "BirthDate",
            }

            report_path = write_report(DummyApp(workspace), input_path, selected, result)

            self.assertTrue(report_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertTrue(report.startswith("---\n"))
            self.assertIn(
                "tags: [pedigree, inbreeding, plugin-report, plugin-pedigree-analysis, pedigree-analysis]",
                report,
            )
            self.assertNotIn("  - pedigree", report)
            self.assertIn("plugin: pedigree_analysis", report)
            self.assertIn("# Pedigree QC & Inbreeding Report", report)
            self.assertIn("## Parent Statistics", report)
            self.assertIn("## Full-Sib Groups", report)
            self.assertIn("## Longest Ancestral Path (LAP)", report)
            self.assertIn("Mean generation depth: 0.50", report)
            self.assertIn("## Inbreeding Trend", report)
            self.assertIn("mean_plot", report)
            self.assertNotIn("sd_plot", report)
            self.assertIn("### Group: G1", report)
            self.assertIn("### Group: G2", report)
            self.assertIn("## Repaired Pedigree", report)
            self.assertIn("Missing values are written as `0`.", report)
            self.assertIn("Open repaired pedigree TXT", report)
            self.assertNotIn("### Preview", report)
            self.assertIn("Open all inbreeding records", report)
            self.assertIn("## Auto-fix summary", report)
            self.assertIn("## Repaired Pedigree", report)
            self.assertIn("### QC status after auto-fix", report)
            self.assertIn("### Applied fixes", report)
            self.assertIn("| Issue | Status | Count | Affected records | Method |", report)
            self.assertIn("| Removed rows | ✔ Pass | 1 | row 3 | Remove rows without a valid Progeny ID. |", report)
            self.assertIn("Missing Parents | ✔ Pass | 1 | P | Add missing parents as founder rows.", report)
            self.assertIn("Loops | ✔ Pass | 1 | C Dam -> D (C -> D -> C) | Clear one parent link", report)
            self.assertNotIn("#### Removed rows", report)
            self.assertNotIn("Auto-fix method:", report)
            self.assertNotIn("## Quality Control Summary", report)
            self.assertNotIn("## Data Quality Checks", report)
            csv_files = list((workspace / "Plugins" / "PedigreeAnalysis" / "tables").glob("*_inbreeding_all.csv"))
            self.assertEqual(1, len(csv_files))
            repaired_files = list((workspace / "Plugins" / "PedigreeAnalysis" / "tables").glob("*_repaired_pedigree.txt"))
            self.assertEqual(1, len(repaired_files))
            repaired = repaired_files[0].read_text(encoding="utf-8")
            self.assertIn("Progeny Sire Dam Group BirthDate", repaired)
            self.assertIn("B A 0 G2 0", repaired)

            large_input_path = workspace / "pedigree_large.csv"
            large_input_path.write_text("Progeny,Sire,Dam\nA,0,0\nB,A,0\n", encoding="utf-8")
            large_result = dict(result)
            large_autofix = dict(result["autofix"])
            large_autofix["missing_parents"] = 25
            large_autofix["missing_parent_ids"] = [f"P{index}" for index in range(25)]
            large_result["autofix"] = large_autofix
            large_report_path = write_report(DummyApp(workspace), large_input_path, selected, large_result)
            large_report = large_report_path.read_text(encoding="utf-8")
            self.assertIn("Open affected records TXT", large_report)
            affected_files = list((workspace / "Plugins" / "PedigreeAnalysis" / "tables").glob("*_autofix_affected_records.txt"))
            self.assertEqual(1, len(affected_files))
            affected_text = affected_files[0].read_text(encoding="utf-8")
            self.assertIn("Auto-fix affected records", affected_text)
            self.assertIn("## Missing Parents", affected_text)
            self.assertIn("- P24", affected_text)

            zh_report_path = write_report(DummyApp(workspace, language="zh"), input_path, selected, result)
            zh_report = zh_report_path.read_text(encoding="utf-8")

            self.assertIn("# 系谱质控与近交分析报告", zh_report)
            self.assertIn("## 亲本统计", zh_report)
            self.assertIn("## 修复后的系谱", zh_report)
            self.assertIn("缺失值写为 `0`。", zh_report)
            self.assertIn("### 分组: G1", zh_report)
            self.assertIn("打开全部近交记录", zh_report)

    def test_lap_trend_uses_numeric_order(self) -> None:
        records = [
            {"lap_depth": 1, "inbreeding": 0.01},
            {"lap_depth": 11, "inbreeding": 0.11},
            {"lap_depth": 2, "inbreeding": 0.02},
            {"lap_depth": 10, "inbreeding": 0.10},
            {"lap_depth": 9, "inbreeding": 0.09},
        ]

        trend_type, rows = trend_rows(records, prefer_birthdate=False)

        self.assertEqual("LAP", trend_type)
        self.assertEqual(["1", "2", "9", "10", "11"], [row["bucket"] for row in rows])

    def test_auto_fix_pedigree_rows_repairs_qc_inputs_before_analysis(self) -> None:
        selected = {
            "progeny": "Progeny",
            "sire": "Sire",
            "dam": "Dam",
            "group": "Group",
            "sex": "(none)",
            "birthdate": "BirthDate",
        }
        rows = [
            {"Progeny": "", "Sire": "0", "Dam": "0", "Group": "", "BirthDate": ""},
            {"Progeny": "A", "Sire": "0", "Dam": "0", "Group": "", "BirthDate": "2000-01-01"},
            {"Progeny": "A", "Sire": "P", "Dam": "0", "Group": "G1", "BirthDate": "2000-01-01"},
            {"Progeny": "B", "Sire": "B", "Dam": "0", "Group": "", "BirthDate": "2001-01-01"},
            {"Progeny": "Q", "Sire": "0", "Dam": "0", "Group": "", "BirthDate": "2010-01-01"},
            {"Progeny": "C", "Sire": "Q", "Dam": "0", "Group": "", "BirthDate": "2009-01-01"},
            {"Progeny": "M", "Sire": "X", "Dam": "0", "Group": "", "BirthDate": ""},
            {"Progeny": "D", "Sire": "E", "Dam": "0", "Group": "", "BirthDate": ""},
            {"Progeny": "E", "Sire": "D", "Dam": "0", "Group": "", "BirthDate": ""},
        ]

        fixed, summary = auto_fix_pedigree_rows(rows, selected)
        by_id = {row["Progeny"]: row for row in fixed}

        self.assertEqual(1, summary["missing_ids"])
        self.assertEqual(1, summary["duplicates"])
        self.assertEqual(2, summary["missing_parents"])
        self.assertEqual(1, summary["self_parent"])
        self.assertEqual(1, summary["birthdate"])
        self.assertEqual(1, summary["loops"])
        self.assertEqual("P", by_id["A"]["Sire"])
        self.assertEqual("G1", by_id["A"]["Group"])
        self.assertEqual("0", by_id["B"]["Sire"])
        self.assertEqual("0", by_id["C"]["BirthDate"])
        self.assertEqual({"0"}, {by_id["P"]["Sire"], by_id["P"]["Dam"]})
        self.assertEqual({"0"}, {by_id["X"]["Sire"], by_id["X"]["Dam"]})
        self.assertEqual([], detect_parent_cycles(fixed, selected))


if __name__ == "__main__":
    unittest.main()
