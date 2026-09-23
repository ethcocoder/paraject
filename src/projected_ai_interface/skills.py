"""Documented skills and allowlisted tool dispatch."""
from __future__ import annotations

import re
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
    """Explicit allowlist: only registered Python callables can be dispatched."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, function: Callable[..., Any]) -> None:
        if not name or not callable(function):
            raise ValueError("tools require a name and callable")
        self._tools[name] = function

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        function = self._tools.get(name)
        if function is None:
            return ToolResult(False, error=f"tool not allowlisted: {name}")
        if not isinstance(arguments, dict):
            return ToolResult(False, error="tool arguments must be an object")
        try:
            return ToolResult(True, result=function(**arguments))
        except (TypeError, ValueError, FileNotFoundError, PermissionError) as exc:
            return ToolResult(False, error=str(exc))
