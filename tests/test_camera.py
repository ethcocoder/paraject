import json

from projected_ai_interface.camera import CameraFrame, CameraMetrics, SyntheticCameraSource
from projected_ai_interface.camera_cli import main


def test_synthetic_source_yields_requested_frames_and_metrics():
    source = SyntheticCameraSource(frames=5, width=640, height=480)
    source.open()
    frames = list(source.frames())
    assert len(frames) == 5
    assert frames[-1].sequence == 4
    assert frames[-1].width == 640
    assert source.metrics.frames == 5
    assert source.metrics.dropped_frames == 0
    source.close()


def test_metrics_report_fps_latency_and_drops():
    metrics = CameraMetrics()
    metrics.record(CameraFrame(None, 10.0, 0, 10, 10), received_at=10.01)
    metrics.record(CameraFrame(None, 10.1, 2, 10, 10), received_at=10.12)
    snapshot = metrics.snapshot()
    assert snapshot["frames"] == 2
    assert snapshot["dropped_frames"] == 1
    assert snapshot["fps"] == 10.0
    assert snapshot["average_latency_ms"] == 15.0


def test_camera_cli_synthetic_mode(capsys):
    assert main(["--synthetic", "--frames", "3", "--width", "160", "--height", "120"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["frames"] == 3
    assert output["dropped_frames"] == 0
