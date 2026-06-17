from __future__ import annotations

from dataclasses import dataclass
import sys

DEFAULT_THEME = "graphite"

THEMES: dict[str, dict[str, str]] = {
    "graphite": {
        "NAME": "Graphite",
        "BG": "#15161a",
        "SURFACE": "#1e2027",
        "SURFACE_2": "#252832",
        "SIDEBAR": "#22242c",
        "SIDEBAR_SURFACE": "#2b2e38",
        "SIDEBAR_BORDER": "#3a3e4a",
        "SIDEBAR_TEXT": "#e1e5ee",
        "SIDEBAR_MUTED": "#9299aa",
        "SIDEBAR_HOVER": "#343844",
        "BORDER": "#343844",
        "TEXT": "#edf0f7",
        "TEXT_SOFT": "#c8ceda",
        "MUTED": "#8991a3",
        "ACCENT": "#3f8cff",
        "ACCENT_2": "#23c483",
        "DANGER": "#ff5f73",
        "CODE_BG": "#2b303b",
        "CODE_TEXT": "#a6e3a1",
        "LINK": "#67a6ff",
        "IMAGE_LINK": "#f5c2e7",
        "QUOTE": "#b9c1d4",
        "FIND_MATCH": "#3a3f4d",
        "OUTLINE_CURRENT": "#32415f",
        "DISABLED": "#505463",
        "HIGHLIGHT_BG": "#6b5500",
        "HIGHLIGHT_FG": "#ffe47a",
    },
    "obsidian": {
        "NAME": "Obsidian",
        "BG": "#191919",
        "SURFACE": "#202020",
        "SURFACE_2": "#272727",
        "SIDEBAR": "#252525",
        "SIDEBAR_SURFACE": "#303030",
        "SIDEBAR_BORDER": "#3d3d3d",
        "SIDEBAR_TEXT": "#e7e7e7",
        "SIDEBAR_MUTED": "#9b9b9b",
        "SIDEBAR_HOVER": "#363636",
        "BORDER": "#383838",
        "TEXT": "#f1f1f1",
        "TEXT_SOFT": "#d0d0d0",
        "MUTED": "#929292",
        "ACCENT": "#7c6ff0",
        "ACCENT_2": "#5cc8a1",
        "DANGER": "#ef6b73",
        "CODE_BG": "#2e2e2e",
        "CODE_TEXT": "#9fe3b1",
        "LINK": "#9d93ff",
        "IMAGE_LINK": "#e8a6d8",
        "QUOTE": "#bebebe",
        "FIND_MATCH": "#44404f",
        "OUTLINE_CURRENT": "#413d61",
        "DISABLED": "#5d5d5d",
        "HIGHLIGHT_BG": "#644e00",
        "HIGHLIGHT_FG": "#ffe47a",
    },
    "dracula": {
        "NAME": "Dracula",
        "BG": "#282a36",
        "SURFACE": "#30323f",
        "SURFACE_2": "#383a49",
        "SIDEBAR": "#343746",
        "SIDEBAR_SURFACE": "#414455",
        "SIDEBAR_BORDER": "#515568",
        "SIDEBAR_TEXT": "#f8f8f2",
        "SIDEBAR_MUTED": "#a7a8b8",
        "SIDEBAR_HOVER": "#474a5c",
        "BORDER": "#4a4d60",
        "TEXT": "#f8f8f2",
        "TEXT_SOFT": "#d7d7d0",
        "MUTED": "#a3a4b3",
        "ACCENT": "#bd93f9",
        "ACCENT_2": "#50fa7b",
        "DANGER": "#ff5555",
        "CODE_BG": "#343746",
        "CODE_TEXT": "#50fa7b",
        "LINK": "#8be9fd",
        "IMAGE_LINK": "#ff79c6",
        "QUOTE": "#f1fa8c",
        "FIND_MATCH": "#4d4f63",
        "OUTLINE_CURRENT": "#514568",
        "DISABLED": "#666979",
        "HIGHLIGHT_BG": "#6d5c00",
        "HIGHLIGHT_FG": "#f1fa8c",
    },
    "nord": {
        "NAME": "Nord",
        "BG": "#2e3440",
        "SURFACE": "#353c49",
        "SURFACE_2": "#3b4252",
        "SIDEBAR": "#3b4252",
        "SIDEBAR_SURFACE": "#434c5e",
        "SIDEBAR_BORDER": "#566176",
        "SIDEBAR_TEXT": "#eceff4",
        "SIDEBAR_MUTED": "#a7b0c0",
        "SIDEBAR_HOVER": "#4c566a",
        "BORDER": "#4c566a",
        "TEXT": "#eceff4",
        "TEXT_SOFT": "#d8dee9",
        "MUTED": "#9aa5b5",
        "ACCENT": "#88c0d0",
        "ACCENT_2": "#a3be8c",
        "DANGER": "#bf616a",
        "CODE_BG": "#3b4252",
        "CODE_TEXT": "#a3be8c",
        "LINK": "#81a1c1",
        "IMAGE_LINK": "#b48ead",
        "QUOTE": "#e5e9f0",
        "FIND_MATCH": "#4c566a",
        "OUTLINE_CURRENT": "#40566a",
        "DISABLED": "#667085",
        "HIGHLIGHT_BG": "#524c20",
        "HIGHLIGHT_FG": "#ebcb8b",
    },
    "solarized": {
        "NAME": "Solarized Dark",
        "BG": "#002b36",
        "SURFACE": "#073642",
        "SURFACE_2": "#0b3d49",
        "SIDEBAR": "#073b46",
        "SIDEBAR_SURFACE": "#104752",
        "SIDEBAR_BORDER": "#23535c",
        "SIDEBAR_TEXT": "#eee8d5",
        "SIDEBAR_MUTED": "#93a1a1",
        "SIDEBAR_HOVER": "#164b56",
        "BORDER": "#1b4d57",
        "TEXT": "#fdf6e3",
        "TEXT_SOFT": "#eee8d5",
        "MUTED": "#93a1a1",
        "ACCENT": "#268bd2",
        "ACCENT_2": "#2aa198",
        "DANGER": "#dc322f",
        "CODE_BG": "#073642",
        "CODE_TEXT": "#859900",
        "LINK": "#2aa198",
        "IMAGE_LINK": "#d33682",
        "QUOTE": "#b58900",
        "FIND_MATCH": "#31545b",
        "OUTLINE_CURRENT": "#164e63",
        "DISABLED": "#586e75",
        "HIGHLIGHT_BG": "#3f3600",
        "HIGHLIGHT_FG": "#b58900",
    },
    "tokyo_night": {
        "NAME": "Tokyo Night",
        "BG": "#1a1b26",
        "SURFACE": "#202230",
        "SURFACE_2": "#292c3d",
        "SIDEBAR": "#24283b",
        "SIDEBAR_SURFACE": "#2f344d",
        "SIDEBAR_BORDER": "#3b4261",
        "SIDEBAR_TEXT": "#c0caf5",
        "SIDEBAR_MUTED": "#7f88ad",
        "SIDEBAR_HOVER": "#343b58",
        "BORDER": "#3b4261",
        "TEXT": "#c0caf5",
        "TEXT_SOFT": "#a9b1d6",
        "MUTED": "#737da5",
        "ACCENT": "#7aa2f7",
        "ACCENT_2": "#9ece6a",
        "DANGER": "#f7768e",
        "CODE_BG": "#24283b",
        "CODE_TEXT": "#9ece6a",
        "LINK": "#7dcfff",
        "IMAGE_LINK": "#bb9af7",
        "QUOTE": "#e0af68",
        "FIND_MATCH": "#3b4261",
        "OUTLINE_CURRENT": "#364a72",
        "DISABLED": "#565f89",
        "HIGHLIGHT_BG": "#453820",
        "HIGHLIGHT_FG": "#e0af68",
    },
    "gruvbox": {
        "NAME": "Gruvbox",
        "BG": "#282828",
        "SURFACE": "#32302f",
        "SURFACE_2": "#3c3836",
        "SIDEBAR": "#3c3836",
        "SIDEBAR_SURFACE": "#504945",
        "SIDEBAR_BORDER": "#665c54",
        "SIDEBAR_TEXT": "#ebdbb2",
        "SIDEBAR_MUTED": "#a89984",
        "SIDEBAR_HOVER": "#504945",
        "BORDER": "#504945",
        "TEXT": "#fbf1c7",
        "TEXT_SOFT": "#ebdbb2",
        "MUTED": "#a89984",
        "ACCENT": "#83a598",
        "ACCENT_2": "#b8bb26",
        "DANGER": "#fb4934",
        "CODE_BG": "#3c3836",
        "CODE_TEXT": "#b8bb26",
        "LINK": "#8ec07c",
        "IMAGE_LINK": "#d3869b",
        "QUOTE": "#fabd2f",
        "FIND_MATCH": "#504945",
        "OUTLINE_CURRENT": "#455a56",
        "DISABLED": "#7c6f64",
        "HIGHLIGHT_BG": "#544200",
        "HIGHLIGHT_FG": "#fabd2f",
    },
    "catppuccin": {
        "NAME": "Catppuccin Mocha",
        "BG": "#1e1e2e",
        "SURFACE": "#252537",
        "SURFACE_2": "#2b2b40",
        "SIDEBAR": "#313244",
        "SIDEBAR_SURFACE": "#3b3c52",
        "SIDEBAR_BORDER": "#4b4d67",
        "SIDEBAR_TEXT": "#cdd6f4",
        "SIDEBAR_MUTED": "#9399b2",
        "SIDEBAR_HOVER": "#45475a",
        "BORDER": "#45475a",
        "TEXT": "#cdd6f4",
        "TEXT_SOFT": "#bac2de",
        "MUTED": "#9399b2",
        "ACCENT": "#89b4fa",
        "ACCENT_2": "#a6e3a1",
        "DANGER": "#f38ba8",
        "CODE_BG": "#313244",
        "CODE_TEXT": "#a6e3a1",
        "LINK": "#89dceb",
        "IMAGE_LINK": "#f5c2e7",
        "QUOTE": "#f9e2af",
        "FIND_MATCH": "#45475a",
        "OUTLINE_CURRENT": "#3d4f70",
        "DISABLED": "#6c7086",
        "HIGHLIGHT_BG": "#433528",
        "HIGHLIGHT_FG": "#f9e2af",
    },
    "github_light": {
        "NAME": "GitHub Light", "BG": "#f6f8fa", "SURFACE": "#ffffff", "SURFACE_2": "#eef1f4",
        "SIDEBAR": "#ffffff", "SIDEBAR_SURFACE": "#f6f8fa", "SIDEBAR_BORDER": "#d0d7de",
        "SIDEBAR_TEXT": "#24292f", "SIDEBAR_MUTED": "#57606a", "SIDEBAR_HOVER": "#eaeef2",
        "BORDER": "#d0d7de", "TEXT": "#1f2328", "TEXT_SOFT": "#424a53", "MUTED": "#656d76",
        "ACCENT": "#0969da", "ACCENT_2": "#1a7f37", "DANGER": "#cf222e", "CODE_BG": "#eaeef2",
        "CODE_TEXT": "#116329", "LINK": "#0969da", "IMAGE_LINK": "#8250df", "QUOTE": "#57606a",
        "FIND_MATCH": "#fff1a8", "OUTLINE_CURRENT": "#dbeafe", "DISABLED": "#8c959f",
        "HIGHLIGHT_BG": "#fff1a8", "HIGHLIGHT_FG": "#5c3d00",
    },
    "solarized_light": {
        "NAME": "Solarized Light", "BG": "#eee8d5", "SURFACE": "#f7f1de", "SURFACE_2": "#e4deca",
        "SIDEBAR": "#fdf6e3", "SIDEBAR_SURFACE": "#eee8d5", "SIDEBAR_BORDER": "#d6cfba",
        "SIDEBAR_TEXT": "#586e75", "SIDEBAR_MUTED": "#657b83", "SIDEBAR_HOVER": "#e4dec9",
        "BORDER": "#d4cdb8", "TEXT": "#073642", "TEXT_SOFT": "#40575d", "MUTED": "#657b83",
        "ACCENT": "#268bd2", "ACCENT_2": "#2aa198", "DANGER": "#dc322f", "CODE_BG": "#e2dcc8",
        "CODE_TEXT": "#657b00", "LINK": "#1676a7", "IMAGE_LINK": "#d33682", "QUOTE": "#765800",
        "FIND_MATCH": "#f4df9b", "OUTLINE_CURRENT": "#cfe4e8", "DISABLED": "#839496",
        "HIGHLIGHT_BG": "#f2da00", "HIGHLIGHT_FG": "#4a3300",
    },
    "nord_light": {
        "NAME": "Nord Snow", "BG": "#e5e9f0", "SURFACE": "#eceff4", "SURFACE_2": "#d8dee9",
        "SIDEBAR": "#f4f6fa", "SIDEBAR_SURFACE": "#e5e9f0", "SIDEBAR_BORDER": "#c4cad4",
        "SIDEBAR_TEXT": "#2e3440", "SIDEBAR_MUTED": "#5e6879", "SIDEBAR_HOVER": "#d8dee9",
        "BORDER": "#c4cad4", "TEXT": "#2e3440", "TEXT_SOFT": "#434c5e", "MUTED": "#5e6879",
        "ACCENT": "#5e81ac", "ACCENT_2": "#4f7548", "DANGER": "#a84650", "CODE_BG": "#d8dee9",
        "CODE_TEXT": "#46683f", "LINK": "#466b91", "IMAGE_LINK": "#805678", "QUOTE": "#4c566a",
        "FIND_MATCH": "#eadf9f", "OUTLINE_CURRENT": "#c9d9ea", "DISABLED": "#7b8494",
        "HIGHLIGHT_BG": "#eadf9f", "HIGHLIGHT_FG": "#3b3000",
    },
    "catppuccin_latte": {
        "NAME": "Catppuccin Latte", "BG": "#e6e9ef", "SURFACE": "#eff1f5", "SURFACE_2": "#dce0e8",
        "SIDEBAR": "#f5f6fa", "SIDEBAR_SURFACE": "#e6e9ef", "SIDEBAR_BORDER": "#bcc0cc",
        "SIDEBAR_TEXT": "#4c4f69", "SIDEBAR_MUTED": "#6c6f85", "SIDEBAR_HOVER": "#dce0e8",
        "BORDER": "#bcc0cc", "TEXT": "#3b3d54", "TEXT_SOFT": "#4c4f69", "MUTED": "#6c6f85",
        "ACCENT": "#1e66f5", "ACCENT_2": "#287a55", "DANGER": "#d20f39", "CODE_BG": "#dce0e8",
        "CODE_TEXT": "#28754d", "LINK": "#1e66f5", "IMAGE_LINK": "#8839ef", "QUOTE": "#5c5f77",
        "FIND_MATCH": "#f5e0a3", "OUTLINE_CURRENT": "#cad9f4", "DISABLED": "#8c8fa1",
        "HIGHLIGHT_BG": "#f5e0a3", "HIGHLIGHT_FG": "#4c3500",
    },
    "icon_light": {
        "NAME": "Icon Light",
        "BG": "#f4f1e8",
        "SURFACE": "#fffaf0",
        "SURFACE_2": "#ebe4d8",
        "SIDEBAR": "#efe8dc",
        "SIDEBAR_SURFACE": "#fff7ea",
        "SIDEBAR_BORDER": "#d8caba",
        "SIDEBAR_TEXT": "#2c2635",
        "SIDEBAR_MUTED": "#766b7d",
        "SIDEBAR_HOVER": "#eadfce",
        "BORDER": "#d8caba",
        "TEXT": "#211c26",
        "TEXT_SOFT": "#4b4251",
        "MUTED": "#756b74",
        "ACCENT": "#df7134",
        "ACCENT_2": "#2b8584",
        "DANGER": "#c44b55",
        "CODE_BG": "#e7ded3",
        "CODE_TEXT": "#186f6e",
        "LINK": "#6f53a3",
        "IMAGE_LINK": "#c56b2f",
        "QUOTE": "#7050a0",
        "FIND_MATCH": "#f2d991",
        "OUTLINE_CURRENT": "#e7d9c5",
        "DISABLED": "#9b908a",
        "HIGHLIGHT_BG": "#e9ca72",
        "HIGHLIGHT_FG": "#4a2c05",
    },
    "icon_dark": {
        "NAME": "Icon Dark",
        "BG": "#101116",
        "SURFACE": "#181922",
        "SURFACE_2": "#222431",
        "SIDEBAR": "#151720",
        "SIDEBAR_SURFACE": "#202332",
        "SIDEBAR_BORDER": "#33384b",
        "SIDEBAR_TEXT": "#f1eef7",
        "SIDEBAR_MUTED": "#a49db3",
        "SIDEBAR_HOVER": "#292d3d",
        "BORDER": "#33384b",
        "TEXT": "#f4f1f8",
        "TEXT_SOFT": "#d5d0df",
        "MUTED": "#9c96a9",
        "ACCENT": "#a65bd4",
        "ACCENT_2": "#65b6d2",
        "DANGER": "#f27686",
        "CODE_BG": "#202332",
        "CODE_TEXT": "#e2b85a",
        "LINK": "#68b7d7",
        "IMAGE_LINK": "#c17be5",
        "QUOTE": "#e2b85a",
        "FIND_MATCH": "#343045",
        "OUTLINE_CURRENT": "#2b3d55",
        "DISABLED": "#5c6172",
        "HIGHLIGHT_BG": "#5d451c",
        "HIGHLIGHT_FG": "#ffd479",
    },
}

PALETTE_KEYS = tuple(key for key in THEMES[DEFAULT_THEME] if key != "NAME")

_THEME_MODULE_PREFIX = "writeonside_app"
_THEME_SYNC_MODULES = (
    f"{_THEME_MODULE_PREFIX}.app",
    f"{_THEME_MODULE_PREFIX}.ui.window",
    f"{_THEME_MODULE_PREFIX}.ui.tray_manager",
    f"{_THEME_MODULE_PREFIX}.ui.editor",
    f"{_THEME_MODULE_PREFIX}.ui.editor_structure",
    f"{_THEME_MODULE_PREFIX}.ui.wikilinks_ui",
    f"{_THEME_MODULE_PREFIX}.ui.image_viewer",
    f"{_THEME_MODULE_PREFIX}.ui.explorer",
    f"{_THEME_MODULE_PREFIX}.ui.notes",
    f"{_THEME_MODULE_PREFIX}.ui.settings",
    f"{_THEME_MODULE_PREFIX}.ui.theme_utils",
)


@dataclass(frozen=True)
class ThemePalette:
    BG: str
    SURFACE: str
    SURFACE_2: str
    SIDEBAR: str
    SIDEBAR_SURFACE: str
    SIDEBAR_BORDER: str
    SIDEBAR_TEXT: str
    SIDEBAR_MUTED: str
    SIDEBAR_HOVER: str
    BORDER: str
    TEXT: str
    TEXT_SOFT: str
    MUTED: str
    ACCENT: str
    ACCENT_2: str
    DANGER: str
    CODE_BG: str
    CODE_TEXT: str
    LINK: str
    IMAGE_LINK: str
    QUOTE: str
    FIND_MATCH: str
    OUTLINE_CURRENT: str
    DISABLED: str
    HIGHLIGHT_BG: str
    HIGHLIGHT_FG: str

    @classmethod
    def from_dict(cls, palette: dict[str, str]) -> ThemePalette:
        return cls(**{key: palette[key] for key in PALETTE_KEYS})

    def as_dict(self) -> dict[str, str]:
        return {key: getattr(self, key) for key in PALETTE_KEYS}


class ActiveTheme:
    def __init__(self) -> None:
        self._palette = ThemePalette.from_dict(THEMES[DEFAULT_THEME])

    @property
    def palette(self) -> ThemePalette:
        return self._palette

    @property
    def name(self) -> str:
        return getattr(self, "_name", DEFAULT_THEME)

    def set(self, name: str) -> ThemePalette:
        resolved = name if name in THEMES else DEFAULT_THEME
        self._palette = ThemePalette.from_dict(get_theme(resolved))
        self._name = resolved
        sync_palette_to_modules(self._palette)
        return self._palette


current = ActiveTheme()


def sync_palette_to_modules(palette: ThemePalette) -> dict[str, str]:
    values = palette.as_dict()
    globals().update(values)
    for module_name in _THEME_SYNC_MODULES:
        module = sys.modules.get(module_name)
        if module is not None:
            module.__dict__.update(values)
    return values


def get_theme(name: str) -> dict[str, str]:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def set_active_theme(name: str) -> dict[str, str]:
    return current.set(name).as_dict()


current.set(DEFAULT_THEME)
