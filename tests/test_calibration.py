import json

import pytest

from projected_ai_interface.calibration import CalibrationError, CalibrationProfile, calculate_homography, transform_point
from projected_ai_interface.calibration_cli import main


def test_identity_mapping():
    points = [(0, 0), (1, 0), (1, 1), (0, 1)]
    homography = calculate_homography(points, points)
    assert transform_point((0.25, 0.75), homography) == pytest.approx((0.25, 0.75))


def test_scaled_projector_mapping():
    profile = CalibrationProfile.from_points((1000, 1000), (1920, 1080), [(0, 0), (1000, 0), (1000, 1000), (0, 1000)], [(0, 0), (1920, 0), (1920, 1080), (0, 1080)])
    assert profile.map_point((500, 500)) == pytest.approx((960, 540))


def test_profile_round_trip(tmp_path):
    profile = CalibrationProfile.from_points((100, 100), (200, 200), [(0, 0), (100, 0), (100, 100), (0, 100)], [(0, 0), (200, 0), (200, 200), (0, 200)])
    path = tmp_path / 'calibration.json'
    profile.save(path)
    loaded = CalibrationProfile.load(path)
    assert loaded.projector_size == (200, 200)
    assert loaded.map_point((25, 25)) == pytest.approx((50, 50))


def test_rejects_wrong_point_count():
    with pytest.raises(CalibrationError):
        calculate_homography([(0, 0)], [(0, 0)])


def test_calibration_cli_demo(tmp_path, capsys):
    assert main(['--demo', '--profile', str(tmp_path / 'demo.json')]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['mapped_center'] == pytest.approx([960, 540])
