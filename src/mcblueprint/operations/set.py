"""``set``: place a single block."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import BlockSpec, PlacementOperation, parse_vec
from mcblueprint.operations.registry import register


@register
class SetOperation(PlacementOperation):
    type = "set"

    def __init__(self, path: str, position: Vec3, spec: BlockSpec, comment: str | None = None):
        super().__init__(path, spec, comment)
        self.position = position

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        return cls(
            path,
            parse_vec(data, "position", path),
            BlockSpec.from_dict(data, path),
            data.get("comment"),
        )

    def bounds(self) -> AABB:
        return AABB(self.position, self.position)

    def cells(self) -> Iterable[Vec3]:
        yield self.position
