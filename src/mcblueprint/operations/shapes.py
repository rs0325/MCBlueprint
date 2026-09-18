"""Shared geometry for circle / cylinder / sphere (see docs/OPERATIONS.md)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from mcblueprint.model.vec import AABB, AXES, Vec3
from mcblueprint.operations.base import (
    BlockSpec,
    PlacementOperation,
    parse_choice,
    parse_int,
    parse_vec,
)

MODES = ("hollow", "solid")


def inside(distance_sq: int, radius: int) -> bool:
    """WorldEdit-style test: ``d² < (r + 0.5)²``, evaluated in integers."""
    return 4 * distance_sq < (2 * radius + 1) ** 2


def disc_cells(radius: int, mode: str) -> set[tuple[int, int]]:
    """2D offsets of a disc (``solid``) or its 1-thick boundary ring (``hollow``).

    ``hollow`` keeps the cells of the solid disc that have at least one
    4-neighbour outside the disc (WorldEdit ``//hcyl`` behaviour).
    """
    solid = {
        (u, v)
        for u in range(-radius, radius + 1)
        for v in range(-radius, radius + 1)
        if inside(u * u + v * v, radius)
    }
    if mode == "solid":
        return solid
    return {
        (u, v)
        for (u, v) in solid
        if any((u + du, v + dv) not in solid for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    }


def ball_cells(radius: int, mode: str) -> set[Vec3]:
    """3D offsets of a ball (``solid``) or its 1-thick shell (``hollow``, 6-neighbours)."""
    solid = {
        Vec3(x, y, z)
        for x in range(-radius, radius + 1)
        for y in range(-radius, radius + 1)
        for z in range(-radius, radius + 1)
        if inside(x * x + y * y + z * z, radius)
    }
    if mode == "solid":
        return solid
    steps = (
        Vec3(1, 0, 0),
        Vec3(-1, 0, 0),
        Vec3(0, 1, 0),
        Vec3(0, -1, 0),
        Vec3(0, 0, 1),
        Vec3(0, 0, -1),
    )
    return {p for p in solid if any(p + d not in solid for d in steps)}


def plane_axes(axis: str) -> tuple[str, str]:
    """The two in-plane axes for a circle whose normal is ``axis``.

    Returns (outer, inner) scan order: Y outermost when present, otherwise Z.
    """
    remaining = [a for a in AXES if a != axis]
    if "y" in remaining:
        return "y", "x" if "x" in remaining else "z"
    return "z", "x"


def disc_offsets(radius: int, mode: str, axis: str) -> Iterator[Vec3]:
    """Offsets from the centre for a circle in the plane perpendicular to ``axis``."""
    outer, inner = plane_axes(axis)
    cells = disc_cells(radius, mode)
    for u in range(-radius, radius + 1):
        for v in range(-radius, radius + 1):
            if (u, v) in cells:
                yield Vec3(0, 0, 0).with_axis(outer, u).with_axis(inner, v)


def sphere_offsets(radius: int, mode: str) -> Iterator[Vec3]:
    cells = ball_cells(radius, mode)
    for y in range(-radius, radius + 1):
        for z in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                p = Vec3(x, y, z)
                if p in cells:
                    yield p


class RadialOperation(PlacementOperation):
    """Placement operation with ``center``, ``radius`` and ``mode``."""

    def __init__(
        self,
        path: str,
        center: Vec3,
        radius: int,
        mode: str,
        spec: BlockSpec,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, spec, comment)
        self.center = center
        self.radius = radius
        self.mode = mode

    @classmethod
    def parse_common(cls, data: Mapping[str, Any], path: str) -> tuple[Vec3, int, str, BlockSpec]:
        return (
            parse_vec(data, "center", path),
            parse_int(data, "radius", path, minimum=1),
            parse_choice(data, "mode", path, MODES, "hollow"),
            BlockSpec.from_dict(data, path),
        )

    def radial_bounds(self, axis: str | None) -> AABB:
        """Box of ``center ± radius`` in every axis except ``axis`` (if given)."""
        r = Vec3(self.radius, self.radius, self.radius)
        if axis is not None:
            r = r.with_axis(axis, 0)
        return AABB(self.center - r, self.center + r)
