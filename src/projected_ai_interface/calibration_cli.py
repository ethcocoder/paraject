from __future__ import annotations
import argparse
import json
from .calibration import CalibrationProfile

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Calculate a four-point camera-to-projector calibration')
    parser.add_argument('--demo', action='store_true', help='run a deterministic calibration example')
    parser.add_argument('--profile', default='.calibration/demo.json')
    args = parser.parse_args(argv)
    if not args.demo:
        parser.error('use --demo for the headless calibration check')
    profile = CalibrationProfile.from_points((1000, 1000), (1920, 1080), [(0, 0), (1000, 0), (1000, 1000), (0, 1000)], [(0, 0), (1920, 0), (1920, 1080), (0, 1080)])
    profile.save(args.profile)
    print(json.dumps({'profile': args.profile, 'mapped_center': profile.map_point((500, 500)), 'homography': profile.homography}, indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
