from __future__ import annotations

import argparse
import json

from .agent import AgentConfig, AgentRuntime
from .skills import SkillRegistry, ToolRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the Phase 8 agent contract")
    parser.add_argument("--root", default="skills")
    parser.add_argument("--base-url", help="OpenAI-compatible provider base URL")
    parser.add_argument("--model", help="Local model name")
    parser.add_argument("--timeout", type=float, help="Provider timeout in seconds")
    parser.add_argument("--retries", type=int, help="Maximum malformed/provider retries")
    args = parser.parse_args(argv)

    defaults = AgentConfig.from_env()
    config = AgentConfig(
        base_url=args.base_url or defaults.base_url,
        model=args.model or defaults.model,
        api_key=defaults.api_key,
        timeout_seconds=args.timeout if args.timeout is not None else defaults.timeout_seconds,
        max_retries=args.retries if args.retries is not None else defaults.max_retries,
    )
    skills = SkillRegistry()
    skills.load_directory(args.root)
    tools = ToolRegistry()
    print(json.dumps({
        "provider": {
            "base_url": config.base_url,
            "model": config.model,
            "timeout_seconds": config.timeout_seconds,
            "max_retries": config.max_retries,
            "api_key_configured": bool(config.api_key),
        },
        "system_prompt_contract": "strict JSON tool/null action only",
        "skills": skills.names(),
        "tool_schemas": AgentRuntime(None, skills, tools).tool_schemas(),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
