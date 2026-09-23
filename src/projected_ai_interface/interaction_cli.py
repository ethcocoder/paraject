from __future__ import annotations
import argparse
import json
from .calibration import CalibrationProfile
from .interaction import InteractionEngine, UIObject

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Exercise projected UI interaction events')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args(argv)
    if not args.demo: parser.error('use --demo for the headless interaction check')
    profile = CalibrationProfile.from_points((100, 100), (100, 100), [(0, 0), (100, 0), (100, 100), (0, 100)], [(0, 0), (100, 0), (100, 100), (0, 100)])
    engine = InteractionEngine(profile, [UIObject('documents', 'folder', 10, 10, 40, 40)], debounce_frames=2)
    events = []
    for frame in [(20, 20, 'touch'), (20, 20, 'touch'), (20, 20, 'none')]: events.extend(engine.process((frame[0], frame[1]), .96, frame[2], timestamp=1.0 + len(events) * .1))
    print(json.dumps({'events': [event.to_dict() for event in events]}, indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
