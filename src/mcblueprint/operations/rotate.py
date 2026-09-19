"""``rotate``: run nested operations rotated about a vertical axis (90-degree steps)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import ExecutionContext, Operation, Transform, parse_vec
from mcblueprint.operations.nested import NestedOperation
from mcblueprint.operations.registry import register

ANGLES = (90, 180, 270)


@register
class RotateOperation(NestedOperation):
    type = "rotate"

    def __init__(
        self,
        path: str,
        angle: int,
        center: Vec3,
        operations: Sequence[Operation],
        comment: str | None = None,
    ) -> None:
        super().__init__(path, operations, comment)
        self.angle = angle
        self.center = center
        self.transform = Transform.rotation(angle, center)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        angle = data.get("angle")
        if not isinstance(angle, int) or isinstance(angle, bool) or angle not in ANGLES:
            raise BlueprintError(f"{path}.angle: must be one of 90, 180, 270")
        center = parse_vec(data, "center", path)
        return cls(path, angle, center, cls.parse_operations(data, path), data.get("comment"))

    def bounds(self) -> AABB:
        return self.transform.bounds(self.inner_bounds())

    def apply(self, ctx: ExecutionContext) -> None:
        self.apply_with(ctx, self.transform)
