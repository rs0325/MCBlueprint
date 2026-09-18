"""``circle``: ring or disc in the plane perpendicular to ``axis``."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import AABB, AXES, Vec3
from mcblueprint.operations.base import BlockSpec, parse_choice
from mcblueprint.operations.registry import register
from mcblueprint.operations.shapes import RadialOperation, disc_offsets


@register
class CircleOperation(RadialOperation):
    type = "circle"

    def __init__(
        self,
        path: str,
        center: Vec3,
        radius: int,
        mode: str,
        spec: BlockSpec,
        axis: str = "y",
        comment: str | None = None,
    ) -> None:
        super().__init__(path, center, radius, mode, spec, comment)
        self.axis = axis

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        center, radius, mode, spec = cls.parse_common(data, path)
        axis = parse_choice(data, "axis", path, AXES, "y")
        return cls(path, center, radius, mode, spec, axis, data.get("comment"))

    def bounds(self) -> AABB:
        return self.radial_bounds(self.axis)

    def cells(self) -> Iterable[Vec3]:
        for offset in disc_offsets(self.radius, self.mode, self.axis):
            yield self.center + offset
