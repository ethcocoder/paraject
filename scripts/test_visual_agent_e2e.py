from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from openai import OpenAI

from projected_ai_interface.agent import AgentRuntime
from projected_ai_interface.builtin_tools import PathSandbox, open_folder
from projected_ai_interface.skills import SkillRegistry, ToolRegistry


IMAGE = Path("/home/ubuntu/paraject/demo_person_clicking_folder_wide.png")
ROOT = Path("/home/ubuntu/paraject/demo_sandbox").resolve()
DOCUMENTS = ROOT / "Documents"


class VisionSkillProvider:
    """Vision model adapter that returns text for the normal AgentRuntime parser."""

    def __init__(self, image: Path) -> None:
        self.image_data = base64.b64encode(image.read_bytes()).decode("ascii")
        self.client = OpenAI()

    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> str:
        assert "SKILL open_folder" in messages[-1]["content"]
        assert any(item["function"]["name"] == "open_folder" for item in tools)
        enriched = [dict(message) for message in messages]
        enriched[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": enriched[-1]["content"] + "\nInspect the attached image. If a fingertip is visibly touching the Documents folder, select open_folder. The only approved mapping is Documents -> " + str(DOCUMENTS) + ". Return only the exact JSON action schema."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{self.image_data}"}},
            ],
        }
        response = self.client.chat.completions.create(
            model="gpt-5",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are the visual decision layer for a safe local desktop agent. Never invent paths or tools. Use only the documented skills and approved mapping in the user message."},
                *enriched,
            ],
            tools=tools,
            tool_choice="none",
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"


def main() -> int:
    if not IMAGE.is_file():
        raise SystemExit(f"missing demo image: {IMAGE}")
    DOCUMENTS.mkdir(parents=True, exist_ok=True)
    skills = SkillRegistry()
    loaded = skills.load_directory("skills")
    tools = ToolRegistry()
    sandbox = PathSandbox([ROOT])
    tools.register("open_folder", lambda path: open_folder(path, sandbox))
    runtime = AgentRuntime(VisionSkillProvider(IMAGE), skills, tools, max_retries=1)
    result = runtime.run("A person is touching a projected folder. Select the safe documented action.", {"source": "generated_demo_image", "confidence_gate": 0.8})
    output = {
        "skills_loaded": loaded,
        "skill_names": skills.names(),
        "tool_names": tools.names(),
        "skill_context_seen_by_model": True,
        "tool_schema_seen_by_model": True,
        "agent_ok": result.ok,
        "agent_status": result.status,
        "action": {"tool": result.action.tool, "arguments": result.action.arguments} if result.action else None,
        "tool_result": result.tool_result.result if result.tool_result and result.tool_result.ok else None,
        "tool_error": result.tool_result.error if result.tool_result and not result.tool_result.ok else None,
        "attempts": result.attempts,
    }
    print(json.dumps(output, indent=2))
    if not (result.ok and result.action and result.action.tool == "open_folder" and result.tool_result and result.tool_result.ok):
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
