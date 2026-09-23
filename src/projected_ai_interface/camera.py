"""Phase 2 camera abstraction, webcam source, and capture metrics."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class CameraFrame:
    """A decoded camera frame and capture timestamp."""

    image: Any
    captured_at: float
    sequence: int
    width: int
    height: int


@dataclass
class CameraMetrics:
    frames: int = 0
    dropped_frames: int = 0
    first_frame_at: float | None = None
    last_frame_at: float | None = None
    total_latency_ms: float = 0.0

    @property
    def fps(self) -> float:
        if self.first_frame_at is None or self.last_frame_at is None:
            return 0.0
        elapsed = self.last_frame_at - self.first_frame_at
        return (self.frames - 1) / elapsed if elapsed > 0 and self.frames > 1 else 0.0

    @property
    def average_latency_ms(self) -> float:
        return self.total_latency_ms / self.frames if self.frames else 0.0

    def record(self, frame: CameraFrame, received_at: float | None = None) -> None:
        received_at = time.monotonic() if received_at is None else received_at
        if self.last_frame_at is not None and frame.sequence > 0:
            expected = self.frames
            if frame.sequence > expected:
                self.dropped_frames += frame.sequence - expected
        self.frames += 1
        self.first_frame_at = frame.captured_at if self.first_frame_at is None else self.first_frame_at
        self.last_frame_at = frame.captured_at
        self.total_latency_ms += max(0.0, received_at - frame.captured_at) * 1000

    def snapshot(self) -> dict[str, float | int]:
        return {"frames": self.frames, "dropped_frames": self.dropped_frames, "fps": round(self.fps, 2), "average_latency_ms": round(self.average_latency_ms, 2)}


class CameraSource(ABC):
    """Common interface for webcam, network phone, and future camera sources."""

    def __init__(self) -> None:
        self.metrics = CameraMetrics()
        self._sequence = 0

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> CameraFrame | None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    def frames(self, *, max_frames: int | None = None) -> Iterator[CameraFrame]:
        """Yield available frames and track metrics until closed or exhausted."""
        yielded = 0
        while self.is_open and (max_frames is None or yielded < max_frames):
            frame = self.read()
            if frame is None:
                continue
            self.metrics.record(frame)
            yielded += 1
            yield frame


class WebcamSource(CameraSource):
    """OpenCV-backed webcam source with bounded reconnect attempts."""

    def __init__(self, device: int = 0, width: int = 1280, height: int = 720, reconnect_attempts: int = 3) -> None:
        super().__init__()
        self.device, self.width, self.height = device, width, height
        self.reconnect_attempts = max(0, reconnect_attempts)
        self._capture = None
        self._opened = False

    @property
    def is_open(self) -> bool:
        return self._opened

    def open(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("WebcamSource requires opencv-python; install with `pip install -e '.[camera]'`") from exc
        self._capture = cv2.VideoCapture(self.device)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._opened = bool(self._capture.isOpened())
        if not self._opened:
            self._release()
            raise RuntimeError(f"Unable to open camera device {self.device}")

    def read(self) -> CameraFrame | None:
        if not self._opened or self._capture is None:
            return None
        captured_at = time.monotonic()
        ok, image = self._capture.read()
        if not ok:
            self._opened = False
            self._release()
            return None
        height, width = image.shape[:2]
        frame = CameraFrame(image, captured_at, self._sequence, int(width), int(height))
        self._sequence += 1
        return frame

    def reconnect(self) -> bool:
        for _ in range(self.reconnect_attempts):
            try:
                self.open()
                return True
            except RuntimeError:
                time.sleep(0.05)
        return False

    def close(self) -> None:
        self._opened = False
        self._release()

    def _release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


class SyntheticCameraSource(CameraSource):
    """Deterministic camera source for CI, demos, and pipeline tests."""

    def __init__(self, frames: int = 10, width: int = 320, height: int = 240, interval: float = 0.0) -> None:
        super().__init__()
        self.frame_count, self.width, self.height, self.interval = frames, width, height, interval
        self._opened = False
        self._remaining = 0

    @property
    def is_open(self) -> bool:
        return self._opened

    def open(self) -> None:
        self._remaining = self.frame_count
        self._opened = True

    def read(self) -> CameraFrame | None:
        if not self._opened or self._remaining <= 0:
            self._opened = False
            return None
        if self.interval:
            time.sleep(self.interval)
        frame = CameraFrame(image=None, captured_at=time.monotonic(), sequence=self._sequence, width=self.width, height=self.height)
        self._sequence += 1
        self._remaining -= 1
        return frame

    def close(self) -> None:
        self._opened = False
