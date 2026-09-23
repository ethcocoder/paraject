"""Deterministic projected interaction engine."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .calibration import CalibrationProfile


@dataclass(frozen=True)
class UIObject:
    object_id: str
    object_type: str
    x: float
    y: float
    width: float
    height: float

    def contains(self, point: tuple[float, float]) -> bool:
        px, py = point
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


@dataclass(frozen=True)
class InteractionEvent:
    event: str
    position: dict[str, float]
    confidence: float
    object_type: str | None = None
    object_id: str | None = None
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


class EventLogger:
    """Append structured events as JSON Lines without storing camera frames."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, event: InteractionEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")


class InteractionEngine:
    """Map camera points and turn stable pointer states into UI events."""

    def __init__(self, calibration: CalibrationProfile, objects: Iterable[UIObject], *, confidence_threshold: float = 0.70, debounce_frames: int = 2, drag_distance: float = 12.0, swipe_distance: float = 180.0) -> None:
        self.calibration = calibration
        self.objects = tuple(objects)
        self.confidence_threshold = confidence_threshold
        self.debounce_frames = max(1, debounce_frames)
        self.drag_distance = drag_distance
        self.swipe_distance = swipe_distance
        self._candidate_id: str | None = None
        self._candidate_frames = 0
        self._pressed_id: str | None = None
        self._pressed_position: tuple[float, float] | None = None
        self._last_position: tuple[float, float] | None = None
        self._dragging = False
        self._stroke_start: tuple[float, float] | None = None
        self._stroke_started_at: float | None = None

    def hit_test(self, projector_point: tuple[float, float]) -> UIObject | None:
        return next((obj for obj in self.objects if obj.contains(projector_point)), None)

    def process(self, camera_point: tuple[float, float] | None, confidence: float, contact: str, *, timestamp: float | None = None) -> list[InteractionEvent]:
        now = time.time() if timestamp is None else timestamp
        if camera_point is None or confidence < self.confidence_threshold:
            self._candidate_id = None
            self._candidate_frames = 0
            return self._release(now, confidence)
        point = self.calibration.map_point(camera_point)
        target = self.hit_test(point)
        events: list[InteractionEvent] = []
        if target and target.object_id == self._candidate_id:
            self._candidate_frames += 1
        elif target:
            self._candidate_id, self._candidate_frames = target.object_id, 1
        else:
            self._candidate_id, self._candidate_frames = None, 0

        if contact == "touch" and target and self._pressed_id is None and self._candidate_frames >= self.debounce_frames:
            self._pressed_id, self._pressed_position = target.object_id, point
            self._stroke_start, self._stroke_started_at = point, now
            events.append(self._event("touch", point, confidence, target, now))
        elif self._pressed_id and contact == "hover" and self._pressed_position:
            distance = ((point[0] - self._pressed_position[0]) ** 2 + (point[1] - self._pressed_position[1]) ** 2) ** 0.5
            if distance >= self.drag_distance:
                if not self._dragging:
                    self._dragging = True
                    events.append(self._event("drag_start", point, confidence, target, now))
                else:
                    events.append(self._event("drag", point, confidence, target, now))
        elif contact != "touch" and contact != "hover":
            events.extend(self._release(now, confidence, point))
        self._last_position = point
        return events

    def _release(self, timestamp: float, confidence: float, point: tuple[float, float] | None = None) -> list[InteractionEvent]:
        if self._pressed_id is None:
            return []
        point = point or self._last_position or self._pressed_position or (0.0, 0.0)
        target = next((obj for obj in self.objects if obj.object_id == self._pressed_id), None)
        event_name = "drag_end" if self._dragging else "release"
        event = self._event(event_name, point, confidence, target, timestamp)
        events = [event]
        if not self._dragging and self._stroke_start and self._stroke_started_at is not None:
            distance = ((point[0] - self._stroke_start[0]) ** 2 + (point[1] - self._stroke_start[1]) ** 2) ** 0.5
            if distance >= self.swipe_distance:
                direction = "right" if point[0] > self._stroke_start[0] else "left"
                events.append(self._event("swipe", point, confidence, target, timestamp, direction=direction))
        self._pressed_id = self._pressed_position = None
        self._dragging = False
        self._stroke_start = self._stroke_started_at = None
        return events

    @staticmethod
    def _event(name: str, point: tuple[float, float], confidence: float, target: UIObject | None, timestamp: float, direction: str | None = None) -> InteractionEvent:
        return InteractionEvent(name, {"x": round(point[0], 3), "y": round(point[1], 3)}, round(confidence, 4), target.object_type if target else None, target.object_id if target else None, timestamp)
