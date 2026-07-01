import tempfile
import unittest
from pathlib import Path

from writeonside_app.config import AppConfig, load_config
from writeonside_app.plugins import (
    BUILTIN_PLUGINS,
    apply_default_disabled_plugins,
    available_plugins,
    disable_plugin,
    enable_plugin,
    enabled_plugins,
    plugin_status,
    remove_plugin,
    restore_plugin,
)


class PluginTests(unittest.TestCase):
    def test_builtin_plugins_are_enabled_by_default(self) -> None:
        config = AppConfig()
        apply_default_disabled_plugins(config)

        enabled_ids = {plugin.id for plugin in enabled_plugins(config)}
        for plugin in BUILTIN_PLUGINS:
            if plugin.entrypoint:
                self.assertIn(plugin.id, enabled_ids, plugin.id)
            else:
                self.assertNotIn(plugin.id, enabled_ids, plugin.id)
        self.assertEqual("enabled", plugin_status(config, "pedigree_analysis"))
        self.assertEqual("disabled", plugin_status(config, "calendar"))

    def test_plugin_can_be_disabled_removed_and_restored(self) -> None:
        config = AppConfig()
        plugin_id = BUILTIN_PLUGINS[0].id

        disable_plugin(config, plugin_id)
        self.assertEqual("disabled", plugin_status(config, plugin_id))
        self.assertNotIn(plugin_id, [plugin.id for plugin in enabled_plugins(config)])

        enable_plugin(config, plugin_id)
        self.assertEqual("enabled", plugin_status(config, plugin_id))

        remove_plugin(config, plugin_id)
        self.assertEqual("removed", plugin_status(config, plugin_id))
        self.assertNotIn(plugin_id, [plugin.id for plugin in available_plugins(config)])

        restore_plugin(config, plugin_id)
        self.assertEqual("enabled", plugin_status(config, plugin_id))

    def test_unknown_plugin_ids_are_ignored(self) -> None:
        config = AppConfig()

        disable_plugin(config, "missing")
        remove_plugin(config, "missing")
        restore_plugin(config, "missing")

        self.assertEqual([], config.disabled_plugins)
        self.assertEqual([], config.removed_plugins)

    def test_load_config_disables_unsupported_plugins_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            from writeonside_app import config as config_module

            original_dir = config_module.APP_DATA_DIR
            original_file = config_module.CONFIG_FILE
            config_module.APP_DATA_DIR = Path(temp_dir)
            config_module.CONFIG_FILE = Path(temp_dir) / "config.json"
            try:
                config = load_config()
            finally:
                config_module.APP_DATA_DIR = original_dir
                config_module.CONFIG_FILE = original_file

        self.assertEqual("disabled", plugin_status(config, "calendar"))
        self.assertEqual("enabled", plugin_status(config, "color_picker"))

    def test_plugin_shortcuts_are_loaded_and_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            from writeonside_app import config as config_module

            original_dir = config_module.APP_DATA_DIR
            original_file = config_module.CONFIG_FILE
            config_module.APP_DATA_DIR = Path(temp_dir)
            config_module.CONFIG_FILE = Path(temp_dir) / "config.json"
            try:
                config_module.CONFIG_FILE.write_text(
                    '{"plugin_shortcuts": {"Sticky Notes": "CTRL + ALT + S", "missing": "ctrl+shift+m", "stats": "ctrl"}}',
                    encoding="utf-8",
                )
                config = load_config()
            finally:
                config_module.APP_DATA_DIR = original_dir
                config_module.CONFIG_FILE = original_file

        self.assertEqual({"sticky_notes": "ctrl+alt+s", "missing": "ctrl+shift+m"}, config.plugin_shortcuts)


if __name__ == "__main__":
    unittest.main()
