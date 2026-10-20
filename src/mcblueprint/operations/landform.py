"""楕円形の丘または矩形の台地を生成する。"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import (
    BlockSpec,
    ExecutionContext,
    Operation,
    parse_choice,
    parse_int,
    parse_vec,
)
from mcblueprint.operations.registry import register
from mcblueprint.operations.room import parse_spec

SHAPES = ("hill", "plateau")


def _axis_distance(value: int, low: int, high: int) -> float:
    span = high - low
    centre_offset = span % 2
    delta = abs(2 * value - low - high) - centre_offset
    return delta / (span - centre_offset)


@register
class LandformOperation(Operation):
    type = "landform"

    def __init__(
        self,
        path: str,
        shape: str,
        start: Vec3,
        end: Vec3,
        height: int,
        surface: BlockSpec,
        subsurface: BlockSpec,
        edge_width: int | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        if start.y != end.y:
            raise BlueprintError(f"{path}: 'from' and 'to' must have the same y coordinate")
        self.box = AABB.of(start, end)
        if self.box.size.x < 3 or self.box.size.z < 3:
            raise BlueprintError(f"{path}: footprint must be at least 3 x 3")
        self.shape = shape
        self.base_y = self.box.min.y
        self.height = height
        self.surface = surface
        self.subsurface = subsurface
        self.edge_width = edge_width
        if shape == "plateau":
            if edge_width is None:
                raise BlueprintError(f"{path}: 'edgeWidth' is required for a plateau")
            if self.box.size.x < edge_width * 2 + 1 or self.box.size.z < edge_width * 2 + 1:
                raise BlueprintError(
                    f"{path}: footprint must be at least {edge_width * 2 + 1} x "
                    f"{edge_width * 2 + 1} for edgeWidth {edge_width}"
                )
        elif edge_width is not None:
            raise BlueprintError(f"{path}: 'edgeWidth' is only valid for a plateau")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        shape = parse_choice(data, "shape", path, SHAPES, "")
        surface = parse_spec(data, "surface", path)
        if surface is None:
            raise BlueprintError(f"{path}: missing required 'surface'")
        subsurface = parse_spec(data, "subsurface", path)
        if subsurface is None:
            raise BlueprintError(f"{path}: missing required 'subsurface'")
        return cls(
            path,
            shape,
            parse_vec(data, "from", path),
            parse_vec(data, "to", path),
            parse_int(data, "height", path, minimum=1),
            surface,
            subsurface,
            parse_int(data, "edgeWidth", path, minimum=1) if "edgeWidth" in data else None,
            data.get("comment"),
        )

    def bounds(self) -> AABB:
        return AABB(
            self.box.min,
            Vec3(self.box.max.x, self.base_y + self.height, self.box.max.z),
        )

    def apply(self, ctx: ExecutionContext) -> None:
        lo, hi = self.box.min, self.box.max
        for z in range(lo.z, hi.z + 1):
            for x in range(lo.x, hi.x + 1):
                rise = self._rise(x, z)
                if rise is None:
                    continue
                top = self.base_y + rise
                for y in range(self.base_y, top):
                    ctx.place(Vec3(x, y, z), self.subsurface)
                ctx.place(Vec3(x, top, z), self.surface)

    def _rise(self, x: int, z: int) -> int | None:
        if self.shape == "plateau":
            assert self.edge_width is not None
            inset = min(
                x - self.box.min.x,
                self.box.max.x - x,
                z - self.box.min.z,
                self.box.max.z - z,
            )
            if inset >= self.edge_width:
                return self.height
            return (2 * self.height * inset + self.edge_width) // (2 * self.edge_width)

        dx = _axis_distance(x, self.box.min.x, self.box.max.x)
        dz = _axis_distance(z, self.box.min.z, self.box.max.z)
        distance = math.sqrt(dx * dx + dz * dz)
        if distance > 1:
            return None
        return math.floor(self.height * (1 - distance) + 0.5)
