import unittest
from unittest.mock import patch

from writeonside_app.layout_metrics import (
    clamp_layout_widths,
    default_panel_width,
    panel_width_limits,
)


class LayoutMetricsTests(unittest.TestCase):
    def test_panel_limits_scale_with_work_area(self) -> None:
        minimum, maximum = panel_width_limits(2000)
        self.assertEqual(360, minimum)
        self.assertEqual(1000, maximum)
        self.assertEqual(560, default_panel_width(2000))

    def test_clamp_layout_widths_respects_screen(self) -> None:
        panel_width, explorer_width = clamp_layout_widths(1500, 500, 1600)
        self.assertEqual(panel_width_limits(1600)[1], panel_width)
        self.assertEqual(352, explorer_width)

    def test_load_config_clamps_width_to_screen_ratio(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        from writeonside_app.config import load_config

        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text(json.dumps({"width": 1200}), encoding="utf-8")
            with patch("writeonside_app.config.APP_DATA_DIR", config_dir), patch(
                "writeonside_app.config.CONFIG_FILE", config_file
            ), patch("writeonside_app.config.work_area_width", return_value=1920):
                config = load_config()
            self.assertEqual(960, config.width)


if __name__ == "__main__":
    unittest.main()
