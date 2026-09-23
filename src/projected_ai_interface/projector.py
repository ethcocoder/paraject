"""Phase 1 projected UI: grid, folder icons, hover, and touch feedback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .display import DisplayInfo, logical_grid


@dataclass(frozen=True)
class FolderTarget:
    id: str
    label: str
    x: int
    y: int
    width: int = 180
    height: int = 130

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


class ProjectorUI:
    """Borderless Tk UI. Rendering is kept behind this class for headless testing."""

    def __init__(self, display: DisplayInfo, *, title: str = "Projected AI Interface") -> None:
        self.display = display
        self.title = title
        self.targets = self._make_targets(display.width, display.height)
        self.hovered: str | None = None
        self.touched: str | None = None
        self._root = None
        self._canvas = None

    @staticmethod
    def _make_targets(width: int, height: int) -> list[FolderTarget]:
        margin_x, margin_y = max(40, width // 12), max(70, height // 8)
        gap_x = max(40, width // 14)
        return [
            FolderTarget("documents", "Documents", margin_x, margin_y),
            FolderTarget("projects", "Projects", margin_x + 180 + gap_x, margin_y),
            FolderTarget("downloads", "Downloads", margin_x, margin_y + 180),
        ]

    def hit_test(self, x: int, y: int) -> FolderTarget | None:
        return next((target for target in self.targets if target.contains(x, y)), None)

    def dry_run(self) -> dict:
        """Describe the UI without requiring a graphical display."""
        return {
            "display": self.display.__dict__,
            "grid": logical_grid(self.display.width, self.display.height),
            "folders": [target.__dict__ for target in self.targets],
            "states": {"hovered": self.hovered, "touched": self.touched},
        }

    def run(self, on_touch: Callable[[FolderTarget], None] | None = None) -> None:
        import tkinter as tk

        root = tk.Tk()
        self._root, self._canvas = root, tk.Canvas(root, bg="#101827", highlightthickness=0)
        root.title(self.title)
        root.geometry(f"{self.display.width}x{self.display.height}+{self.display.x}+{self.display.y}")
        root.overrideredirect(True)
        root.attributes("-fullscreen", True)
        self._canvas.pack(fill="both", expand=True)
        self._render()
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Button-1>", lambda event: self._on_touch(event, on_touch))
        root.bind("<Escape>", root.destroy)
        root.mainloop()

    def _on_motion(self, event) -> None:
        target = self.hit_test(event.x, event.y)
        self.hovered = target.id if target else None
        self._render()

    def _on_touch(self, event, callback) -> None:
        target = self.hit_test(event.x, event.y)
        if not target:
            return
        self.touched = target.id
        self._render()
        if callback:
            callback(target)
        if self._root:
            self._root.after(220, self._clear_touch)

    def _clear_touch(self) -> None:
        self.touched = None
        self._render()

    def _render(self) -> None:
        if self._canvas is None:
            return
        canvas = self._canvas
        width, height = self.display.width, self.display.height
        canvas.delete("all")
        for x in logical_grid(width, height)["vertical"]:
            canvas.create_line(x, 0, x, height, fill="#26364d", width=1)
        for y in logical_grid(width, height)["horizontal"]:
            canvas.create_line(0, y, width, y, fill="#26364d", width=1)
        canvas.create_text(32, 28, anchor="nw", text="PROJECTED AI INTERFACE  •  PHASE 1", fill="#8ea6c7", font=("Arial", 16, "bold"))
        for target in self.targets:
            active = target.id == self.hovered
            touched = target.id == self.touched
            color = "#55d6be" if touched else ("#4d83d1" if active else "#28527d")
            x, y, w, h = target.x, target.y, target.width, target.height
            canvas.create_rectangle(x, y, x + w, y + h, outline="#9cc9ff" if active else "#52769d", width=3 if active else 2)
            canvas.create_rectangle(x + 18, y + 28, x + w - 18, y + h - 20, fill=color, outline="")
            canvas.create_rectangle(x + 18, y + 18, x + 82, y + 42, fill=color, outline="")
            canvas.create_text(x + w // 2, y + h - 8, text=target.label, fill="white", font=("Arial", 14, "bold"))
        status = "TOUCH REGISTERED" if self.touched else (f"HOVER: {self.hovered}" if self.hovered else "READY — move over a folder and click")
        canvas.create_text(width // 2, height - 35, text=status, fill="#55d6be" if self.touched else "#a8b9cf", font=("Arial", 15))
