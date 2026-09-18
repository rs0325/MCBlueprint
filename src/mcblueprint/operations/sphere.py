"""``sphere``: ball or spherical shell."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.registry import register
from mcblueprint.operations.shapes import RadialOperation, sphere_offsets


@register
class SphereOperation(RadialOperation):
    type = "sphere"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        center, radius, mode, spec = cls.parse_common(data, path)
        return cls(path, center, radius, mode, spec, data.get("comment"))

    def bounds(self) -> AABB:
        return self.radial_bounds(None)

    def cells(self) -> Iterable[Vec3]:
        for offset in sphere_offsets(self.radius, self.mode):
            yield self.center + offset
