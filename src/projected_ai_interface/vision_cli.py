from __future__ import annotations
import argparse
import json
from .vision import HandDetection, Landmark, TemporalSmoother, TouchDetector, VisionConfig, smooth_detection

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Exercise the Phase 4 fingertip vision pipeline')
    parser.add_argument('--demo', action='store_true', help='run deterministic synthetic landmarks')
    args = parser.parse_args(argv)
    if not args.demo:
        parser.error('live camera wiring is intentionally separate; use --demo for a headless check')
    config = VisionConfig()
    smoother, touch = TemporalSmoother(config.smoothing_alpha), TouchDetector(config)
    results = []
    for x, y, z in [(0.40, 0.50, 0.0), (0.43, 0.51, -0.12), (0.43, 0.51, -0.12)]:
        landmarks = tuple(Landmark(x, y, z) if index == 8 else Landmark(0.5, 0.5) for index in range(21))
        detection = smooth_detection(HandDetection(landmarks, 0.95), smoother)
        results.append({'x': round(detection.fingertip.x, 3), 'y': round(detection.fingertip.y, 3), 'state': touch.classify(detection.fingertip, detection.confidence)})
    print(json.dumps({'frames': results, 'confidence_threshold': config.confidence_threshold}, indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
