from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if (ROOT / "src").is_dir():
    sys.path.insert(0, str(ROOT / "src"))

from projected_ai_interface.live_service import build_live_agent_from_env  # noqa: E402

PORT = int(os.getenv("PROJECTED_BACKEND_PORT", "8766"))
MODEL_DIR = Path(os.getenv("PROJECTED_MODEL_DIR", ".models/smollm-135m"))
MODEL = MODEL_DIR / "model_q4.onnx"
TOKENIZER = MODEL_DIR / "tokenizer.json"
agent = None
startup_error: str | None = None


def snapshot() -> dict:
    model_bundled = MODEL.is_file() and TOKENIZER.is_file()
    payload = {
        "ok": bool(agent and agent.health()["ok"]),
        "model": "SmolLM-135M-Instruct-ONNX",
        "model_bundled": model_bundled,
        "vision_configured": bool(os.getenv("OPENAI_API_KEY")),
        "camera_port": int(os.getenv("PROJECTED_CAMERA_PORT", "8765")),
        "version": "v2-live",
        "startup_error": startup_error,
    }
    if agent:
        payload.update(agent.health())
    return payload


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/health", "/status"}:
            self.send_error(404)
            return
        payload = snapshot()
        body = json.dumps(payload).encode()
        self.send_response(200 if payload["model_bundled"] else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    if not MODEL.is_file() or not TOKENIZER.is_file():
        startup_error = "bundled SmolLM model artifacts are missing"
    elif not os.getenv("OPENAI_API_KEY"):
        startup_error = "OPENAI_API_KEY is required for live vision inference"
    else:
        try:
            agent = build_live_agent_from_env()
            agent.start()
        except Exception as exc:
            startup_error = str(exc) or exc.__class__.__name__
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(json.dumps(snapshot()), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if agent:
            agent.stop()
