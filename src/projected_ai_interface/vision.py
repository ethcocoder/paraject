"""Phase 4 vision primitives and optional MediaPipe hand adapter."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Iterable


@dataclass(frozen=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


@dataclass(frozen=True)
class HandDetection:
    landmarks: tuple[Landmark, ...]
    confidence: float

    @property
    def fingertip(self) -> Landmark | None:
        return self.landmarks[8] if len(self.landmarks) > 8 else None


@dataclass(frozen=True)
class VisionConfig:
    confidence_threshold: float = 0.70
    smoothing_alpha: float = 0.35
    touch_depth_threshold: float = 0.08
    touch_velocity_threshold: float = 0.025


class TemporalSmoother:
    """Exponential smoother for normalized fingertip coordinates."""

    def __init__(self, alpha: float = 0.35) -> None:
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be greater than 0 and no greater than 1")
        self.alpha = alpha
        self._point: tuple[float, float] | None = None

    def update(self, x: float, y: float) -> tuple[float, float]:
        if self._point is None:
            self._point = (x, y)
        else:
            old_x, old_y = self._point
            self._point = (old_x + self.alpha * (x - old_x), old_y + self.alpha * (y - old_y))
        return self._point

    def reset(self) -> None:
        self._point = None


class TouchDetector:
    """Classify hover/touch from fingertip depth and motion stability.

    A camera-independent interface keeps calibration and projected hit testing
    separate. Depth is normalized by the selected hand model; adapters that do
    not provide depth can still emit hover events and never guess a touch.
    """

    def __init__(self, config: VisionConfig | None = None) -> None:
        self.config = config or VisionConfig()
        self._previous: tuple[float, float] | None = None
        self._contact_streak = 0

    def classify(self, fingertip: Landmark | None, confidence: float) -> str:
        if fingertip is None or confidence < self.config.confidence_threshold:
            self._previous = None
            self._contact_streak = 0
            return "none"
        current = (fingertip.x, fingertip.y)
        velocity = 0.0 if self._previous is None else hypot(current[0] - self._previous[0], current[1] - self._previous[1])
        self._previous = current
        if fingertip.z <= -self.config.touch_depth_threshold and velocity <= self.config.touch_velocity_threshold:
            self._contact_streak += 1
        else:
            self._contact_streak = 0
        if self._contact_streak >= 2:
            return "touch"
        return "hover"


def smooth_detection(detection: HandDetection, smoother: TemporalSmoother) -> HandDetection:
    tip = detection.fingertip
    if tip is None:
        return detection
    x, y = smoother.update(tip.x, tip.y)
    landmarks = list(detection.landmarks)
    landmarks[8] = Landmark(x, y, tip.z, tip.visibility)
    return HandDetection(tuple(landmarks), detection.confidence)


class MediaPipeHandDetector:
    """Optional MediaPipe adapter; imports the heavy dependency only on use."""

    def __init__(self, config: VisionConfig | None = None) -> None:
        self.config = config or VisionConfig()
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("MediaPipe is required for live hand tracking; install with `pip install -e '.[vision]'`") from exc
        self._hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=self.config.confidence_threshold, min_tracking_confidence=self.config.confidence_threshold)

    def detect(self, image: Any) -> HandDetection | None:
        result = self._hands.process(image)
        if not result.multi_hand_landmarks:
            return None
        hand = result.multi_hand_landmarks[0]
        landmarks = tuple(Landmark(point.x, point.y, point.z) for point in hand.landmark)
        confidence = min((point.visibility for point in landmarks), default=1.0)
        return HandDetection(landmarks, confidence)

    def close(self) -> None:
        self._hands.close()
