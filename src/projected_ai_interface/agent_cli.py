from __future__ import annotations

import argparse
import json

from .agent import AgentConfig, AgentRuntime
from .skills import SkillRegistry, ToolRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the Phase 8 agent contract")
    parser.add_argument("--root", default="skills")
    parser.add_argument("--backend", choices=("onnx", "smollm", "onnx-causal", "openai-compatible"), help="inference backend")
    parser.add_argument("--base-url", help="OpenAI-compatible provider base URL")
    parser.add_argument("--model", help="Local model name")
    parser.add_argument("--onnx-model", help="path to a local ONNX action model")
    parser.add_argument("--onnx-tokenizer", help="path to tokenizer.json for a causal ONNX model")
    parser.add_argument("--onnx-max-new-tokens", type=int, help="maximum generated tokens for a causal ONNX model")
    parser.add_argument("--timeout", type=float, help="Provider timeout in seconds")
    parser.add_argument("--retries", type=int, help="Maximum malformed/provider retries")
    args = parser.parse_args(argv)

    defaults = AgentConfig.from_env()
    config = AgentConfig(
        backend=args.backend or defaults.backend,
        base_url=args.base_url or defaults.base_url,
        model=args.model or defaults.model,
        api_key=defaults.api_key,
        timeout_seconds=args.timeout if args.timeout is not None else defaults.timeout_seconds,
        max_retries=args.retries if args.retries is not None else defaults.max_retries,
        onnx_model=args.onnx_model or defaults.onnx_model,
        onnx_tokenizer=args.onnx_tokenizer or defaults.onnx_tokenizer,
        onnx_max_new_tokens=args.onnx_max_new_tokens if args.onnx_max_new_tokens is not None else defaults.onnx_max_new_tokens,
        onnx_labels=defaults.onnx_labels,
    )
    skills = SkillRegistry()
    skills.load_directory(args.root)
    tools = ToolRegistry()
    print(json.dumps({
        "provider": {
            "backend": config.backend,
            "base_url": config.base_url,
            "model": config.model,
            "onnx_model": config.onnx_model,
            "onnx_tokenizer": config.onnx_tokenizer,
            "onnx_max_new_tokens": config.onnx_max_new_tokens,
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
