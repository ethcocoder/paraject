"""Camera-to-projector calibration using a four-point homography."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

Point = tuple[float, float]


class CalibrationError(ValueError):
    """Raised when calibration points cannot define a stable transform."""


def _solve_linear(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Solve a small linear system with Gaussian elimination and pivoting."""
    n = len(values)
    augmented = [row[:] + [values[i]] for i, row in enumerate(matrix)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            raise CalibrationError("calibration points are degenerate")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [item / divisor for item in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    return [augmented[i][-1] for i in range(n)]


def calculate_homography(camera_points: Iterable[Point], projector_points: Iterable[Point]) -> tuple[float, ...]:
    """Calculate a 3x3 projective transform from four corresponding points."""
    source, target = list(camera_points), list(projector_points)
    if len(source) != 4 or len(target) != 4:
        raise CalibrationError("exactly four camera and four projector points are required")
    matrix: list[list[float]] = []
    values: list[float] = []
    for (x, y), (u, v) in zip(source, target):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        values.append(u)
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        values.append(v)
    result = _solve_linear(matrix, values)
    return tuple(result) + (1.0,)


def transform_point(point: Point, homography: Iterable[float]) -> Point:
    values = tuple(homography)
    if len(values) != 9:
        raise CalibrationError("homography must contain nine values")
    x, y = point
    denominator = values[6] * x + values[7] * y + values[8]
    if abs(denominator) < 1e-10:
        raise CalibrationError("point maps to an invalid projective denominator")
    return ((values[0] * x + values[1] * y + values[2]) / denominator, (values[3] * x + values[4] * y + values[5]) / denominator)


@dataclass
class CalibrationProfile:
    camera_size: tuple[int, int]
    projector_size: tuple[int, int]
    camera_points: tuple[Point, ...]
    projector_points: tuple[Point, ...]
    homography: tuple[float, ...]
    version: int = 1

    @classmethod
    def from_points(cls, camera_size: tuple[int, int], projector_size: tuple[int, int], camera_points: Iterable[Point], projector_points: Iterable[Point]) -> "CalibrationProfile":
        camera, projector = tuple(camera_points), tuple(projector_points)
        return cls(camera_size, projector_size, camera, projector, calculate_homography(camera, projector))

    def map_point(self, point: Point) -> Point:
        return transform_point(point, self.homography)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CalibrationProfile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(tuple(data["camera_size"]), tuple(data["projector_size"]), tuple(tuple(point) for point in data["camera_points"]), tuple(tuple(point) for point in data["projector_points"]), tuple(data["homography"]), int(data.get("version", 1)))
