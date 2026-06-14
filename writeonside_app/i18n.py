from __future__ import annotations

from .locales import TRANSLATIONS

SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh": "中文",
    "pt": "Português",
}

_current = "en"


def normalize_language(code: object) -> str:
    text = str(code or "en").strip().lower().replace("_", "-")
    if text.startswith("zh"):
        return "zh"
    if text.startswith("pt"):
        return "pt"
    if text in SUPPORTED_LANGUAGES:
        return text
    return "en"


def set_language(code: object) -> str:
    global _current
    _current = normalize_language(code)
    return _current


def get_language() -> str:
    return _current


def t(key: str, **kwargs: object) -> str:
    catalog = TRANSLATIONS.get(_current) or TRANSLATIONS["en"]
    text = catalog.get(key) or TRANSLATIONS["en"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


def command_label(command_id: str) -> str:
    return t(f"cmd.{command_id}")


def command_tooltip(command_id: str, shortcut_display: str = "") -> str:
    label = command_label(command_id)
    if shortcut_display:
        return t("tooltip.command_with_shortcut", label=label, shortcut=shortcut_display)
    return label
