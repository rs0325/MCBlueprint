"""Top-level Blueprint model (see docs/FORMAT.md section 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import reduce
from typing import TYPE_CHECKING, Any

from mcblueprint.model.palette import Palette
from mcblueprint.model.vec import AABB, Vec3

if TYPE_CHECKING:
    from mcblueprint.foundation import FoundationPlan
    from mcblueprint.operations.base import Operation
    from mcblueprint.terrain import TerrainPlacement

FORMAT_VERSION = 1


@dataclass
class Blueprint:
    format_version: int
    minecraft_version: str
    name: str
    operations: list[Operation]
    description: str | None = None
    author: str | None = None
    seed: int = 0
    origin: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    size: Vec3 | None = None
    palettes: dict[str, Palette] = field(default_factory=dict)
    metadata: dict[str, Any] | None = None
    terrain: TerrainPlacement | None = None
    foundation: FoundationPlan | None = None

    def bounds(self) -> AABB:
        """生成せずに出力矩形を返す。地形指定時はairを含む施工矩形。"""
        if self.terrain is not None:
            return self.terrain.region
        return reduce(AABB.union, (op.bounds() for op in self.operations))
