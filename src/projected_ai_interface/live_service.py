"""Live local-network camera service for the packaged desktop runtime."""
from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .agent import AgentRuntime, SmolLMCausalProvider
from .builtin_tools import PathSandbox, open_folder
from .camera import CameraFrame, NetworkCameraSource
from .discovery import DiscoveryAdvertisement
from .skills import SkillRegistry, ToolRegistry


class VisionProvider(Protocol):
    def analyze(self, frame: CameraFrame) -> dict[str, Any]: ...


class OpenAIVisionProvider:
    """Small remote vision adapter; no vision model is downloaded to the desktop."""

    def __init__(self, api_key: str, *, model: str = "gpt-5", timeout_seconds: float = 30.0, base_url: str = "https://api.openai.com/v1") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for live vision inference")
        self.api_key, self.model, self.timeout_seconds, self.base_url = api_key, model, timeout_seconds, base_url.rstrip("/")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("live vision requires the openai package") from exc
        if "PROJECTED_VISION_BASE_URL" not in os.environ and (os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")):
            self.client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        else:
            self.client = OpenAI(api_key=api_key, base_url=self.base_url, timeout=timeout_seconds)

    def analyze(self, frame: CameraFrame) -> dict[str, Any]:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("live vision requires opencv-python") from exc
        ok, encoded = cv2.imencode(".jpg", frame.image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            raise ValueError("unable to encode camera frame")
        image = base64.b64encode(encoded.tobytes()).decode("ascii")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": "Return JSON only with exactly clicked, target_label, confidence. clicked is true only when a fingertip visibly touches a projected folder. Never return filesystem paths."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Parse this projected desktop interaction camera frame."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}},
                    ]},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            event = json.loads(content)
        except Exception as exc:
            if "401" in str(exc):
                raise RuntimeError("vision provider authentication failed") from exc
            raise RuntimeError(f"vision provider unavailable: {exc}") from exc
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("vision provider returned invalid structured output") from exc
        if set(event) != {"clicked", "target_label", "confidence"}:
            raise ValueError("vision event schema mismatch")
        event["clicked"] = bool(event["clicked"])
        event["target_label"] = str(event["target_label"])
        event["confidence"] = float(event["confidence"])
        return event


@dataclass(frozen=True)
class Target:
    target_id: str
    label: str
    path: Path
    action: str = "open_folder"


class TargetRegistry:
    def __init__(self, targets: list[Target]) -> None:
        self._targets = {target.label.casefold(): target for target in targets}
        if not self._targets:
            raise ValueError("at least one target is required")

    def resolve(self, label: str) -> Target | None:
        return self._targets.get(label.strip().casefold())

    def labels(self) -> list[str]:
        return sorted(target.label for target in self._targets.values())


@dataclass
class LiveMetrics:
    frames_seen: int = 0
    vision_events: int = 0
    actions_attempted: int = 0
    actions_succeeded: int = 0
    errors: int = 0
    last_error: str | None = None
    last_event: dict[str, Any] | None = None
    last_action: dict[str, Any] | None = None


class LiveCameraAgent:
    """Own the complete mobile camera -> tool execution lifecycle."""

    def __init__(
        self,
        *,
        model_path: str | Path,
        tokenizer_path: str | Path,
        vision: VisionProvider,
        root: str | Path,
        host: str = "0.0.0.0",
        port: int = 8765,
        launch_folders: bool = False,
        cooldown_seconds: float = 1.0,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        documents = self.root / "Documents"
        documents.mkdir(parents=True, exist_ok=True)
        self.vision = vision
        self.source = NetworkCameraSource(host=host, port=port)
        self.discovery = DiscoveryAdvertisement(port=port, name="Projected AI Desktop")
        self.metrics = LiveMetrics()
        self.targets = TargetRegistry([Target("documents_folder", "Documents", documents)])
        self.skills = SkillRegistry(); self.skills.load_directory("skills")
        self.tools = ToolRegistry()
        sandbox = PathSandbox([self.root])
        self.tools.register("open_folder", lambda path: open_folder(path, sandbox, launch=launch_folders))
        self.agent = AgentRuntime(SmolLMCausalProvider(str(model_path), str(tokenizer_path), max_new_tokens=64), self.skills, self.tools, max_retries=0)
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self._last_action_at = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        try:
            self.source.open()
            self.discovery.start()
        except Exception:
            self.source.close()
            raise
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="projected-live-agent", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.source.close()
        self.discovery.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None

    def _run(self) -> None:
        try:
            for frame in self.source.frames():
                if self._stop.is_set():
                    break
                self.metrics.frames_seen += 1
                try:
                    self._process_frame(frame)
                except Exception as exc:
                    self.metrics.errors += 1
                    self.metrics.last_error = str(exc) or exc.__class__.__name__
        except Exception as exc:
            self._start_error = str(exc)
            self.metrics.errors += 1
            self.metrics.last_error = self._start_error

    def _process_frame(self, frame: CameraFrame) -> None:
        event = self.vision.analyze(frame)
        self.metrics.last_event = event
        if not event.get("clicked") or float(event.get("confidence", 0.0)) < 0.80:
            return
        self.metrics.vision_events += 1
        target = self.targets.resolve(str(event.get("target_label", "")))
        if target is None or target.action != "open_folder":
            return
        now = time.monotonic()
        if now - self._last_action_at < self.cooldown_seconds:
            return
        self._last_action_at = now
        self.metrics.actions_attempted += 1
        runtime_event = {
            "clicked": True,
            "target_id": target.target_id,
            "target_label": target.label,
            "confidence": float(event["confidence"]),
        }
        request = f"The vision model detected a touch on {target.label}. The only allowed tool is open_folder. Call open_folder now for the approved path: {target.path}. Return exactly JSON with tool and arguments and no explanation."
        result = self.agent.run(request, runtime_event)
        self.metrics.last_action = {
            "ok": result.ok,
            "status": result.status,
            "tool": result.action.tool if result.action else None,
            "tool_result": result.tool_result.result if result.tool_result and result.tool_result.ok else None,
            "error": result.error,
        }
        if result.ok:
            self.metrics.actions_succeeded += 1

    def health(self) -> dict[str, Any]:
        return {
            "ok": self._thread is not None and self._thread.is_alive() and self._start_error is None,
            "receiver": self.source.is_open,
            "discovery": self.discovery._zeroconf is not None,
            "model": "SmolLM-135M-Instruct-ONNX",
            "skills": self.skills.names(),
            "targets": self.targets.labels(),
            "metrics": self.metrics.__dict__,
            "camera_metrics": self.source.metrics.snapshot(),
            "port": self.source.port,
            "last_error": self.metrics.last_error,
        }


def build_live_agent_from_env() -> LiveCameraAgent:
    model_dir = Path(os.getenv("PROJECTED_MODEL_DIR", ".models/smollm-135m"))
    root = Path(os.getenv("PROJECTED_SANDBOX_ROOT", str(Path.home() / "Documents")))
    vision = OpenAIVisionProvider(
        os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("PROJECTED_VISION_MODEL", "gpt-5"),
        base_url=os.getenv("PROJECTED_VISION_BASE_URL", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")),
    )
    return LiveCameraAgent(
        model_path=model_dir / "model_q4.onnx",
        tokenizer_path=model_dir / "tokenizer.json",
        vision=vision,
        root=root,
        host=os.getenv("PROJECTED_CAMERA_HOST", "0.0.0.0"),
        port=int(os.getenv("PROJECTED_CAMERA_PORT", "8765")),
        launch_folders=os.getenv("PROJECTED_LAUNCH_FOLDERS", "0") == "1",
    )
