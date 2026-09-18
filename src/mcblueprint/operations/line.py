"""``line``: cells along the segment between two points (3D DDA)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import BlockSpec
from mcblueprint.operations.box_like import CornerOperation
from mcblueprint.operations.registry import register


def line_cells(start: Vec3, end: Vec3) -> Iterable[Vec3]:
    """Inclusive cells from ``start`` to ``end``; ``round(v) = floor(v + 0.5)``."""
    d = end - start
    n = max(abs(d.x), abs(d.y), abs(d.z))
    if n == 0:
        yield start
        return
    for i in range(n + 1):
        yield Vec3(
            start.x + _round_half_up(d.x * i / n),
            start.y + _round_half_up(d.y * i / n),
            start.z + _round_half_up(d.z * i / n),
        )


def _round_half_up(value: float) -> int:
    return int((value + 0.5) // 1)


@register
class LineOperation(CornerOperation):
    type = "line"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        start, end = cls.parse_corners(data, path)
        return cls(path, start, end, BlockSpec.from_dict(data, path), data.get("comment"))

    def cells(self) -> Iterable[Vec3]:
        return line_cells(self.start, self.end)
