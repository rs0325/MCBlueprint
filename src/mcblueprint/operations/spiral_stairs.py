"""``spiral_stairs``: staircase winding around a vertical axis, one block up per step."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import BlockSpec, parse_choice, parse_int, parse_vec
from mcblueprint.operations.composite import (
    CompositeOperation,
    is_stairs,
    oriented,
    parse_block,
    spec_json,
)
from mcblueprint.operations.registry import register
from mcblueprint.operations.shapes import disc_cells

DEFAULT_HEADROOM = 3
TURNS = ("clockwise", "counterclockwise")


def ring_path(radius: int, clockwise: bool) -> list[tuple[int, int]]:
    """Cells of the radius-``radius`` ring ordered by angle, starting east (+x).

    Clockwise (seen from above) goes east -> south -> west -> north.
    """
    cells = sorted(
        disc_cells(radius, "hollow"), key=lambda c: math.atan2(c[1], c[0]) % (2 * math.pi)
    )
    if not clockwise:
        cells = [cells[0]] + cells[:0:-1]
    return cells


def facing_for(offset: tuple[int, int], next_offset: tuple[int, int]) -> str:
    """Horizontal direction of travel from one ring cell to the next (major axis)."""
    dx, dz = next_offset[0] - offset[0], next_offset[1] - offset[1]
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


@register
class SpiralStairsOperation(CompositeOperation):
    type = "spiral_stairs"

    def __init__(
        self,
        path: str,
        center: Vec3,
        radius: int,
        height: int,
        spec: BlockSpec,
        turn: str = "clockwise",
        headroom: int = DEFAULT_HEADROOM,
        column: BlockState | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        self.center = center
        self.radius = radius
        self.height = height
        self.spec = spec
        self.turn = turn
        self.headroom = headroom
        self.column = column

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        radius = parse_int(data, "radius", path, minimum=1)
        if radius > 8:
            raise BlueprintError(f"{path}.radius: must be <= 8")
        return cls(
            path,
            parse_vec(data, "center", path),
            radius,
            parse_int(data, "height", path, minimum=1),
            BlockSpec.from_dict(data, path),
            parse_choice(data, "turn", path, TURNS, "clockwise"),
            parse_int(data, "headroom", path, minimum=2, default=DEFAULT_HEADROOM),
            parse_block(data, "column", path),
            data.get("comment"),
        )

    def expand(self) -> list[dict[str, Any]]:
        ring = ring_path(self.radius, self.turn == "clockwise")
        stairs = is_stairs(self.spec)
        ops: list[dict[str, Any]] = []
        if self.column is not None:
            ops.append(
                {
                    "type": "fill",
                    "from": self.center.to_list(),
                    "to": (self.center + Vec3(0, self.height - 1, 0)).to_list(),
                    "block": self.column.to_string(),
                }
            )
        for i in range(self.height):
            offset = ring[i % len(ring)]
            following = ring[(i + 1) % len(ring)]
            outer = self.center + Vec3(offset[0], i, offset[1])
            # a two-cell-wide tread: the ring cell plus the cell one step towards the axis
            inner = self.center + Vec3(
                round(offset[0] * (self.radius - 1) / self.radius),
                i,
                round(offset[1] * (self.radius - 1) / self.radius),
            )
            cells = [outer] if self.radius == 1 or inner == self.center else [outer, inner]
            block = (
                oriented(self.spec, facing=facing_for(offset, following), half="bottom")
                if stairs
                else spec_json(self.spec)
            )
            for cell in cells:
                ops.append({"type": "set", "position": cell.to_list(), **block})
                ops.append(
                    {
                        "type": "fill",
                        "from": (cell + Vec3(0, 1, 0)).to_list(),
                        "to": (cell + Vec3(0, self.headroom, 0)).to_list(),
                        "block": "minecraft:air",
                    }
                )
        return ops
