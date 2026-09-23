from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

from openai import OpenAI


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: parse_demo_image.py IMAGE")
    image_path = Path(sys.argv[1]).resolve()
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-5",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a conservative visual interaction parser. Return JSON only with exactly these keys: clicked, target_label, confidence. clicked is true only when a person's fingertip visibly contacts a projected folder icon. Never infer a filesystem path from the image. target_label should be the visible folder label or null. confidence is a number from 0 to 1.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Parse this projected desktop interaction image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                ],
            },
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    result = json.loads(content)
    required = {"clicked", "target_label", "confidence"}
    if set(result) != required or not isinstance(result["clicked"], bool) or not isinstance(result["confidence"], (int, float)):
        raise RuntimeError("vision parser returned an invalid schema")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
