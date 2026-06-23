import unittest

from writeonside_app.config import AppConfig
from writeonside_app.plugins import (
    BUILTIN_PLUGINS,
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

        self.assertEqual(BUILTIN_PLUGINS, enabled_plugins(config))
        self.assertEqual("enabled", plugin_status(config, BUILTIN_PLUGINS[0].id))
        self.assertEqual("pedigree_analysis", BUILTIN_PLUGINS[0].id)
        self.assertTrue(BUILTIN_PLUGINS[0].entrypoint)

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


if __name__ == "__main__":
    unittest.main()
