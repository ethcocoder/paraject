from __future__ import annotations
import argparse
import json
from .agent import AgentRuntime
from .skills import SkillRegistry, ToolRegistry

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Inspect the Phase 8 agent contract')
    parser.add_argument('--root', default='skills')
    args = parser.parse_args(argv)
    skills = SkillRegistry(); skills.load_directory(args.root)
    tools = ToolRegistry()
    print(json.dumps({'system_prompt_contract': 'JSON tool/null action only', 'skills': skills.names(), 'tool_schemas': AgentRuntime(None, skills, tools).tool_schemas()}, indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
