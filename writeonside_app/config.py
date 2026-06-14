import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .shortcuts import DEFAULT_COMMAND_SHORTCUTS, normalize_command_shortcuts

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
    font_size: int = 10
    attachments_folder: str = "Attachments"
    language: str = "en"
    command_shortcuts: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COMMAND_SHORTCUTS))


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
    merged["width"] = clamp_int(merged["width"], 360, 900, cfg.width)
    merged["explorer_width"] = clamp_int(merged["explorer_width"], 150, 360, cfg.explorer_width)
    merged["nav_width"] = clamp_int(merged["nav_width"], 8, 32, cfg.nav_width)
    if merged["nav_width"] == 10:
        merged["nav_width"] = cfg.nav_width
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
