import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writeonside_app.config import AppConfig, load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_load_config_clamps_width_and_normalizes_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "width": 1200,
                        "theme": "",
                        "attachments_folder": "\\Attachments\\",
                    }
                ),
                encoding="utf-8",
            )
            with patch("writeonside_app.config.APP_DATA_DIR", config_dir), patch(
                "writeonside_app.config.CONFIG_FILE", config_file
            ):
                config = load_config()
            self.assertEqual(900, config.width)
            self.assertEqual("graphite", config.theme)
            self.assertEqual("Attachments", config.attachments_folder)

    def test_load_config_normalizes_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text(json.dumps({"language": "zh-CN"}), encoding="utf-8")
            with patch("writeonside_app.config.APP_DATA_DIR", config_dir), patch(
                "writeonside_app.config.CONFIG_FILE", config_file
            ):
                config = load_config()
            self.assertEqual("zh", config.language)

    def test_save_config_writes_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            with patch("writeonside_app.config.APP_DATA_DIR", config_dir), patch(
                "writeonside_app.config.CONFIG_FILE", config_file
            ):
                save_config(AppConfig(width=480, theme="nord"))
                config = load_config()
            self.assertEqual(480, config.width)
            self.assertEqual("nord", config.theme)


if __name__ == "__main__":
    unittest.main()
