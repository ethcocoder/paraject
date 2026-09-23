from __future__ import annotations
import argparse
import json
from pathlib import Path
from .skills import SkillRegistry

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='List documented Projected AI skills')
    parser.add_argument('--root', default='skills')
    args = parser.parse_args(argv)
    registry = SkillRegistry()
    count = registry.load_directory(Path(args.root))
    print(json.dumps({'loaded': count, 'skills': registry.names()}, indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
