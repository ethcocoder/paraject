"""Display discovery and logical projector coordinate helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DisplayInfo:
    """A physical display rectangle in desktop coordinates."""

    index: int
    x: int
    y: int
    width: int
    height: int
    name: str = "display"


def detect_displays() -> list[DisplayInfo]:
    """Return connected displays when screeninfo is available.

    The dependency is optional so the dry-run and geometry tests work on CI and
    headless machines. A caller can still provide an explicit display rectangle.
    """
    try:
        from screeninfo import get_monitors  # type: ignore
    except ImportError:
        return []
    return [
        DisplayInfo(i, int(m.x), int(m.y), int(m.width), int(m.height), str(getattr(m, "name", "display")))
        for i, m in enumerate(get_monitors())
    ]


def logical_grid(width: int, height: int, columns: int = 4, rows: int = 3) -> dict[str, Any]:
    """Return deterministic grid lines and cell rectangles for rendering/tests."""
    if width <= 0 or height <= 0 or columns < 1 or rows < 1:
        raise ValueError("width, height, columns, and rows must be positive")
    return {
        "width": width,
        "height": height,
        "columns": columns,
        "rows": rows,
        "vertical": [round(width * i / columns) for i in range(columns + 1)],
        "horizontal": [round(height * i / rows) for i in range(rows + 1)],
    }
