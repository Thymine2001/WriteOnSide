import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writeonside_app.config import AppConfig, load_config, save_config
from writeonside_app.file_labels import COLOR_TAG_PALETTE


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
            ), patch("writeonside_app.config.work_area_width", return_value=1920):
                config = load_config()
            self.assertEqual(960, config.width)
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

    def test_load_config_migrates_tokyo_night_theme_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text(json.dumps({"theme": "tokyo_night"}), encoding="utf-8")
            with patch("writeonside_app.config.APP_DATA_DIR", config_dir), patch(
                "writeonside_app.config.CONFIG_FILE", config_file
            ):
                config = load_config()
            self.assertEqual("mid_night", config.theme)

    def test_load_config_preserves_nav_width_setting(self) -> None:
        for nav_width in (4, 10, 24):
            with self.subTest(nav_width=nav_width), tempfile.TemporaryDirectory() as temp_dir:
                config_dir = Path(temp_dir)
                config_file = config_dir / "config.json"
                config_file.write_text(json.dumps({"nav_width": nav_width}), encoding="utf-8")
                with patch("writeonside_app.config.APP_DATA_DIR", config_dir), patch(
                    "writeonside_app.config.CONFIG_FILE", config_file
                ):
                    config = load_config()
            self.assertEqual(nav_width, config.nav_width)

    def test_load_config_normalizes_file_label_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "tag_view_mode": "both",
                        "show_created_dates_in_tags": True,
                        "file_color_tags": {
                            "C:/Notes/A.md": [*COLOR_TAG_PALETTE, "#FFFFFF"],
                        },
                        "custom_tag_color": "#12abef",
                        "pinned_notes": ["C:/Notes/A.md", "c:/notes/a.md"],
                    }
                ),
                encoding="utf-8",
            )
            with patch("writeonside_app.config.APP_DATA_DIR", config_dir), patch(
                "writeonside_app.config.CONFIG_FILE", config_file
            ):
                config = load_config()
            self.assertEqual("both", config.tag_view_mode)
            self.assertTrue(config.show_created_dates_in_tags)
            self.assertEqual(list(COLOR_TAG_PALETTE[:3]), config.file_color_tags["C:/Notes/A.md"])
            self.assertEqual("#12ABEF", config.custom_tag_color)
            self.assertEqual(["C:/Notes/A.md"], config.pinned_notes)

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
