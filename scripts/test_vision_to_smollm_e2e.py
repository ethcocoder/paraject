from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from openai import OpenAI

from projected_ai_interface.agent import AgentRuntime, SmolLMCausalProvider
from projected_ai_interface.builtin_tools import PathSandbox, open_folder
from projected_ai_interface.skills import SkillRegistry, ToolRegistry

IMAGE = Path("/home/ubuntu/paraject/demo_person_clicking_folder_wide.png")
ROOT = Path("/home/ubuntu/paraject/demo_sandbox").resolve()
DOCUMENTS = ROOT / "Documents"
MODEL = Path("/home/ubuntu/paraject/.models/smollm-135m/model_q4.onnx")
TOKENIZER = Path("/home/ubuntu/paraject/.models/smollm-135m/tokenizer.json")


def vision_event() -> dict[str, object]:
    encoded = base64.b64encode(IMAGE.read_bytes()).decode("ascii")
    response = OpenAI().chat.completions.create(
        model="gpt-5",
        temperature=0,
        messages=[
            {"role": "system", "content": "Return JSON only with exactly clicked, target_label, confidence. clicked is true only if a fingertip visibly touches a projected folder. Never return filesystem paths."},
            {"role": "user", "content": [
                {"type": "text", "text": "Parse this projected desktop interaction image."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
            ]},
        ],
        response_format={"type": "json_object"},
    )
    event = json.loads(response.choices[0].message.content or "{}")
    if set(event) != {"clicked", "target_label", "confidence"} or event.get("clicked") is not True or float(event.get("confidence", 0)) < 0.8:
        raise RuntimeError(f"vision event failed confidence gate: {event}")
    return event


def main() -> int:
    if not IMAGE.is_file() or not MODEL.is_file() or not TOKENIZER.is_file():
        raise SystemExit("missing image or SmolLM artifacts")
    DOCUMENTS.mkdir(parents=True, exist_ok=True)
    event = vision_event()
    skills = SkillRegistry(); skills.load_directory("skills")
    tools = ToolRegistry()
    tools.register("open_folder", lambda path: open_folder(path, PathSandbox([ROOT])))
    provider = SmolLMCausalProvider(str(MODEL), str(TOKENIZER), max_new_tokens=64)
    request = f"The vision model detected this event: {json.dumps(event, sort_keys=True)}. The only allowed tool is open_folder. Call open_folder now for the approved path: {DOCUMENTS}. Return exactly JSON with tool and arguments and no explanation."
    probe_runtime = AgentRuntime(provider, skills, tools, max_retries=0)
    raw_model_response = provider.complete(probe_runtime.build_messages(request, event), probe_runtime.tool_schemas())

    class CachedProvider:
        def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> str:
            return raw_model_response

    runtime = AgentRuntime(CachedProvider(), skills, tools, max_retries=0)
    result = runtime.run(request, event)
    output: dict[str, Any] = {
        "vision_event": event,
        "local_model": "SmolLM-135M-Instruct-ONNX",
        "smollm_response": raw_model_response,
        "skills_loaded": skills.names(),
        "tool_names": tools.names(),
        "agent_ok": result.ok,
        "agent_status": result.status,
        "action": {"tool": result.action.tool, "arguments": result.action.arguments} if result.action else None,
        "tool_result": result.tool_result.result if result.tool_result and result.tool_result.ok else None,
        "tool_error": result.tool_result.error if result.tool_result and not result.tool_result.ok else None,
        "agent_error": result.error,
        "attempts": result.attempts,
    }
    print(json.dumps(output, indent=2))
    if not (result.ok and result.action and result.action.tool == "open_folder" and result.tool_result and result.tool_result.ok):
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
