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

    backend: str = "onnx"
    base_url: str = "http://127.0.0.1:11434/v1"
    model: str = "tinyllama"
    api_key: str = "local"
    timeout_seconds: float = 30.0
    max_retries: int = 1
    onnx_model: str | None = None
    onnx_tokenizer: str | None = None
    onnx_max_new_tokens: int = 64
    onnx_labels: tuple[str, ...] = ("null", "open_folder", "list_folder")

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
            backend=os.getenv("PROJECTED_AGENT_BACKEND", cls.backend).lower(),
            base_url=os.getenv("PROJECTED_AGENT_BASE_URL", cls.base_url),
            model=os.getenv("PROJECTED_AGENT_MODEL", cls.model),
            api_key=os.getenv("PROJECTED_AGENT_API_KEY", cls.api_key),
            timeout_seconds=positive_float("PROJECTED_AGENT_TIMEOUT", cls.timeout_seconds),
            max_retries=nonnegative_int("PROJECTED_AGENT_RETRIES", cls.max_retries),
            onnx_model=os.getenv("PROJECTED_AGENT_ONNX_MODEL") or None,
            onnx_tokenizer=os.getenv("PROJECTED_AGENT_ONNX_TOKENIZER") or None,
            onnx_max_new_tokens=nonnegative_int("PROJECTED_AGENT_ONNX_MAX_NEW_TOKENS", cls.onnx_max_new_tokens) or cls.onnx_max_new_tokens,
            onnx_labels=tuple(filter(None, os.getenv("PROJECTED_AGENT_ONNX_LABELS", ",".join(cls.onnx_labels)).split(","))),
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


class OnnxActionProvider:
    """Run a small local ONNX action classifier without a model server.

    The model is expected to accept an ``input_ids`` int64 tensor shaped
    ``[1, sequence]`` and return logits shaped ``[1, label_count]``. This is a
    deliberately narrow adapter for tiny local classifiers: tokenization is a
    deterministic vocabulary lookup and the result is converted into the same
    strict structured action consumed by ``AgentRuntime``. A full language model
    can use the same provider boundary once its tokenizer/output contract is
    supplied.
    """

    def __init__(
        self,
        model_path: str,
        *,
        vocabulary: dict[str, int] | None = None,
        labels: tuple[str, ...] = ("null", "open_folder", "list_folder"),
        max_tokens: int = 64,
    ) -> None:
        if not model_path:
            raise ValueError("model_path is required")
        if not labels or max_tokens < 1:
            raise ValueError("labels and max_tokens are required")
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("OnnxActionProvider requires onnxruntime and numpy; install with `pip install -e '.[onnx]'`") from exc
        self._np = np
        self.labels = labels
        self.vocabulary = {word.lower(): int(index) for word, index in (vocabulary or {}).items()}
        self.max_tokens = max_tokens
        try:
            self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        except Exception as exc:
            raise RuntimeError(f"unable to load ONNX model: {exc}") from exc

    @classmethod
    def from_config(cls, config: AgentConfig, *, vocabulary: dict[str, int] | None = None) -> "OnnxActionProvider":
        if not config.onnx_model:
            raise ValueError("PROJECTED_AGENT_ONNX_MODEL is required for the ONNX backend")
        return cls(config.onnx_model, vocabulary=vocabulary, labels=config.onnx_labels)

    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        request = messages[-1].get("content", "") if messages else ""
        ids = [self.vocabulary.get(token, 0) for token in request.lower().split()[: self.max_tokens]]
        ids.extend([0] * (self.max_tokens - len(ids)))
        input_ids = self._np.asarray([ids], dtype=self._np.int64)
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: input_ids})
        if not outputs:
            raise RuntimeError("ONNX model returned no outputs")
        logits = self._np.asarray(outputs[0])
        if logits.ndim != 2 or logits.shape[0] != 1 or logits.shape[1] != len(self.labels):
            raise ValueError("ONNX action model must return [1, label_count] logits")
        label = self.labels[int(self._np.argmax(logits[0]))]
        return {"tool": None if label == "null" else label, "arguments": {}}


class SmolLMCausalProvider:
    """Generate structured actions from a causal ONNX language model.

    This adapter targets the exported SmolLM graph used by
    ``scripts/verify_smollm_onnx.py``: an initial prompt pass followed by
    greedy one-token KV-cache decoding.  It deliberately returns generated
    text to let ``AgentRuntime`` apply the same strict action validation used
    by every other provider.
    """

    def __init__(self, model_path: str, tokenizer_path: str, *, max_new_tokens: int = 64) -> None:
        if not model_path or not tokenizer_path:
            raise ValueError("model_path and tokenizer_path are required")
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be positive")
        try:
            import numpy as np
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise RuntimeError("SmolLMCausalProvider requires onnxruntime, numpy, and tokenizers; install with `pip install -e '.[onnx]'`") from exc
        self._np = np
        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        try:
            self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        except Exception as exc:
            raise RuntimeError(f"unable to load causal ONNX model: {exc}") from exc
        self.max_new_tokens = max_new_tokens
        self._inputs = {spec.name: spec for spec in self.session.get_inputs()}
        self._outputs = {spec.name: spec for spec in self.session.get_outputs()}
        self._past_names = sorted(name for name in self._inputs if name.startswith("past_key_values."))
        if not {"input_ids", "attention_mask", "position_ids"}.issubset(self._inputs):
            raise RuntimeError("causal ONNX model must expose input_ids, attention_mask, and position_ids")
        if not self._past_names or not all("present." + name[len("past_key_values."):] in self._outputs for name in self._past_names):
            raise RuntimeError("causal ONNX model has an incomplete KV-cache graph contract")
        self._eos_id = next((self.tokenizer.token_to_id(token) for token in ("<|im_end|>", "</s>", "<eos>") if self.tokenizer.token_to_id(token) is not None), 2)

    @classmethod
    def from_config(cls, config: AgentConfig) -> "SmolLMCausalProvider":
        if not config.onnx_model:
            raise ValueError("PROJECTED_AGENT_ONNX_MODEL is required for the causal ONNX backend")
        if not config.onnx_tokenizer:
            raise ValueError("PROJECTED_AGENT_ONNX_TOKENIZER is required for the causal ONNX backend")
        return cls(config.onnx_model, config.onnx_tokenizer, max_new_tokens=config.onnx_max_new_tokens)

    @staticmethod
    def _prompt(messages: list[dict[str, str]]) -> str:
        return "".join(
            f"<|im_start|>{message['role']}\n{message.get('content', '')}<|im_end|>\n"
            for message in messages
        ) + "<|im_start|>assistant\n"

    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> str:
        del tools  # The tool contract is already included in the runtime's user prompt.
        encoded = self.tokenizer.encode(self._prompt(messages), add_special_tokens=False)
        token_ids = encoded.ids
        if not token_ids:
            raise RuntimeError("causal ONNX tokenizer produced an empty prompt")
        generated = list(token_ids)
        feeds: dict[str, Any] = {
            "input_ids": self._np.asarray([token_ids], dtype=self._np.int64),
            "attention_mask": self._np.ones((1, len(token_ids)), dtype=self._np.int64),
            "position_ids": self._np.arange(len(token_ids), dtype=self._np.int64)[None, :],
        }
        for name in self._past_names:
            shape = self._inputs[name].shape
            try:
                heads, head_dim = int(shape[1]), int(shape[3])
            except (IndexError, TypeError, ValueError) as exc:
                raise RuntimeError(f"unsupported KV-cache input shape for {name}: {shape}") from exc
            feeds[name] = self._np.zeros((1, heads, 0, head_dim), dtype=self._np.float32)

        output_specs = list(self.session.get_outputs())
        by_name = dict(zip((spec.name for spec in output_specs), self.session.run(None, feeds)))
        for _ in range(self.max_new_tokens):
            if "logits" not in by_name:
                raise RuntimeError("causal ONNX model returned no logits output")
            next_id = int(self._np.argmax(by_name["logits"][0, -1]))
            generated.append(next_id)
            if next_id == self._eos_id:
                break
            total_length = len(generated)
            feeds = {
                "input_ids": self._np.asarray([[next_id]], dtype=self._np.int64),
                "attention_mask": self._np.ones((1, total_length), dtype=self._np.int64),
                "position_ids": self._np.asarray([[total_length - 1]], dtype=self._np.int64),
            }
            for name in self._past_names:
                feeds[name] = by_name["present." + name[len("past_key_values."):]]
            by_name = dict(zip((spec.name for spec in output_specs), self.session.run(None, feeds)))
        return self.tokenizer.decode(generated[len(token_ids):], skip_special_tokens=True).strip()


def provider_from_config(config: AgentConfig, *, vocabulary: dict[str, int] | None = None) -> AgentProvider:
    """Construct the configured standalone or server-backed provider."""
    if config.backend == "onnx":
        return OnnxActionProvider.from_config(config, vocabulary=vocabulary)
    if config.backend in {"smollm", "onnx-causal", "onnx-smollm"}:
        return SmolLMCausalProvider.from_config(config)
    if config.backend in {"openai", "openai-compatible", "ollama"}:
        return OpenAICompatibleProvider.from_config(config)
    raise ValueError(f"unsupported agent backend: {config.backend}")


class AgentRuntime:
    def __init__(
        self,
        provider: AgentProvider,
        skills: SkillRegistry,
        tools: ToolRegistry,
        *,
        max_retries: int = 1,
        max_request_chars: int = 4096,
        max_event_chars: int = 8192,
    ) -> None:
        if max_request_chars < 1 or max_event_chars < 1:
            raise ValueError("runtime input limits must be positive")
        self.provider, self.skills, self.tools = provider, skills, tools
        self.max_retries = max(0, max_retries)
        self.max_request_chars, self.max_event_chars = max_request_chars, max_event_chars

    def build_messages(self, request: str, event: dict[str, Any] | None = None) -> list[dict[str, str]]:
        if not isinstance(request, str) or not request.strip():
            raise ValueError("agent request must be a non-empty string")
        if len(request) > self.max_request_chars:
            raise ValueError(f"agent request exceeds {self.max_request_chars} characters")
        if event is not None and not isinstance(event, dict):
            raise ValueError("agent event must be an object")
        event_json = json.dumps(event or {}, sort_keys=True)
        if len(event_json) > self.max_event_chars:
            raise ValueError(f"agent event exceeds {self.max_event_chars} characters")
        skill_context = "\n\n".join(
            f"SKILL {skill.name}\nPurpose: {skill.purpose}\nInputs: {skill.inputs}\nSafety: {skill.safety}\nTool: {skill.tool}"
            for name in self.skills.names()
            for skill in [self.skills.get(name)]
            if skill.tool in self.tools.names()
        )
        user = f"Request: {request}\nEvent: {event_json}\nAvailable skills:\n{skill_context}"
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
        try:
            messages = self.build_messages(request, event)
        except ValueError as exc:
            return self._result(False, None, None, str(exc), started, 0, "invalid_input")
        last_error = "agent did not return a valid action"
        attempts = 0
        for attempt in range(self.max_retries + 1):
            attempts = attempt + 1
            try:
                response = self.provider.complete(messages, self.tool_schemas())
            except Exception as exc:
                last_error = str(exc) or exc.__class__.__name__
                if attempt < self.max_retries:
                    messages.append({"role": "user", "content": "The provider failed. Retry once and return only a strict JSON action."})
                    continue
                return self._result(False, None, None, last_error, started, attempts, "provider_error")
            try:
                action = self._parse_action(response)
                self._validate_action(action)
                if action.tool is None:
                    return self._result(True, action, None, None, started, attempts, "noop")
                result = self.tools.call(action.tool, action.arguments)
                return self._result(result.ok, action, result, result.error, started, attempts, "success" if result.ok else "tool_error")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    messages.append({"role": "user", "content": "Invalid or unavailable response. Return only a strict JSON object with exactly tool and arguments, using a documented registered tool or null."})
        return self._result(False, None, None, last_error, started, attempts, "invalid_output")

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
                data = AgentRuntime._parse_json_text(message.get("content") or "{}")
        elif isinstance(response, str):
            data = AgentRuntime._parse_json_text(response)
        if not isinstance(data, dict) or set(data) - {"tool", "arguments"} or "tool" not in data or "arguments" not in data:
            raise ValueError("agent response must contain exactly tool and arguments")
        if not isinstance(data["arguments"], dict):
            raise ValueError("agent arguments must be an object")
        tool = data["tool"]
        if tool is not None and (not isinstance(tool, str) or not tool.strip()):
            raise ValueError("tool must be a non-empty string or null")
        return AgentAction(tool, data["arguments"])

    @staticmethod
    def _parse_json_text(text: str) -> Any:
        """Parse JSON while accepting a single Markdown code fence."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)

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
