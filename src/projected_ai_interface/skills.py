"""Documented skills and allowlisted tool dispatch."""
from __future__ import annotations

import inspect
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Skill:
    name: str
    purpose: str
    preconditions: str
    inputs: str
    output: str
    safety: str
    tool: str
    source: Path


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    result: Any = None
    error: str | None = None
    code: str | None = None


@dataclass(frozen=True)
class ToolExecution:
    name: str
    arguments: dict[str, Any]
    ok: bool
    error: str | None
    elapsed_ms: float


class SkillFormatError(ValueError):
    pass


def parse_skill_markdown(path: str | Path) -> Skill:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip().lower()
            fields[current] = ""
        elif current is not None:
            fields[current] += line + "\n"
    required = ["name", "purpose", "preconditions", "inputs", "output", "safety", "tool"]
    missing = [field for field in required if not fields.get(field, "").strip()]
    if missing:
        raise SkillFormatError(f"{source}: missing sections: {', '.join(missing)}")
    return Skill(fields["name"].strip(), fields["purpose"].strip(), fields["preconditions"].strip(), fields["inputs"].strip(), fields["output"].strip(), fields["safety"].strip(), fields["tool"].strip().splitlines()[0].strip(), source)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def load_directory(self, root: str | Path) -> int:
        count = 0
        for path in sorted(Path(root).rglob("SKILL.md")):
            skill = parse_skill_markdown(path)
            self._skills[skill.name] = skill
            count += 1
        return count

    def get(self, name: str) -> Skill:
        return self._skills[name]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._skills))


class ToolRegistry:
    """Explicit allowlist for Python callables with bounded execution."""

    def __init__(self, *, default_timeout_seconds: float | None = 30.0) -> None:
        if default_timeout_seconds is not None and default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be positive or None")
        self._tools: dict[str, Callable[..., Any]] = {}
        self.default_timeout_seconds = default_timeout_seconds
        self.execution_log: list[ToolExecution] = []

    def register(self, name: str, function: Callable[..., Any]) -> None:
        if not name or not callable(function):
            raise ValueError("tools require a name and callable")
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = function

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def call(self, name: str, arguments: dict[str, Any], *, timeout_seconds: float | None = None) -> ToolResult:
        started = time.perf_counter()
        if name not in self._tools:
            return self._record(name, arguments, ToolResult(False, error=f"tool not allowlisted: {name}", code="unregistered_tool"), started)
        if not isinstance(arguments, dict):
            return self._record(name, {}, ToolResult(False, error="tool arguments must be an object", code="malformed_arguments"), started)
        timeout = self.default_timeout_seconds if timeout_seconds is None else timeout_seconds
        if timeout is not None and timeout <= 0:
            return self._record(name, arguments, ToolResult(False, error="timeout must be positive or None", code="invalid_timeout"), started)
        function = self._tools[name]
        try:
            signature = inspect.signature(function)
            signature.bind(**arguments)
        except (TypeError, ValueError) as exc:
            return self._record(name, arguments, ToolResult(False, error=f"malformed arguments: {exc}", code="malformed_arguments"), started)
        try:
            if timeout is None:
                value = function(**arguments)
            else:
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(function, **arguments)
                try:
                    value = future.result(timeout=timeout)
                finally:
                    # A Python thread cannot be forcefully stopped, but the
                    # caller must not block on a timed-out tool. The worker is
                    # discarded and its result is never exposed.
                    executor.shutdown(wait=False, cancel_futures=True)
            return self._record(name, arguments, ToolResult(True, result=value), started)
        except FutureTimeoutError:
            return self._record(name, arguments, ToolResult(False, error=f"tool timed out after {timeout:g}s", code="timeout"), started)
        except Exception as exc:
            return self._record(name, arguments, ToolResult(False, error=str(exc) or exc.__class__.__name__, code=type(exc).__name__), started)

    def _record(self, name: str, arguments: dict[str, Any], result: ToolResult, started: float) -> ToolResult:
        self.execution_log.append(ToolExecution(name, dict(arguments), result.ok, result.error, (time.perf_counter() - started) * 1000))
        return result
