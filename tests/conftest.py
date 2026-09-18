"""Shared test helpers: a minimal test-only operation registered as ``test_point``."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import BlockSpec, PlacementOperation, parse_vec
from mcblueprint.operations.registry import register


@register
class TestPointOperation(PlacementOperation):
    """Places a single cell; exists so tests do not depend on real operations."""

    __test__ = False  # not a pytest test class
    type = "test_point"

    def __init__(self, path: str, position: Vec3, spec: BlockSpec) -> None:
        super().__init__(path, spec)
        self.position = position

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        return cls(path, parse_vec(data, "position", path), BlockSpec.from_dict(data, path))

    def bounds(self) -> AABB:
        return AABB(self.position, self.position)

    def cells(self) -> Iterable[Vec3]:
        yield self.position
