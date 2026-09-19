"""``translate``: run nested operations shifted by ``offset``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Self

from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import ExecutionContext, Operation, Transform, parse_vec
from mcblueprint.operations.nested import NestedOperation
from mcblueprint.operations.registry import register


@register
class TranslateOperation(NestedOperation):
    type = "translate"

    def __init__(
        self, path: str, offset: Vec3, operations: Sequence[Operation], comment: str | None = None
    ) -> None:
        super().__init__(path, operations, comment)
        self.offset = offset
        self.transform = Transform.translation(offset)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        offset = parse_vec(data, "offset", path)
        return cls(path, offset, cls.parse_operations(data, path), data.get("comment"))

    def bounds(self) -> AABB:
        return self.transform.bounds(self.inner_bounds())

    def apply(self, ctx: ExecutionContext) -> None:
        self.apply_with(ctx, self.transform)
