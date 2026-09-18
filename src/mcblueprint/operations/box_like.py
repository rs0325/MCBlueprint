"""Shared base for operations defined by two opposite corners (``from`` / ``to``)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from mcblueprint.errors import BlueprintError
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import BlockSpec, PlacementOperation, parse_vec


class CornerOperation(PlacementOperation):
    """Placement operation spanning the box between ``from`` and ``to`` (any order)."""

    def __init__(
        self, path: str, start: Vec3, end: Vec3, spec: BlockSpec, comment: str | None = None
    ) -> None:
        super().__init__(path, spec, comment)
        self.start = start
        self.end = end
        self.box = AABB.of(start, end)

    @classmethod
    def parse_corners(cls, data: Mapping[str, Any], path: str) -> tuple[Vec3, Vec3]:
        return parse_vec(data, "from", path), parse_vec(data, "to", path)

    @staticmethod
    def require_same_y(start: Vec3, end: Vec3, path: str) -> None:
        if start.y != end.y:
            raise BlueprintError(f"{path}: 'from' and 'to' must have the same y coordinate")

    def bounds(self) -> AABB:
        return self.box


def iter_box(box: AABB) -> Iterator[Vec3]:
    """Every cell of ``box`` in y -> z -> x order (y outermost)."""
    for y in range(box.min.y, box.max.y + 1):
        for z in range(box.min.z, box.max.z + 1):
            for x in range(box.min.x, box.max.x + 1):
                yield Vec3(x, y, z)
