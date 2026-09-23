from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PORT = int(os.getenv("PROJECTED_BACKEND_PORT", "8766"))
MODEL_DIR = Path(os.getenv("PROJECTED_MODEL_DIR", ".models/smollm-135m"))
MODEL = MODEL_DIR / "model_q4.onnx"
TOKENIZER = MODEL_DIR / "tokenizer.json"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        payload = {
            "ok": MODEL.is_file() and TOKENIZER.is_file(),
            "model": "SmolLM-135M-Instruct-ONNX",
            "model_bundled": MODEL.is_file() and TOKENIZER.is_file(),
            "camera_port": 8765,
            "version": "v2",
        }
        body = json.dumps(payload).encode()
        self.send_response(200 if payload["ok"] else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
