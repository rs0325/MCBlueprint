"""``mirror``: run nested operations and their reflection across a plane."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.vec import AABB, AXES
from mcblueprint.operations.base import ExecutionContext, Operation, Transform, parse_choice
from mcblueprint.operations.nested import NestedOperation
from mcblueprint.operations.registry import register


@register
class MirrorOperation(NestedOperation):
    type = "mirror"

    def __init__(
        self,
        path: str,
        axis: str,
        at: float,
        operations: Sequence[Operation],
        keep_original: bool = True,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, operations, comment)
        self.axis = axis
        self.at = at
        self.keep_original = keep_original
        self.reflection = Transform.mirror(axis, at)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        if "axis" not in data:
            raise BlueprintError(f"{path}: missing required 'axis'")
        axis = parse_choice(data, "axis", path, AXES, "y")
        at = data.get("at")
        if not isinstance(at, int | float) or isinstance(at, bool) or (at * 2) != int(at * 2):
            raise BlueprintError(f"{path}.at: must be an integer or end in .5")
        keep = data.get("keepOriginal", True)
        if not isinstance(keep, bool):
            raise BlueprintError(f"{path}.keepOriginal: must be a boolean")
        return cls(path, axis, at, cls.parse_operations(data, path), keep, data.get("comment"))

    def bounds(self) -> AABB:
        inner = self.inner_bounds()
        mirrored = self.reflection.bounds(inner)
        return inner.union(mirrored) if self.keep_original else mirrored

    def apply(self, ctx: ExecutionContext) -> None:
        if self.keep_original:
            self.apply_with(ctx, Transform.identity())
        self.apply_with(ctx, self.reflection)
