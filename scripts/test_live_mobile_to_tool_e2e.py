from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import websockets

from projected_ai_interface.live_service import LiveCameraAgent, OpenAIVisionProvider

IMAGE = Path("demo_person_clicking_folder_wide.png")
ROOT = Path("demo_sandbox").resolve()
MODEL = Path(".models/smollm-135m/model_q4.onnx").resolve()
TOKENIZER = Path(".models/smollm-135m/tokenizer.json").resolve()


async def send_mobile_frame() -> None:
    async with websockets.connect("ws://127.0.0.1:8765/frames", max_size=8 * 1024 * 1024) as socket:
        await socket.send(IMAGE.read_bytes())
        await asyncio.sleep(0.2)


def main() -> int:
    if not all(path.is_file() for path in (IMAGE, MODEL, TOKENIZER)):
        raise SystemExit("missing generated image or local SmolLM artifacts")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for the live vision-model phase")
    (ROOT / "Documents").mkdir(parents=True, exist_ok=True)
    agent = LiveCameraAgent(
        model_path=MODEL,
        tokenizer_path=TOKENIZER,
        vision=OpenAIVisionProvider(os.environ["OPENAI_API_KEY"]),
        root=ROOT,
        host="127.0.0.1",
        port=8765,
        launch_folders=False,
        cooldown_seconds=0.0,
    )
    agent.start()
    try:
        asyncio.run(send_mobile_frame())
        for _ in range(600):
            if agent.metrics.actions_succeeded:
                break
            import time
            time.sleep(0.1)
        result = {
            "transport": "mobile JPEG over ws://127.0.0.1:8765/frames",
            "vision": agent.metrics.last_event,
            "model": "SmolLM-135M-Instruct-ONNX",
            "action": agent.metrics.last_action,
            "health": agent.health(),
        }
        print(json.dumps(result, indent=2))
        if not agent.metrics.actions_succeeded:
            raise SystemExit("live mobile-to-tool action did not succeed")
        return 0
    finally:
        agent.stop()


if __name__ == "__main__":
    raise SystemExit(main())
