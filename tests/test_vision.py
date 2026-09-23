import json

from projected_ai_interface.vision import HandDetection, Landmark, TemporalSmoother, TouchDetector, VisionConfig, smooth_detection
from projected_ai_interface.vision_cli import main


def detection(x=0.5, y=0.5, z=0.0, confidence=0.95):
    return HandDetection(tuple(Landmark(x, y, z) if i == 8 else Landmark(0.5, 0.5) for i in range(21)), confidence)


def test_smoother_reduces_coordinate_jump():
    smoother = TemporalSmoother(0.5)
    assert smoother.update(0.0, 0.0) == (0.0, 0.0)
    assert smoother.update(1.0, 1.0) == (0.5, 0.5)


def test_low_confidence_is_ignored():
    detector = TouchDetector(VisionConfig(confidence_threshold=0.8))
    assert detector.classify(detection(confidence=0.5).fingertip, 0.5) == "none"


def test_hover_then_stable_depth_touch():
    detector = TouchDetector(VisionConfig(touch_depth_threshold=0.08, touch_velocity_threshold=0.03))
    assert detector.classify(detection(z=0).fingertip, 0.95) == "hover"
    assert detector.classify(detection(x=0.51, z=-0.12).fingertip, 0.95) == "hover"
    assert detector.classify(detection(x=0.51, z=-0.12).fingertip, 0.95) == "touch"


def test_smooth_detection_preserves_confidence_and_landmarks():
    result = smooth_detection(detection(x=0.0), TemporalSmoother(0.5))
    assert result.confidence == 0.95
    assert len(result.landmarks) == 21
    assert result.fingertip.x == 0.0


def test_vision_cli_demo(capsys):
    assert main(["--demo"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output["frames"]) == 3
    assert output["frames"][-1]["state"] == "touch"
