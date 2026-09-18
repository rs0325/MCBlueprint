"""``wall``: straight wall or rectangular perimeter wall extruded upwards."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import BlockSpec, parse_int
from mcblueprint.operations.box_like import CornerOperation, iter_box
from mcblueprint.operations.registry import register


@register
class WallOperation(CornerOperation):
    type = "wall"

    def __init__(
        self,
        path: str,
        start: Vec3,
        end: Vec3,
        height: int,
        spec: BlockSpec,
        thickness: int = 1,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, start, end, spec, comment)
        self.height = height
        self.thickness = thickness
        self.footprint = self._footprint()
        self.box = AABB(self.footprint.min, self.footprint.max.with_axis("y", start.y + height - 1))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        start, end = cls.parse_corners(data, path)
        cls.require_same_y(start, end, path)
        height = parse_int(data, "height", path, minimum=1)
        thickness = parse_int(data, "thickness", path, minimum=1, default=1)
        return cls(
            path,
            start,
            end,
            height,
            BlockSpec.from_dict(data, path),
            thickness,
            data.get("comment"),
        )

    @property
    def is_straight(self) -> bool:
        return self.start.x == self.end.x or self.start.z == self.end.z

    def _footprint(self) -> AABB:
        """Bottom layer including thickness (see docs/OPERATIONS.md, wall)."""
        base = AABB.of(self.start, self.end)
        extra = self.thickness - 1
        if not self.is_straight:
            return base
        if self.start.z == self.end.z:
            # X-aligned line (or single column): thicken towards +Z
            return AABB(base.min, base.max.with_axis("z", base.max.z + extra))
        # Z-aligned line: thicken towards +X
        return AABB(base.min, base.max.with_axis("x", base.max.x + extra))

    def _base_cells(self) -> Iterable[Vec3]:
        if self.is_straight:
            yield from iter_box(self.footprint)
            return
        lo, hi = self.footprint.min, self.footprint.max
        ring = self.thickness
        for p in iter_box(self.footprint):
            if p.x - lo.x < ring or hi.x - p.x < ring or p.z - lo.z < ring or hi.z - p.z < ring:
                yield p

    def cells(self) -> Iterable[Vec3]:
        base = list(self._base_cells())
        for dy in range(self.height):
            for p in base:
                yield Vec3(p.x, p.y + dy, p.z)
