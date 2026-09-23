"""Phase 2 camera abstraction, webcam source, and capture metrics."""
from __future__ import annotations

import time
import asyncio
import queue
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Iterator


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


class JPEGFrameDecoder:
    """Decode one binary JPEG payload without retaining the encoded bytes."""

    def __call__(self, payload: bytes) -> tuple[Any, int, int]:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("JPEG decoding requires opencv-python; install with `pip install -e '.[camera]'`") from exc
        image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("invalid JPEG frame")
        height, width = image.shape[:2]
        return image, int(width), int(height)


class NetworkCameraSource(CameraSource):
    """Receive binary JPEG frames from the mobile WebSocket client.

    The receiver is local-network oriented and intentionally accepts only binary
    messages on the documented ``/frames`` path. A bounded queue prevents a slow
    vision pipeline from retaining unbounded camera data; old frames are dropped
    instead. The source uses a background asyncio loop so the existing synchronous
    ``CameraSource`` interface remains unchanged.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        *,
        path: str = "/frames",
        queue_size: int = 3,
        read_timeout: float = 0.25,
        max_frame_bytes: int = 8 * 1024 * 1024,
        decoder: Callable[[bytes], tuple[Any, int, int]] | None = None,
    ) -> None:
        super().__init__()
        if not 0 < port < 65536 or queue_size < 1 or read_timeout <= 0 or max_frame_bytes < 1:
            raise ValueError("invalid network camera configuration")
        self.host, self.port, self.path = host, port, path
        self.queue_size, self.read_timeout, self.max_frame_bytes = queue_size, read_timeout, max_frame_bytes
        self.decoder = decoder or JPEGFrameDecoder()
        self._frames: queue.Queue[tuple[bytes, float, int]] = queue.Queue(maxsize=queue_size)
        self._opened = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self.received_frames = 0
        self.dropped_frames = 0
        self.invalid_frames = 0

    @property
    def is_open(self) -> bool:
        return self._opened

    def open(self) -> None:
        if self._opened:
            return
        self._ready.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._run_server, name="projected-camera-ws", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5):
            self.close()
            raise RuntimeError("timed out starting WebSocket camera receiver")
        if self._startup_error is not None:
            error = self._startup_error
            self.close()
            raise RuntimeError(f"WebSocket camera receiver unavailable: {error}") from error
        self._opened = True

    def read(self) -> CameraFrame | None:
        if not self._opened:
            return None
        try:
            payload, captured_at, sequence = self._frames.get(timeout=self.read_timeout)
        except queue.Empty:
            return None
        try:
            image, width, height = self.decoder(payload)
        except (ValueError, TypeError, RuntimeError):
            self.invalid_frames += 1
            return None
        return CameraFrame(image, captured_at, sequence, width, height)

    def close(self) -> None:
        self._opened = False
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None
        self._loop = None
        self._stop_event = None

    def _run_server(self) -> None:
        try:
            import websockets
        except ImportError as exc:
            self._startup_error = RuntimeError("NetworkCameraSource requires websockets; install with `pip install -e '.[network]'`")
            self._ready.set()
            return
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        self._stop_event = asyncio.Event()

        async def runner() -> None:
            try:
                server = await websockets.serve(self._handle_client, self.host, self.port, max_size=self.max_frame_bytes)
            except BaseException as exc:
                self._startup_error = exc
                self._ready.set()
                return
            self._ready.set()
            await self._stop_event.wait()
            server.close()
            await server.wait_closed()

        try:
            loop.run_until_complete(runner())
        finally:
            loop.close()

    async def _handle_client(self, websocket: Any) -> None:
        request_path = getattr(websocket, "path", None)
        request = getattr(websocket, "request", None)
        if request_path is None and request is not None:
            request_path = getattr(request, "path", None)
        if request_path is not None and request_path != self.path:
            await websocket.close(code=1008, reason="unsupported path")
            return
        async for payload in websocket:
            if not isinstance(payload, (bytes, bytearray, memoryview)):
                continue
            payload = bytes(payload)
            if not payload or len(payload) > self.max_frame_bytes:
                self.invalid_frames += 1
                continue
            sequence = self.received_frames
            self.received_frames += 1
            item = (payload, time.monotonic(), sequence)
            try:
                self._frames.put_nowait(item)
            except queue.Full:
                try:
                    self._frames.get_nowait()
                except queue.Empty:
                    pass
                self.dropped_frames += 1
                self._frames.put_nowait(item)
