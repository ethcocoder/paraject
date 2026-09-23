"""Command-line entry point for the Phase 1 projector prototype."""
from __future__ import annotations

import argparse
import json

from .display import DisplayInfo, detect_displays
from .projector import ProjectorUI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the projected UI prototype")
    parser.add_argument("--dry-run", action="store_true", help="print the UI model without opening a window")
    parser.add_argument("--display", type=int, default=None, help="display index; defaults to the largest detected display")
    parser.add_argument("--width", type=int, default=1280, help="fallback width when no display is detected")
    parser.add_argument("--height", type=int, default=720, help="fallback height when no display is detected")
    args = parser.parse_args(argv)

    displays = detect_displays()
    if displays:
        if args.display is not None:
            if args.display < 0 or args.display >= len(displays):
                parser.error(f"display must be between 0 and {len(displays) - 1}")
            display = displays[args.display]
        else:
            display = max(displays, key=lambda item: item.width * item.height)
    else:
        display = DisplayInfo(0, 0, 0, args.width, args.height, "fallback")

    ui = ProjectorUI(display)
    if args.dry_run:
        print(json.dumps(ui.dry_run(), indent=2))
    else:
        ui.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
