from __future__ import annotations

import tempfile
import unittest
import zipfile
import logging
from pathlib import Path
from unittest.mock import patch

from writeonside_app import diagnostics


class DiagnosticsTests(unittest.TestCase):
    def test_export_diagnostic_report_includes_logs_config_and_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log_dir = root / "Logs"
            report_dir = root / "DiagnosticReports"
            config_file = root / "config.json"
            log_dir.mkdir()
            config_file.write_text('{"theme": "graphite"}', encoding="utf-8")
            (log_dir / "writeonside.log").write_text("log line\n", encoding="utf-8")
            (log_dir / "startup_failure.txt").write_text("failure\n", encoding="utf-8")
            target = root / "report.zip"

            with patch.object(diagnostics, "APP_DATA_DIR", root), patch.object(
                diagnostics, "CONFIG_FILE", config_file
            ), patch.object(diagnostics, "LOG_DIR", log_dir), patch.object(
                diagnostics, "REPORT_DIR", report_dir
            ), patch.object(
                diagnostics, "LOG_FILE", log_dir / "writeonside.log"
            ), patch.object(
                diagnostics, "STARTUP_FAILURE_FILE", log_dir / "startup_failure.txt"
            ):
                report = diagnostics.export_diagnostic_report(target)

            self.assertEqual(target, report)
            with zipfile.ZipFile(report) as archive:
                names = set(archive.namelist())
            logger = logging.getLogger("writeonside")
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
            diagnostics._configured = False
            self.assertIn("environment.json", names)
            self.assertIn("config.json", names)
            self.assertIn("startup_failure.txt", names)
            self.assertTrue(any(name.startswith("logs/") for name in names))


if __name__ == "__main__":
    unittest.main()
