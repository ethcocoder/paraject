import json

import pytest

from projected_ai_interface.cli import main
from projected_ai_interface.display import DisplayInfo, logical_grid
from projected_ai_interface.projector import FolderTarget, ProjectorUI


def test_grid_has_expected_boundaries():
    grid = logical_grid(1200, 900, columns=4, rows=3)
    assert grid["vertical"] == [0, 300, 600, 900, 1200]
    assert grid["horizontal"] == [0, 300, 600, 900]


def test_invalid_grid_dimensions_are_rejected():
    with pytest.raises(ValueError):
        logical_grid(0, 720)


def test_folder_hit_testing_and_boundaries():
    target = FolderTarget("documents", "Documents", 100, 200, 180, 130)
    assert target.contains(100, 200)
    assert target.contains(280, 330)
    assert not target.contains(281, 330)


def test_projector_ui_dry_run_contains_grid_and_folders():
    ui = ProjectorUI(DisplayInfo(1, 100, 50, 1280, 720, "projector"))
    model = ui.dry_run()
    assert model["display"]["name"] == "projector"
    assert model["grid"]["columns"] == 4
    assert {folder["id"] for folder in model["folders"]} == {"documents", "projects", "downloads"}


def test_hit_test_selects_folder():
    ui = ProjectorUI(DisplayInfo(0, 0, 0, 1280, 720))
    assert ui.hit_test(110, 100).id == "documents"
    assert ui.hit_test(0, 0) is None


def test_cli_dry_run(capsys):
    assert main(["--dry-run", "--width", "800", "--height", "600"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["display"]["width"] == 800
    assert output["display"]["height"] == 600
