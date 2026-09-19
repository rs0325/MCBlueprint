"""``arch``: round, pointed or flat arch: a 1-thick ring of blocks around an opening.

The arch is described in a 2D grid ``(u, v)``: ``u`` runs along ``axis`` from the
left edge of the opening, ``v`` upwards from ``position.y``. The opening is a
rectangle (``width`` x ``height``) whose top ``rise + 1`` rows are narrowed to the
arch curve; the ring is every cell touching the opening (4-neighbours) above the
floor. Optional ``trim`` stairs sit in the inner corners of the opening so the
curve reads as rounded.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import BlockSpec, parse_choice, parse_int, parse_vec
from mcblueprint.operations.composite import CompositeOperation, parse_block, spec_json
from mcblueprint.operations.registry import register

STYLES = ("round", "pointed", "flat")
AXES_H = ("x", "z")

Cell = tuple[int, int]


def curve_rows(width: int, style: str) -> list[tuple[int, int]]:
    """``(u_min, u_max)`` of each row of the curved part, bottom (springing row,
    always the full width) first. ``len(rows) - 1`` is the rise of the arch."""
    if style == "flat":
        return [(0, width - 1)]
    rows: list[tuple[int, int]] = []
    k = 0
    while True:
        if style == "round":
            # disc of diameter ``width`` centred on the opening (WorldEdit-style test)
            cells = [
                u for u in range(width) if (2 * u - (width - 1)) ** 2 + (2 * k) ** 2 < width**2
            ]
        else:
            # two arcs of radius ``width`` centred just outside the springers
            limit = (2 * width + 1) ** 2
            cells = [
                u
                for u in range(width)
                if (2 * (u + 1)) ** 2 + (2 * k) ** 2 < limit
                and (2 * (width - u)) ** 2 + (2 * k) ** 2 < limit
            ]
        if not cells:
            return rows
        rows.append((cells[0], cells[-1]))
        k += 1


def arch_rise(width: int, style: str) -> int:
    return len(curve_rows(width, style)) - 1


def opening_cells(width: int, height: int, style: str) -> set[Cell]:
    rows = curve_rows(width, style)
    springing = height - len(rows)
    if springing < 0:
        raise BlueprintError(
            f"height must be at least {len(rows)} for a {style} arch of width {width}"
        )
    cells = {(u, v) for v in range(springing) for u in range(width)}
    for k, (a, b) in enumerate(rows):
        cells.update((u, springing + k) for u in range(a, b + 1))
    return cells


def ring_cells(opening: set[Cell]) -> set[Cell]:
    """Cells touching the opening (4-neighbours) that are not below the floor."""
    ring: set[Cell] = set()
    for u, v in opening:
        for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cell = (u + du, v + dv)
            if cell not in opening and cell[1] >= 0:
                ring.add(cell)
    return ring


def trim_cells(opening: set[Cell], ring: set[Cell]) -> list[tuple[Cell, int]]:
    """Inner corners of the opening: cells with the ring above and on exactly one
    side. The int is ``-1`` when the ring is on the ``u - 1`` side, ``+1`` otherwise."""
    trims = []
    for u, v in sorted(opening, key=lambda c: (c[1], c[0])):
        if (u, v + 1) not in ring:
            continue
        left, right = (u - 1, v) in ring, (u + 1, v) in ring
        if left != right:
            trims.append(((u, v), -1 if left else 1))
    return trims


def runs(cells: Iterable[Cell]) -> list[tuple[int, int, int]]:
    """``(v, u_min, u_max)`` of maximal horizontal runs, bottom row first."""
    ordered = sorted(cells, key=lambda c: (c[1], c[0]))
    result: list[tuple[int, int, int]] = []
    for u, v in ordered:
        if result and result[-1][0] == v and result[-1][2] == u - 1:
            result[-1] = (v, result[-1][1], u)
        else:
            result.append((v, u, u))
    return result


@register
class ArchOperation(CompositeOperation):
    type = "arch"

    def __init__(
        self,
        path: str,
        position: Vec3,
        axis: str,
        width: int,
        height: int,
        spec: BlockSpec,
        style: str = "round",
        depth: int = 1,
        trim: BlockState | None = None,
        fill: BlockState | None = None,
        hollow: bool = True,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        self.position = position
        self.axis = axis
        self.width = width
        self.height = height
        self.spec = spec
        self.style = style
        self.depth = depth
        self.trim = trim
        self.hollow = hollow
        self.fill = fill if fill is not None else (BlockState.of("air") if hollow else None)
        try:
            self.opening = opening_cells(width, height, style)
        except BlueprintError as exc:
            raise BlueprintError(f"{path}: {exc}") from None
        self.ring = ring_cells(self.opening)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        hollow = data.get("hollow", True)
        if not isinstance(hollow, bool):
            raise BlueprintError(f"{path}.hollow: must be a boolean")
        return cls(
            path,
            parse_vec(data, "position", path),
            parse_choice(data, "axis", path, AXES_H, "x"),
            parse_int(data, "width", path, minimum=1),
            parse_int(data, "height", path, minimum=1),
            BlockSpec.from_dict(data, path),
            parse_choice(data, "style", path, STYLES, "round"),
            parse_int(data, "depth", path, minimum=1, default=1),
            parse_block(data, "trim", path),
            parse_block(data, "fill", path),
            hollow,
            data.get("comment"),
        )

    # --- geometry -------------------------------------------------------------

    def _to_world(self, u: int, v: int, d: int) -> Vec3:
        local = Vec3(u, v, d) if self.axis == "x" else Vec3(d, v, u)
        return self.position + local

    def _fill_op(self, v: int, u_min: int, u_max: int, block: dict[str, str]) -> dict[str, Any]:
        a, b = self._to_world(u_min, v, 0), self._to_world(u_max, v, self.depth - 1)
        if a == b:
            return {"type": "set", "position": a.to_list(), **block}
        return {"type": "fill", "from": a.to_list(), "to": b.to_list(), **block}

    def _trim_state(self, side: int) -> BlockState:
        assert self.trim is not None
        state = self.trim
        if state.id.endswith("_stairs"):
            if self.axis == "x":
                facing = "west" if side < 0 else "east"
            else:
                facing = "north" if side < 0 else "south"
            if state.get("facing") is None:
                state = state.with_property("facing", facing)
            if state.get("half") is None:
                state = state.with_property("half", "top")
        elif state.id.endswith("_slab") and state.get("type") is None:
            state = state.with_property("type", "top")
        return state

    def expand(self) -> list[dict[str, Any]]:
        ops = [self._fill_op(v, a, b, spec_json(self.spec)) for v, a, b in runs(self.ring)]
        if self.fill is not None:
            block = {"block": self.fill.to_string()}
            ops.extend(self._fill_op(v, a, b, block) for v, a, b in runs(self.opening))
        if self.trim is not None:
            for (u, v), side in trim_cells(self.opening, self.ring):
                ops.append(self._fill_op(v, u, u, {"block": self._trim_state(side).to_string()}))
        return ops


def parse_arch_spec(
    data: Mapping[str, Any], path: str
) -> tuple[str, BlockSpec, BlockState | None] | None:
    """``arch`` object of ``doorway`` / ``window``: ``{style, block, trim}``."""
    value = data.get("arch")
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise BlueprintError(f"{path}.arch: must be an object with 'style' and 'block'")
    sub = f"{path}.arch"
    return (
        parse_choice(value, "style", sub, STYLES, "round"),
        BlockSpec.from_dict(value, sub),
        parse_block(value, "trim", sub),
    )
