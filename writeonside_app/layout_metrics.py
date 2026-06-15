from __future__ import annotations

from .platform import get_work_area

PANEL_WIDTH_MIN_RATIO = 0.18
PANEL_WIDTH_MAX_RATIO = 0.50
PANEL_WIDTH_DEFAULT_RATIO = 0.28
EXPLORER_WIDTH_MIN_RATIO = 0.10
EXPLORER_WIDTH_MAX_RATIO = 0.22
EXPLORER_WIDTH_DEFAULT_RATIO = 0.14


def work_area_width() -> int:
    left, _top, right, _bottom = get_work_area()
    width = right - left
    return width if width > 0 else 1366


def panel_width_limits(work_width: int | None = None) -> tuple[int, int]:
    work_width = work_width or work_area_width()
    minimum = max(300, int(work_width * PANEL_WIDTH_MIN_RATIO))
    maximum = max(minimum + 80, int(work_width * PANEL_WIDTH_MAX_RATIO))
    return minimum, maximum


def explorer_width_limits(work_width: int | None = None) -> tuple[int, int]:
    work_width = work_width or work_area_width()
    minimum = max(140, int(work_width * EXPLORER_WIDTH_MIN_RATIO))
    maximum = max(minimum + 40, int(work_width * EXPLORER_WIDTH_MAX_RATIO))
    return minimum, maximum


def default_panel_width(work_width: int | None = None) -> int:
    work_width = work_width or work_area_width()
    minimum, maximum = panel_width_limits(work_width)
    target = int(work_width * PANEL_WIDTH_DEFAULT_RATIO)
    return max(minimum, min(maximum, target))


def default_explorer_width(work_width: int | None = None) -> int:
    work_width = work_width or work_area_width()
    minimum, maximum = explorer_width_limits(work_width)
    target = int(work_width * EXPLORER_WIDTH_DEFAULT_RATIO)
    return max(minimum, min(maximum, target))


def clamp_panel_width(width: int, work_width: int | None = None) -> int:
    minimum, maximum = panel_width_limits(work_width)
    return max(minimum, min(maximum, int(width)))


def clamp_explorer_width(width: int, work_width: int | None = None) -> int:
    minimum, maximum = explorer_width_limits(work_width)
    return max(minimum, min(maximum, int(width)))


def clamp_layout_widths(
    panel_width: int,
    explorer_width: int,
    work_width: int | None = None,
) -> tuple[int, int]:
    return (
        clamp_panel_width(panel_width, work_width),
        clamp_explorer_width(explorer_width, work_width),
    )
