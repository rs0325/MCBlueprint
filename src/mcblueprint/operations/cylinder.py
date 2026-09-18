"""``cylinder``: ``height`` stacked circles along ``axis`` (hollow = side wall only)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import AABB, AXES, Vec3
from mcblueprint.operations.base import BlockSpec, parse_choice, parse_int
from mcblueprint.operations.registry import register
from mcblueprint.operations.shapes import RadialOperation, disc_offsets


@register
class CylinderOperation(RadialOperation):
    type = "cylinder"

    def __init__(
        self,
        path: str,
        center: Vec3,
        radius: int,
        height: int,
        mode: str,
        spec: BlockSpec,
        axis: str = "y",
        comment: str | None = None,
    ) -> None:
        super().__init__(path, center, radius, mode, spec, comment)
        self.height = height
        self.axis = axis

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        center, radius, mode, spec = cls.parse_common(data, path)
        height = parse_int(data, "height", path, minimum=1)
        axis = parse_choice(data, "axis", path, AXES, "y")
        return cls(path, center, radius, height, mode, spec, axis, data.get("comment"))

    def bounds(self) -> AABB:
        base = self.radial_bounds(self.axis)
        top = base.max.with_axis(self.axis, self.center.axis(self.axis) + self.height - 1)
        return AABB(base.min, top)

    def cells(self) -> Iterable[Vec3]:
        disc = list(disc_offsets(self.radius, self.mode, self.axis))
        for level in range(self.height):
            step = Vec3(0, 0, 0).with_axis(self.axis, level)
            for offset in disc:
                yield self.center + offset + step
