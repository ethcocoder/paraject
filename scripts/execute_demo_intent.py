from __future__ import annotations

import json
from pathlib import Path

from projected_ai_interface.builtin_tools import PathSandbox, open_folder


ROOT = Path("/home/ubuntu/paraject/demo_sandbox").resolve()
LABEL_TO_PATH = {"Documents": ROOT / "Documents"}


def execute(intent: dict[str, object]) -> dict[str, object]:
    if intent.get("clicked") is not True or float(intent.get("confidence", 0)) < 0.8:
        return {"executed": False, "reason": "low-confidence or no click"}
    label = intent.get("target_label")
    if not isinstance(label, str) or label not in LABEL_TO_PATH:
        return {"executed": False, "reason": "target label is not allowlisted"}
    target = LABEL_TO_PATH[label]
    target.mkdir(parents=True, exist_ok=True)
    result = open_folder(str(target), PathSandbox([ROOT]))
    return {"executed": True, "target_label": label, "tool_result": result}


if __name__ == "__main__":
    intent = {"clicked": True, "target_label": "Documents", "confidence": 0.92}
    print(json.dumps(execute(intent), indent=2))
