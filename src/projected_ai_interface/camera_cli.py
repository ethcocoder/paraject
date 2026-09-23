"""Camera capture diagnostics."""
from __future__ import annotations

import argparse
import json

from .camera import NetworkCameraSource, SyntheticCameraSource, WebcamSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Test a camera source and print capture metrics")
    parser.add_argument("--synthetic", action="store_true", help="use deterministic frames instead of a webcam")
    parser.add_argument("--network", action="store_true", help="receive binary JPEG frames from the mobile WebSocket client")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", default="/frames")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args(argv)
    if args.synthetic and args.network:
        parser.error("--synthetic and --network are mutually exclusive")
    if args.network:
        source = NetworkCameraSource(args.host, args.port, path=args.path)
    else:
        source = SyntheticCameraSource(args.frames, args.width, args.height) if args.synthetic else WebcamSource(args.device, args.width, args.height)
    source.open()
    try:
        for _ in source.frames(max_frames=args.frames):
            pass
        print(json.dumps(source.metrics.snapshot(), indent=2))
    finally:
        source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
