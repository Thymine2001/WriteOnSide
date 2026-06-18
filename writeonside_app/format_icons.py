from __future__ import annotations

# Segoe MDL2 Assets glyphs for a consistent Windows-native toolbar/menu look.
FORMAT_MDL2_FONT = ("Segoe MDL2 Assets", 10)

FORMAT_MDL2_ICONS: dict[str, str] = {
    "find_replace_show": "\uE70D",  # ChevronDown
    "find_replace_hide": "\uE70E",  # ChevronUp
    "quote": "\uE8FD",  # Message
    "image": "\uEB9F",  # Picture
    "table": "\uED58",  # GridView
    "task": "\uE739",  # Checkbox
    "divider": "\uECE8",  # PageSeparator
    "attachment": "\uE723",  # Attach
    "paste_clipboard_image": "\uE77F",  # Paste
    "clear_formatting": "\uE894",  # EraseTool
}

FORMAT_MDL2_KEYS = frozenset(FORMAT_MDL2_ICONS)


def format_action_glyph(key: str, fallback: str) -> str:
    return FORMAT_MDL2_ICONS.get(key, fallback)


def format_menu_label(glyph: str, text: str) -> str:
    return f"{glyph}  {text}"
