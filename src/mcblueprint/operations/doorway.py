"""``doorway``: opening in a wall, optionally fitted with a (double) door."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import parse_int, parse_vec
from mcblueprint.operations.composite import (
    CompositeOperation,
    direction_vec,
    parse_block,
    parse_direction,
    right_of,
)
from mcblueprint.operations.registry import register


@register
class DoorwayOperation(CompositeOperation):
    type = "doorway"

    def __init__(
        self,
        path: str,
        position: Vec3,
        facing: str,
        width: int = 1,
        height: int = 2,
        door: BlockState | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        self.position = position
        self.facing = facing
        self.width = width
        self.height = height
        self.door = door
        if door is not None and not door.id.endswith("_door"):
            raise BlueprintError(f"{path}.door: must be a door block (e.g. oak_door)")
        if door is not None and width > 2:
            raise BlueprintError(f"{path}: a door needs width 1 or 2")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        return cls(
            path,
            parse_vec(data, "position", path),
            parse_direction(data, "facing", path),
            parse_int(data, "width", path, minimum=1, default=1),
            parse_int(data, "height", path, minimum=2, default=2),
            parse_block(data, "door", path),
            data.get("comment"),
        )

    def expand(self) -> list[dict[str, Any]]:
        # the opening extends along the wall towards +x / +z from ``position``
        along = direction_vec(right_of(self.facing))
        if along.x < 0 or along.z < 0:
            along = -along
        far = self.position + along * (self.width - 1) + Vec3(0, self.height - 1, 0)
        ops: list[dict[str, Any]] = [
            {
                "type": "fill",
                "from": self.position.to_list(),
                "to": far.to_list(),
                "block": "minecraft:air",
            }
        ]
        if self.door is None:
            return ops
        right = direction_vec(right_of(self.facing))
        for i in range(self.width):
            cell = self.position + along * i
            if self.width == 1:
                hinge = self.door.get("hinge") or "left"
            else:
                # double doors: hinges on the outer sides so both leaves swing apart
                other = self.position + along * (1 - i)
                hinge = "right" if (cell - other) == right else "left"
            for half, dy in (("lower", 0), ("upper", 1)):
                state = (
                    self.door.with_property("facing", self.facing)
                    .with_property("half", half)
                    .with_property("hinge", hinge)
                )
                ops.append(
                    {
                        "type": "set",
                        "position": (cell + Vec3(0, dy, 0)).to_list(),
                        "block": state.to_string(),
                    }
                )
        return ops
