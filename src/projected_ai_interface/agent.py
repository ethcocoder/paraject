"""Phase 8 local small-LLM agent runtime.

The runtime deliberately keeps model output at the structured-action boundary. The
model can select a documented, registered tool, but it cannot provide shell text or
bypass the tool registry.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .skills import SkillRegistry, ToolRegistry, ToolResult


SYSTEM_PROMPT = """You are the Projected AI Interface local agent. Choose exactly one registered skill when an action is needed. Never output shell commands, code, or unregistered tools. Return JSON only with exactly these keys: tool and arguments. The tool value must be a documented tool name or null. arguments must always be an object. If no safe skill applies, return tool=null and arguments={}."""


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration, overridable with environment variables."""

    base_url: str = "http://127.0.0.1:11434/v1"
    model: str = "tinyllama"
    api_key: str = "local"
    timeout_seconds: float = 30.0
    max_retries: int = 1

    @classmethod
    def from_env(cls) -> "AgentConfig":
        def positive_float(name: str, default: float) -> float:
            try:
                value = float(os.getenv(name, default))
                return value if value > 0 else default
            except (TypeError, ValueError):
                return default

        def nonnegative_int(name: str, default: int) -> int:
            try:
                value = int(os.getenv(name, default))
                return max(0, value)
            except (TypeError, ValueError):
                return default

        return cls(
            base_url=os.getenv("PROJECTED_AGENT_BASE_URL", cls.base_url),
            model=os.getenv("PROJECTED_AGENT_MODEL", cls.model),
            api_key=os.getenv("PROJECTED_AGENT_API_KEY", cls.api_key),
            timeout_seconds=positive_float("PROJECTED_AGENT_TIMEOUT", cls.timeout_seconds),
            max_retries=nonnegative_int("PROJECTED_AGENT_RETRIES", cls.max_retries),
        )


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
    attempts: int = 1
    status: str = "success"


class AgentProvider(Protocol):
    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> Any: ...


class OpenAICompatibleProvider:
    """Adapter for local Ollama/llama.cpp-style OpenAI-compatible servers."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        model: str = "tinyllama",
        api_key: str = "local",
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.base_url, self.model, self.api_key = base_url.rstrip("/"), model, api_key
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_config(cls, config: AgentConfig) -> "OpenAICompatibleProvider":
        return cls(config.base_url, config.model, config.api_key, config.timeout_seconds)

    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"local model HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"local model unavailable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("local model request timed out") from exc


class AgentRuntime:
    def __init__(
        self,
        provider: AgentProvider,
        skills: SkillRegistry,
        tools: ToolRegistry,
        *,
        max_retries: int = 1,
    ) -> None:
        self.provider, self.skills, self.tools = provider, skills, tools
        self.max_retries = max(0, max_retries)

    def build_messages(self, request: str, event: dict[str, Any] | None = None) -> list[dict[str, str]]:
        skill_context = "\n\n".join(
            f"SKILL {skill.name}\nPurpose: {skill.purpose}\nInputs: {skill.inputs}\nSafety: {skill.safety}\nTool: {skill.tool}"
            for name in self.skills.names()
            for skill in [self.skills.get(name)]
            if skill.tool in self.tools.names()
        )
        user = f"Request: {request}\nEvent: {json.dumps(event or {}, sort_keys=True)}\nAvailable skills:\n{skill_context}"
        return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]

    def tool_schemas(self) -> list[dict[str, Any]]:
        """Expose only tools that are both registered and documented."""
        schemas = []
        for name in self.skills.names():
            skill = self.skills.get(name)
            if skill.tool not in self.tools.names():
                continue
            schemas.append({
                "type": "function",
                "function": {
                    "name": skill.tool,
                    "description": skill.purpose,
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": True},
                },
            })
        return schemas

    def run(self, request: str, event: dict[str, Any] | None = None) -> AgentResult:
        started = time.perf_counter()
        messages = self.build_messages(request, event)
        last_error = "agent did not return a valid action"
        attempts = 0
        for attempt in range(self.max_retries + 1):
            attempts = attempt + 1
            try:
                response = self.provider.complete(messages, self.tool_schemas())
                action = self._parse_action(response)
                self._validate_action(action)
                if action.tool is None:
                    return self._result(True, action, None, None, started, attempts, "noop")
                result = self.tools.call(action.tool, action.arguments)
                return self._result(result.ok, action, result, result.error, started, attempts, "success" if result.ok else "tool_error")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    messages.append({"role": "user", "content": "Invalid or unavailable response. Return only a strict JSON object with exactly tool and arguments, using a documented registered tool or null."})
        return self._result(False, None, None, last_error, started, attempts, "provider_error" if "model" in last_error or "local" in last_error else "invalid_output")

    @staticmethod
    def _result(ok: bool, action: AgentAction | None, tool_result: ToolResult | None, error: str | None, started: float, attempts: int, status: str) -> AgentResult:
        return AgentResult(ok, action, tool_result, error, (time.perf_counter() - started) * 1000, attempts, status)

    @staticmethod
    def _parse_action(response: Any) -> AgentAction:
        data = response
        if isinstance(response, dict) and "choices" in response:
            choices = response.get("choices")
            if not isinstance(choices, list) or not choices:
                raise ValueError("agent response choices must be non-empty")
            message = choices[0].get("message", {})
            calls = message.get("tool_calls") or []
            if calls:
                function = calls[0].get("function", {})
                data = {"tool": function.get("name"), "arguments": json.loads(function.get("arguments", "{}"))}
            else:
                data = json.loads(message.get("content") or "{}")
        elif isinstance(response, str):
            data = json.loads(response)
        if not isinstance(data, dict) or set(data) - {"tool", "arguments"} or "tool" not in data or "arguments" not in data:
            raise ValueError("agent response must contain exactly tool and arguments")
        if not isinstance(data["arguments"], dict):
            raise ValueError("agent arguments must be an object")
        tool = data["tool"]
        if tool is not None and (not isinstance(tool, str) or not tool.strip()):
            raise ValueError("tool must be a non-empty string or null")
        return AgentAction(tool, data["arguments"])

    def _validate_action(self, action: AgentAction) -> None:
        if action.tool is None:
            return
        if action.tool not in self.tools.names():
            raise ValueError(f"tool not registered: {action.tool}")
        matching = [self.skills.get(name) for name in self.skills.names() if self.skills.get(name).tool == action.tool]
        if not matching:
            raise ValueError(f"tool has no documented skill: {action.tool}")
        if not all(isinstance(key, str) for key in action.arguments):
            raise ValueError("tool argument keys must be strings")
