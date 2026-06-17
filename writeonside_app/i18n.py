from __future__ import annotations

from .locales import TRANSLATIONS

SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh": "中文",
    "pt": "Português",
    "de": "Deutsch",
    "fr": "Français",
    "nl": "Nederlands",
    "ko": "한국어",
    "it": "Italiano",
    "hi": "हिन्दी",
    "uk": "Українська",
}

_current = "en"


def normalize_language(code: object) -> str:
    text = str(code or "en").strip().lower().replace("_", "-")
    if text.startswith("zh"):
        return "zh"
    if text.startswith("pt"):
        return "pt"
    if text.startswith("de"):
        return "de"
    if text.startswith("fr"):
        return "fr"
    if text.startswith("nl"):
        return "nl"
    if text.startswith("ko"):
        return "ko"
    if text.startswith("it"):
        return "it"
    if text.startswith("hi"):
        return "hi"
    if text.startswith("uk") or text.startswith("ua"):
        return "uk"
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
