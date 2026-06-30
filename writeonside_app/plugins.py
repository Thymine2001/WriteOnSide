from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig, normalize_plugin_ids


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name_key: str
    description_key: str
    icon: str
    version: str = "0.1.0"
    entrypoint: str = ""


BUILTIN_PLUGINS: tuple[PluginManifest, ...] = (
    PluginManifest(
        "pedigree_analysis",
        "plugins.pedigree.name",
        "plugins.pedigree.description",
        "🧬",
        entrypoint="writeonside_app.builtin_plugins.pedigree_analysis:run",
    ),
    PluginManifest(
        "sticky_notes",
        "plugins.sticky.name",
        "plugins.sticky.description",
        "🗒",
        entrypoint="writeonside_app.builtin_plugins.sticky_notes:run",
    ),
    PluginManifest("calendar", "plugins.placeholder.calendar", "plugins.description.calendar", "📅"),
    PluginManifest("deep_search", "plugins.placeholder.search", "plugins.description.search", "🔎"),
    PluginManifest(
        "organizer",
        "plugins.attachment_organizer.name",
        "plugins.attachment_organizer.description",
        "🗂",
        entrypoint="writeonside_app.builtin_plugins.attachment_organizer:run",
    ),
    PluginManifest("stats", "plugins.placeholder.stats", "plugins.description.stats", "📊"),
    PluginManifest("sync", "plugins.placeholder.sync", "plugins.description.sync", "🔁"),
    PluginManifest("extensions", "plugins.placeholder.extensions", "plugins.description.extensions", "🧩"),
    PluginManifest("themes", "plugins.placeholder.theme", "plugins.description.theme", "🎨"),
    PluginManifest("templates", "plugins.placeholder.templates", "plugins.description.templates", "📝"),
    PluginManifest("security", "plugins.placeholder.security", "plugins.description.security", "🔐"),
    PluginManifest("export", "plugins.placeholder.export", "plugins.description.export", "📦"),
    PluginManifest("automation", "plugins.placeholder.automation", "plugins.description.automation", "⚙"),
)

BUILTIN_PLUGIN_IDS = frozenset(plugin.id for plugin in BUILTIN_PLUGINS)


def plugin_by_id(plugin_id: str) -> PluginManifest | None:
    normalized = normalize_plugin_ids([plugin_id])
    if not normalized:
        return None
    target = normalized[0]
    return next((plugin for plugin in BUILTIN_PLUGINS if plugin.id == target), None)


def available_plugins(config: AppConfig) -> tuple[PluginManifest, ...]:
    removed = set(normalize_plugin_ids(config.removed_plugins))
    return tuple(plugin for plugin in BUILTIN_PLUGINS if plugin.id not in removed)


def enabled_plugins(config: AppConfig) -> tuple[PluginManifest, ...]:
    disabled = set(normalize_plugin_ids(config.disabled_plugins))
    return tuple(plugin for plugin in available_plugins(config) if plugin.id not in disabled)


def removed_plugins(config: AppConfig) -> tuple[PluginManifest, ...]:
    removed = set(normalize_plugin_ids(config.removed_plugins))
    return tuple(plugin for plugin in BUILTIN_PLUGINS if plugin.id in removed)


def plugin_status(config: AppConfig, plugin_id: str) -> str:
    normalized = normalize_plugin_ids([plugin_id])
    if not normalized:
        return "unknown"
    target = normalized[0]
    if target not in BUILTIN_PLUGIN_IDS:
        return "unknown"
    if target in set(normalize_plugin_ids(config.removed_plugins)):
        return "removed"
    if target in set(normalize_plugin_ids(config.disabled_plugins)):
        return "disabled"
    return "enabled"


def enable_plugin(config: AppConfig, plugin_id: str) -> None:
    plugin = plugin_by_id(plugin_id)
    if plugin is None:
        return
    config.removed_plugins = [value for value in normalize_plugin_ids(config.removed_plugins) if value != plugin.id]
    config.disabled_plugins = [value for value in normalize_plugin_ids(config.disabled_plugins) if value != plugin.id]
    enabled = normalize_plugin_ids(config.enabled_plugins)
    if plugin.id not in enabled:
        enabled.append(plugin.id)
    config.enabled_plugins = enabled


def disable_plugin(config: AppConfig, plugin_id: str) -> None:
    plugin = plugin_by_id(plugin_id)
    if plugin is None or plugin.id in set(normalize_plugin_ids(config.removed_plugins)):
        return
    disabled = normalize_plugin_ids(config.disabled_plugins)
    if plugin.id not in disabled:
        disabled.append(plugin.id)
    config.disabled_plugins = disabled
    config.enabled_plugins = [value for value in normalize_plugin_ids(config.enabled_plugins) if value != plugin.id]


def remove_plugin(config: AppConfig, plugin_id: str) -> None:
    plugin = plugin_by_id(plugin_id)
    if plugin is None:
        return
    removed = normalize_plugin_ids(config.removed_plugins)
    if plugin.id not in removed:
        removed.append(plugin.id)
    config.removed_plugins = removed
    config.disabled_plugins = [value for value in normalize_plugin_ids(config.disabled_plugins) if value != plugin.id]
    config.enabled_plugins = [value for value in normalize_plugin_ids(config.enabled_plugins) if value != plugin.id]


def restore_plugin(config: AppConfig, plugin_id: str) -> None:
    plugin = plugin_by_id(plugin_id)
    if plugin is None:
        return
    config.removed_plugins = [value for value in normalize_plugin_ids(config.removed_plugins) if value != plugin.id]
    config.disabled_plugins = [value for value in normalize_plugin_ids(config.disabled_plugins) if value != plugin.id]
