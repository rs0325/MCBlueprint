"""``floor``: one-block-high horizontal layer."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import BlockSpec
from mcblueprint.operations.box_like import CornerOperation, iter_box
from mcblueprint.operations.registry import register


@register
class FloorOperation(CornerOperation):
    type = "floor"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        start, end = cls.parse_corners(data, path)
        cls.require_same_y(start, end, path)
        return cls(path, start, end, BlockSpec.from_dict(data, path), data.get("comment"))

    def cells(self) -> Iterable[Vec3]:
        return iter_box(self.box)
