import tempfile
import unittest
from pathlib import Path

from writeonside_app.builtin_plugins.pedigree_analysis import read_table, trend_rows, write_report


class DummyApp:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

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
            csv_files = list((workspace / "Plugins" / "PedigreeAnalysis" / "tables").glob("*_inbreeding_all.csv"))
            self.assertEqual(1, len(csv_files))
            repaired_files = list((workspace / "Plugins" / "PedigreeAnalysis" / "tables").glob("*_repaired_pedigree.txt"))
            self.assertEqual(1, len(repaired_files))
            repaired = repaired_files[0].read_text(encoding="utf-8")
            self.assertIn("Progeny Sire Dam Group BirthDate", repaired)
            self.assertIn("B A 0 G2 0", repaired)

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


if __name__ == "__main__":
    unittest.main()
