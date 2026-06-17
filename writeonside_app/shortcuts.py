from __future__ import annotations

from collections.abc import Mapping

from .hotkeys import normalize_hotkey, validate_hotkey


COMMAND_SHORTCUTS = {
    "open_file": ("Open file", "ctrl+o"),
    "new_note": ("New note", "ctrl+n"),
    "save_note": ("Save note", "ctrl+s"),
    "toggle_mode": ("Toggle read/edit mode", "ctrl+e"),
    "outline": ("Outline", "ctrl+shift+o"),
    "backlinks": ("Backlinks", "ctrl+shift+b"),
    "find": ("Find", "ctrl+f"),
    "replace": ("Find and replace", "ctrl+h"),
    "frontmatter": ("Create YAML Front Matter", "ctrl+alt+y"),
    "bold": ("Bold", "ctrl+b"),
    "italic": ("Italic", "ctrl+i"),
    "underline": ("Underline", "ctrl+u"),
    "strike": ("Strikethrough", "ctrl+shift+x"),
    "heading": ("Heading", "ctrl+alt+h"),
    "highlight": ("Highlight", "ctrl+shift+m"),
    "color": ("Text color", "ctrl+alt+c"),
    "code": ("Inline code / code block", "ctrl+`"),
    "quote": ("Quote", "ctrl+shift+q"),
    "link": ("Link", "ctrl+k"),
    "image": ("Insert image", "ctrl+shift+i"),
    "table": ("Insert table", "ctrl+alt+t"),
    "bullet": ("Bullet list", "ctrl+alt+b"),
    "ordered": ("Numbered list", "ctrl+alt+o"),
    "task": ("Task list", "ctrl+alt+l"),
    "divider": ("Divider", "ctrl+alt+d"),
}

DEFAULT_COMMAND_SHORTCUTS = {
    command_id: shortcut for command_id, (_label, shortcut) in COMMAND_SHORTCUTS.items()
}

TK_KEY_NAMES = {
    "enter": "Return",
    "return": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "space": "space",
    "page up": "Prior",
    "page down": "Next",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "delete": "Delete",
    "backspace": "BackSpace",
    "tab": "Tab",
}


def normalize_command_shortcuts(raw: Mapping[str, object] | None) -> dict[str, str]:
    shortcuts = dict(DEFAULT_COMMAND_SHORTCUTS)
    if not isinstance(raw, Mapping):
        return shortcuts
    for command_id in COMMAND_SHORTCUTS:
        value = raw.get(command_id)
        if value is None:
            continue
        normalized = normalize_hotkey(str(value))
        shortcuts[command_id] = normalized if normalized and validate_hotkey(normalized) else ""
    return shortcuts


def hotkey_to_tk_sequence(hotkey: str) -> str | None:
    normalized = normalize_hotkey(hotkey)
    if not normalized:
        return None
    parts = normalized.split("+")
    if not parts:
        return None
    key = parts[-1]
    modifiers = []
    for modifier in parts[:-1]:
        mapped = {
            "ctrl": "Control",
            "control": "Control",
            "shift": "Shift",
            "alt": "Alt",
            "win": "Win",
        }.get(modifier)
        if mapped and mapped not in modifiers:
            modifiers.append(mapped)
    tk_key = TK_KEY_NAMES.get(key, key)
    if len(tk_key) == 1 and tk_key.isalpha():
        tk_key = tk_key.lower()
    return "<" + "-".join([*modifiers, tk_key]) + ">"


def shortcut_conflicts(shortcuts: Mapping[str, str]) -> dict[str, list[str]]:
    by_shortcut: dict[str, list[str]] = {}
    for command_id, shortcut in shortcuts.items():
        normalized = normalize_hotkey(shortcut)
        if normalized:
            by_shortcut.setdefault(normalized, []).append(command_id)
    return {shortcut: command_ids for shortcut, command_ids in by_shortcut.items() if len(command_ids) > 1}
