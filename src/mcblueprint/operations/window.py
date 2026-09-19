"""``window``: opening filled with glass panes (connections set automatically)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import parse_choice, parse_int, parse_vec
from mcblueprint.operations.composite import CompositeOperation, parse_block
from mcblueprint.operations.registry import register

AXES_H = ("x", "z")
CONNECTING_SUFFIXES = ("_pane", "_bars", "_fence", "_wall")


@register
class WindowOperation(CompositeOperation):
    type = "window"

    def __init__(
        self,
        path: str,
        position: Vec3,
        axis: str,
        width: int = 1,
        height: int = 1,
        block: BlockState | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        self.position = position
        self.axis = axis
        self.width = width
        self.height = height
        self.block = block or BlockState.of("glass_pane")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        return cls(
            path,
            parse_vec(data, "position", path),
            parse_choice(data, "axis", path, AXES_H, "x"),
            parse_int(data, "width", path, minimum=1, default=1),
            parse_int(data, "height", path, minimum=1, default=1),
            parse_block(data, "block", path),
            data.get("comment"),
        )

    def expand(self) -> list[dict[str, Any]]:
        state = self.block
        if state.id.endswith(CONNECTING_SUFFIXES):
            sides = ("east", "west") if self.axis == "x" else ("north", "south")
            for side in sides:
                if state.get(side) is None:
                    state = state.with_property(side, "true")
        along = Vec3(1, 0, 0) if self.axis == "x" else Vec3(0, 0, 1)
        far = self.position + along * (self.width - 1) + Vec3(0, self.height - 1, 0)
        return [
            {
                "type": "fill",
                "from": self.position.to_list(),
                "to": far.to_list(),
                "block": state.to_string(),
            }
        ]
