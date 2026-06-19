from __future__ import annotations

import queue
from typing import Any

KEY_DOWN = "down"
KEY_UP = "up"


class _LazyKeyboard:
    """Delay the relatively expensive Windows keyboard hook import until use."""

    _module: Any = None

    def _load(self):
        if self._module is None:
            import keyboard as keyboard_module

            self._module = keyboard_module
        return self._module

    def __getattr__(self, name: str):
        return getattr(self._load(), name)


keyboard = _LazyKeyboard()


def hook(*args, **kwargs):
    return keyboard.hook(*args, **kwargs)


def unhook(*args, **kwargs):
    return keyboard.unhook(*args, **kwargs)


def get_hotkey_name(*args, **kwargs):
    return keyboard.get_hotkey_name(*args, **kwargs)

# Windows hook stacks and some apps leave virtual function keys "stuck" in
# keyboard._pressed_events. keyboard.read_hotkey() merges that global state
# into the recorded combination, which often yields values like "f22+ctrl+g".
PHANTOM_HOTKEY_KEYS = frozenset({"f22", "f23", "f24"})


def normalize_hotkey(hotkey: str) -> str:
    # Keys like "page up" / "caps lock" contain spaces that must be kept;
    # only trim whitespace around the "+" separators.
    cleaned = hotkey.strip().lower()
    if "+" not in cleaned and "_" in cleaned:
        cleaned = cleaned.replace("_", "+")
    parts = [part.strip() for part in cleaned.split("+")]
    filtered = [part for part in parts if part and part not in PHANTOM_HOTKEY_KEYS]
    return "+".join(filtered)


def format_hotkey_display(hotkey: str) -> str:
    labels = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "win": "Win"}
    parts = [p for p in normalize_hotkey(hotkey).split("+") if p]
    return "+".join(labels.get(p, p.upper() if len(p) <= 3 else p.title()) for p in parts)


def is_phantom_hotkey_key(name: str | None) -> bool:
    return bool(name) and name.strip().lower() in PHANTOM_HOTKEY_KEYS


def filter_phantom_hotkey_names(names: list[str]) -> list[str]:
    return [name for name in names if name and not is_phantom_hotkey_key(name)]


def purge_phantom_pressed_keys() -> int:
    removed = 0
    with keyboard._pressed_events_lock:
        for scan_code in list(keyboard._pressed_events):
            event = keyboard._pressed_events[scan_code]
            if is_phantom_hotkey_key(event.name):
                del keyboard._pressed_events[scan_code]
                removed += 1
    return removed


def read_hotkey_clean(*, suppress: bool = False) -> str:
    """Record a hotkey without stale global key state such as virtual F22."""
    purge_phantom_pressed_keys()

    event_queue: queue.Queue = queue.Queue()
    pressed_names: list[str] = []

    def on_event(event) -> bool:
        event_queue.put(event)
        return event.event_type == KEY_DOWN

    hooked = hook(on_event, suppress=suppress)
    try:
        while True:
            event = event_queue.get()
            name = event.name
            if is_phantom_hotkey_key(name):
                continue
            if event.event_type == KEY_DOWN:
                if name and name not in pressed_names:
                    pressed_names.append(name)
                continue
            if event.event_type == KEY_UP:
                return get_hotkey_name(filter_phantom_hotkey_names(pressed_names))
    finally:
        unhook(hooked)


def validate_hotkey(hotkey: str) -> bool:
    normalized = normalize_hotkey(hotkey)
    if not normalized:
        return False
    try:
        keyboard.parse_hotkey(normalized)
        return True
    except Exception:
        return False
