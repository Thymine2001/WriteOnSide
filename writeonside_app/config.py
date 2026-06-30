import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .hotkeys import is_modifier_only_hotkey, normalize_hotkey, validate_hotkey
from .layout_metrics import (
    clamp_explorer_width,
    clamp_panel_width,
    default_explorer_width,
    default_panel_width,
    explorer_width_limits,
    panel_width_limits,
    work_area_width,
)
from .shortcuts import DEFAULT_COMMAND_SHORTCUTS, normalize_command_shortcuts
from .file_labels import (
    TAG_VIEW_MODES,
    normalize_custom_color,
    normalize_file_color_tags,
    normalize_pinned_notes,
)

APP_NAME = "WriteOnSide"
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
CONFIG_FILE = APP_DATA_DIR / "config.json"
PREVIOUS_CONFIG = Path.home() / ".writeonside_config.json"
LEGACY_CONFIG = Path.home() / ".sidenotes_config.json"


@dataclass
class AppConfig:
    notes_directory: str = str(Path.home() / "Documents" / APP_NAME)
    obsidian_vault: str = ""
    current_note_path: str = ""
    hotkey: str = "ctrl+shift+enter"
    width: int = 520
    explorer_width: int = 210
    nav_width: int = 16
    nav_bar_visible: bool = True
    nav_bar_anchor: str = "panel_edge"
    alpha: float = 0.98
    explorer_open: bool = True
    auto_save: bool = True
    auto_save_delay_ms: int = 900
    auto_close_on_blur: bool = False
    auto_close_on_escape: bool = False
    remember_last_note: bool = True
    view_mode: str = "edit"
    app_position: str = "right"
    theme: str = "graphite"
    start_on_boot: bool = False
    font_family: str = "Segoe UI"
    font_size: int = 11
    attachments_folder: str = "Attachments"
    language: str = "en"
    command_shortcuts: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COMMAND_SHORTCUTS))
    tag_view_mode: str = "text"
    show_created_dates_in_tags: bool = False
    file_color_tags: dict[str, list[str]] = field(default_factory=dict)
    custom_tag_color: str = ""
    pinned_notes: list[str] = field(default_factory=list)
    enabled_plugins: list[str] = field(default_factory=list)
    disabled_plugins: list[str] = field(default_factory=list)
    removed_plugins: list[str] = field(default_factory=list)
    plugin_shortcuts: dict[str, str] = field(default_factory=dict)
    sticky_notes_double_ctrl: bool = True
    sticky_notes_default_tag: str = "sticky"
    sticky_notes_pinned: bool = False


def clamp_int(value, low: int, high: int, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def clamp_float(value, low: float, high: float, default: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def migrate_config(raw: dict) -> dict:
    if not raw.get("notes_directory"):
        vault = str(raw.get("obsidian_vault", "")).strip()
        local_path = str(raw.get("local_path", "")).strip()
        if vault:
            raw["notes_directory"] = vault
        elif local_path:
            raw["notes_directory"] = str(Path(local_path).expanduser().parent)
    return raw


def normalize_relative_folder(value: object, default: str = "Attachments") -> str:
    text = str(value or default).strip().replace("\\", "/").strip("/")
    path = Path(text)
    if not text or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return default
    return path.as_posix()


def normalize_plugin_ids(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        plugin_id = str(item or "").strip().casefold().replace(" ", "_")
        if not plugin_id or plugin_id in seen:
            continue
        seen.add(plugin_id)
        normalized.append(plugin_id)
    return normalized


def normalize_plugin_shortcuts(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    shortcuts: dict[str, str] = {}
    for raw_id, raw_shortcut in value.items():
        plugin_ids = normalize_plugin_ids([raw_id])
        if not plugin_ids:
            continue
        shortcut = normalize_hotkey(str(raw_shortcut or ""))
        if shortcut and not is_modifier_only_hotkey(shortcut) and validate_hotkey(shortcut):
            shortcuts[plugin_ids[0]] = shortcut
    return shortcuts


def load_config() -> AppConfig:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        migration_source = PREVIOUS_CONFIG if PREVIOUS_CONFIG.exists() else LEGACY_CONFIG
        if migration_source.exists():
            try:
                shutil.copy2(migration_source, CONFIG_FILE)
            except OSError:
                pass

    data = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            backup = CONFIG_FILE.with_suffix(".broken.json")
            try:
                shutil.copy2(CONFIG_FILE, backup)
            except OSError:
                pass
            data = {}

    data = migrate_config(data)
    cfg = AppConfig()
    valid_keys = set(asdict(cfg))
    merged = asdict(cfg)
    merged.update({k: v for k, v in data.items() if k in valid_keys})
    work_width = work_area_width()
    panel_min, panel_max = panel_width_limits(work_width)
    explorer_min, explorer_max = explorer_width_limits(work_width)
    merged["width"] = clamp_panel_width(
        clamp_int(merged["width"], panel_min, panel_max, default_panel_width(work_width)),
        work_width,
    )
    merged["explorer_width"] = clamp_explorer_width(
        clamp_int(merged["explorer_width"], explorer_min, explorer_max, default_explorer_width(work_width)),
        work_width,
    )
    merged["nav_width"] = clamp_int(merged["nav_width"], 4, 24, cfg.nav_width)
    merged["nav_bar_visible"] = bool(merged.get("nav_bar_visible", True))
    nav_bar_anchor = str(merged.get("nav_bar_anchor") or cfg.nav_bar_anchor).strip().lower()
    merged["nav_bar_anchor"] = nav_bar_anchor if nav_bar_anchor in {"panel_edge", "screen_edge"} else cfg.nav_bar_anchor
    merged["auto_save_delay_ms"] = clamp_int(
        merged["auto_save_delay_ms"], 300, 5000, cfg.auto_save_delay_ms
    )
    merged["alpha"] = clamp_float(merged["alpha"], 0.30, 1.0, cfg.alpha)
    merged["font_size"] = clamp_int(merged["font_size"], 8, 20, cfg.font_size)
    merged["font_family"] = str(merged.get("font_family") or cfg.font_family).strip() or cfg.font_family
    merged["attachments_folder"] = normalize_relative_folder(
        merged.get("attachments_folder"),
        cfg.attachments_folder,
    )
    merged["command_shortcuts"] = normalize_command_shortcuts(merged.get("command_shortcuts"))
    tag_view_mode = str(merged.get("tag_view_mode") or cfg.tag_view_mode).strip().lower()
    merged["tag_view_mode"] = tag_view_mode if tag_view_mode in TAG_VIEW_MODES else cfg.tag_view_mode
    merged["show_created_dates_in_tags"] = bool(merged.get("show_created_dates_in_tags", False))
    merged["file_color_tags"] = normalize_file_color_tags(merged.get("file_color_tags"))
    merged["custom_tag_color"] = normalize_custom_color(merged.get("custom_tag_color"))
    merged["pinned_notes"] = normalize_pinned_notes(merged.get("pinned_notes"))
    merged["enabled_plugins"] = normalize_plugin_ids(merged.get("enabled_plugins"))
    merged["disabled_plugins"] = normalize_plugin_ids(merged.get("disabled_plugins"))
    merged["removed_plugins"] = normalize_plugin_ids(merged.get("removed_plugins"))
    merged["plugin_shortcuts"] = normalize_plugin_shortcuts(merged.get("plugin_shortcuts"))
    merged["sticky_notes_double_ctrl"] = bool(merged.get("sticky_notes_double_ctrl", True))
    merged["sticky_notes_default_tag"] = str(merged.get("sticky_notes_default_tag") or "sticky").strip() or "sticky"
    merged["sticky_notes_pinned"] = bool(merged.get("sticky_notes_pinned", False))
    raw_language = str(merged.get("language") or cfg.language).strip().lower()
    if raw_language.startswith("zh"):
        merged["language"] = "zh"
    elif raw_language.startswith("pt"):
        merged["language"] = "pt"
    elif raw_language == "en":
        merged["language"] = "en"
    else:
        merged["language"] = cfg.language
    if merged["view_mode"] not in {"edit", "read"}:
        merged["view_mode"] = "edit"
    if merged["app_position"] not in {"left", "right"}:
        merged["app_position"] = "right"
    # Fix #12: avoid a circular import (config → theme) by deferring theme
    # validation to the first use of get_theme(), which already falls back to
    # the default theme for unknown names.  We still guard against obviously
    # bad values (non-string, empty) to keep config.theme well-formed.
    raw_theme = merged.get("theme", "")
    if not isinstance(raw_theme, str) or not raw_theme.strip():
        merged["theme"] = cfg.theme
    elif raw_theme == "tokyo_night":
        merged["theme"] = "mid_night"
    return AppConfig(**merged)


def save_config(config: AppConfig) -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(asdict(config), ensure_ascii=False, indent=2)
    fd, temp_name = tempfile.mkstemp(prefix=".config.", suffix=".tmp", dir=str(APP_DATA_DIR))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
        os.replace(temp_path, CONFIG_FILE)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
