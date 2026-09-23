"""Phase 8 local small-LLM agent runtime."""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .skills import SkillRegistry, ToolRegistry, ToolResult


SYSTEM_PROMPT = """You are the Projected AI Interface local agent. Choose exactly one registered skill when an action is needed. Never output shell commands, code, or unregistered tools. Return JSON only with keys tool and arguments. If no safe skill applies, return tool=null and arguments={}."""


@dataclass(frozen=True)
class AgentAction:
    tool: str | None
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentResult:
    ok: bool
    action: AgentAction | None
    tool_result: ToolResult | None
    error: str | None
    latency_ms: float


class AgentProvider(Protocol):
    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> Any: ...


class OpenAICompatibleProvider:
    """Adapter for local Ollama/llama.cpp-style OpenAI-compatible servers."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434/v1", model: str = "tinyllama", api_key: str = "local") -> None:
        self.base_url, self.model, self.api_key = base_url.rstrip("/"), model, api_key

    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = json.dumps({"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto", "temperature": 0}).encode()
        request = urllib.request.Request(f"{self.base_url}/chat/completions", data=payload, headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())


class AgentRuntime:
    def __init__(self, provider: AgentProvider, skills: SkillRegistry, tools: ToolRegistry, *, max_retries: int = 1) -> None:
        self.provider, self.skills, self.tools, self.max_retries = provider, skills, tools, max(0, max_retries)

    def build_messages(self, request: str, event: dict[str, Any] | None = None) -> list[dict[str, str]]:
        skill_context = "\n\n".join(f"SKILL {skill.name}\nPurpose: {skill.purpose}\nInputs: {skill.inputs}\nSafety: {skill.safety}\nTool: {skill.tool}" for skill in (self.skills.get(name) for name in self.skills.names()))
        user = f"Request: {request}\nEvent: {json.dumps(event or {}, sort_keys=True)}\nAvailable skills:\n{skill_context}"
        return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {"name": skill.tool, "description": skill.purpose, "parameters": {"type": "object", "properties": {}, "additionalProperties": True}}} for name in self.skills.names() for skill in [self.skills.get(name)]]

    def run(self, request: str, event: dict[str, Any] | None = None) -> AgentResult:
        started = time.perf_counter()
        messages = self.build_messages(request, event)
        last_error = "agent did not return a valid action"
        for attempt in range(self.max_retries + 1):
            try:
                response = self.provider.complete(messages, self.tool_schemas())
                action = self._parse_action(response)
                self._validate_action(action)
                if action.tool is None:
                    return AgentResult(True, action, None, None, (time.perf_counter() - started) * 1000)
                result = self.tools.call(action.tool, action.arguments)
                return AgentResult(result.ok, action, result, result.error, (time.perf_counter() - started) * 1000)
            except (ValueError, KeyError, TypeError) as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    messages.append({"role": "user", "content": "Invalid response. Return only valid JSON with a registered tool and object arguments."})
        return AgentResult(False, None, None, last_error, (time.perf_counter() - started) * 1000)

    @staticmethod
    def _parse_action(response: Any) -> AgentAction:
        data = response
        if isinstance(response, dict) and "choices" in response:
            message = response["choices"][0]["message"]
            calls = message.get("tool_calls") or []
            if calls:
                function = calls[0]["function"]
                data = {"tool": function["name"], "arguments": json.loads(function.get("arguments", "{}"))}
            else:
                data = json.loads(message.get("content") or "{}")
        elif isinstance(response, str):
            data = json.loads(response)
        if not isinstance(data, dict) or not isinstance(data.get("arguments", {}), dict):
            raise ValueError("agent response must contain an object named arguments")
        tool = data.get("tool")
        if tool is not None and not isinstance(tool, str):
            raise ValueError("tool must be a string or null")
        return AgentAction(tool, data.get("arguments", {}))

    def _validate_action(self, action: AgentAction) -> None:
        if action.tool is None:
            return
        if action.tool not in self.tools.names():
            raise ValueError(f"tool not registered: {action.tool}")
        matching = [self.skills.get(name) for name in self.skills.names() if self.skills.get(name).tool == action.tool]
        if not matching:
            raise ValueError(f"tool has no documented skill: {action.tool}")
