"""``box``: cuboid, hollow (six one-block faces) by default."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import BlockSpec, parse_choice
from mcblueprint.operations.box_like import CornerOperation, iter_box
from mcblueprint.operations.registry import register

MODES = ("hollow", "solid")


@register
class BoxOperation(CornerOperation):
    type = "box"

    def __init__(
        self,
        path: str,
        start: Vec3,
        end: Vec3,
        spec: BlockSpec,
        mode: str = "hollow",
        comment: str | None = None,
    ) -> None:
        super().__init__(path, start, end, spec, comment)
        self.mode = mode

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        start, end = cls.parse_corners(data, path)
        mode = parse_choice(data, "mode", path, MODES, "hollow")
        return cls(path, start, end, BlockSpec.from_dict(data, path), mode, data.get("comment"))

    def cells(self) -> Iterable[Vec3]:
        if self.mode == "solid":
            yield from iter_box(self.box)
            return
        lo, hi = self.box.min, self.box.max
        for p in iter_box(self.box):
            if p.x in (lo.x, hi.x) or p.y in (lo.y, hi.y) or p.z in (lo.z, hi.z):
                yield p
