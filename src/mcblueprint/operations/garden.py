"""``garden``: a farm (farmland, crops and irrigation channels) or a flower bed
(ground with plants from a palette), optionally fenced with a gate and lanterns.

``from`` / ``to`` span the ground layer. With a ``fence`` the outermost ring of the
rectangle carries the fence (on the ground block) and the interior is planted;
without one the whole rectangle is planted. Expands into ``fill`` / ``floor`` /
``set``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import BlockSpec, parse_choice, parse_int, parse_vec
from mcblueprint.operations.composite import (
    CompositeOperation,
    parse_block,
    parse_direction,
    spec_json,
)
from mcblueprint.operations.registry import register
from mcblueprint.operations.room import parse_spec
from mcblueprint.operations.tower import _sub

STYLES = ("farm", "flowers")
AXES_H = ("x", "z")
DEFAULT_CROP = "minecraft:wheat[age=7]"
DEFAULT_GROUND = "minecraft:grass_block"
DEFAULT_WATER_SPACING = 4
DEFAULT_GATE = "minecraft:oak_fence_gate"
DEFAULT_LANTERN = "minecraft:lantern"
FARMLAND = "minecraft:farmland[moisture=7]"
WATER = "minecraft:water"
SIDE_PROPERTY = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def channel_indices(count: int, spacing: int) -> list[int]:
    """Row indices (0-based across ``count`` rows) that become water channels so that
    every other row is within ``spacing`` rows of one: every ``spacing + 1``-th row
    starting at ``spacing``; a strip too short for that gets its last row."""
    if spacing <= 0 or count < 2:
        return []
    channels = list(range(spacing, count, spacing + 1))
    return channels or [count - 1]


def connected_state(state: BlockState, joined: dict[str, bool]) -> BlockState:
    """Fence / wall / pane state with the given side connections (explicit values win)."""
    name = state.id
    if name.endswith(("_fence", "_pane", "_bars")):
        for side, on in joined.items():
            if state.get(side) is None:
                state = state.with_property(side, "true" if on else "false")
    elif name.endswith("_wall"):
        for side, on in joined.items():
            if state.get(side) is None:
                state = state.with_property(side, "low" if on else "none")
        if state.get("up") is None:
            straight = (
                joined["north"] and joined["south"] and not joined["east"] and not joined["west"]
            ) or (joined["east"] and joined["west"] and not joined["north"] and not joined["south"])
            state = state.with_property("up", "false" if straight else "true")
    return state


@register
class GardenOperation(CompositeOperation):
    type = "garden"

    def __init__(
        self,
        path: str,
        start: Vec3,
        end: Vec3,
        style: str = "farm",
        crop: BlockState | None = None,
        water: int = DEFAULT_WATER_SPACING,
        rows: str | None = None,
        ground: BlockSpec | None = None,
        plants: BlockSpec | None = None,
        fence: BlockState | None = None,
        gate: Mapping[str, Any] | None = None,
        lanterns: Mapping[str, Any] | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        if start.y != end.y:
            raise BlueprintError(f"{path}: 'from' and 'to' must have the same y coordinate")
        self.box = AABB.of(start, end)
        self.style = style
        self.crop = crop or BlockState.parse(DEFAULT_CROP)
        self.water = water
        self.ground = ground or BlockSpec(block=BlockState.parse(DEFAULT_GROUND))
        self.plants = plants
        self.fence = fence
        size = self.box.size
        self.rows = rows or ("x" if size.x >= size.z else "z")
        inner = self.box
        if fence is not None:
            if size.x < 3 or size.z < 3:
                raise BlueprintError(f"{path}: a fenced garden must be at least 3 x 3")
            inner = AABB(self.box.min + Vec3(1, 0, 1), self.box.max - Vec3(1, 0, 1))
        self.inner = inner
        if style == "flowers" and plants is None:
            raise BlueprintError(f"{path}: 'plants' (a block or a palette) is required for flowers")
        self._parse_gate(gate, path)
        self._parse_lanterns(lanterns, path)

    def _parse_gate(self, data: Mapping[str, Any] | None, path: str) -> None:
        self.gate = data
        if data is None:
            return
        sub = f"{path}.gate"
        if self.fence is None:
            raise BlueprintError(f"{sub}: a gate needs a 'fence'")
        self.gate_side = parse_direction(data, "side", sub, "south")
        self.gate_offset = parse_int(data, "offset", sub, minimum=1) if "offset" in data else None
        self.gate_block = parse_block(data, "block", sub) or BlockState.of(DEFAULT_GATE)
        along = self.box.size.x if self.gate_side in ("north", "south") else self.box.size.z
        if self.gate_offset is not None and self.gate_offset > along - 2:
            raise BlueprintError(
                f"{sub}.offset: must be between 1 and {along - 2} (inside the corners)"
            )

    def _parse_lanterns(self, data: Mapping[str, Any] | None, path: str) -> None:
        self.lanterns = data
        if data is None:
            return
        sub = f"{path}.lanterns"
        if self.fence is None:
            raise BlueprintError(f"{sub}: lanterns need a 'fence' to stand on")
        self.lantern_spacing = parse_int(data, "spacing", sub, minimum=1, default=4)
        self.lantern_block = parse_block(data, "block", sub) or BlockState.of(DEFAULT_LANTERN)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        return cls(
            path,
            parse_vec(data, "from", path),
            parse_vec(data, "to", path),
            parse_choice(data, "style", path, STYLES, "farm"),
            parse_block(data, "crop", path),
            parse_int(data, "water", path, minimum=0, default=DEFAULT_WATER_SPACING),
            parse_choice(data, "rows", path, AXES_H, "x") if "rows" in data else None,
            parse_spec(data, "ground", path),
            parse_spec(data, "plants", path),
            parse_block(data, "fence", path),
            _sub(data, "gate", path),
            _sub(data, "lanterns", path),
            data.get("comment"),
        )

    # --- layout ---------------------------------------------------------------

    def ring_cells(self) -> list[tuple[int, int]]:
        """(x, z) of the fence ring, clockwise from the north-west corner."""
        lo, hi = self.box.min, self.box.max
        cells = [(x, lo.z) for x in range(lo.x, hi.x + 1)]
        cells += [(hi.x, z) for z in range(lo.z + 1, hi.z + 1)]
        cells += [(x, hi.z) for x in range(hi.x - 1, lo.x - 1, -1)]
        cells += [(lo.x, z) for z in range(hi.z - 1, lo.z, -1)]
        return cells

    def gate_cell(self) -> tuple[int, int]:
        lo, hi = self.box.min, self.box.max
        if self.gate_side in ("north", "south"):
            x = lo.x + (self.gate_offset if self.gate_offset is not None else (hi.x - lo.x) // 2)
            return x, (lo.z if self.gate_side == "north" else hi.z)
        z = lo.z + (self.gate_offset if self.gate_offset is not None else (hi.z - lo.z) // 2)
        return (lo.x if self.gate_side == "west" else hi.x), z

    def channel_lines(self) -> list[int]:
        """Coordinates (z for rows along x, x for rows along z) of the water channels."""
        lo, hi = self.inner.min, self.inner.max
        if self.rows == "x":
            return [lo.z + i for i in channel_indices(hi.z - lo.z + 1, self.water)]
        return [lo.x + i for i in channel_indices(hi.x - lo.x + 1, self.water)]

    def expand(self) -> list[dict[str, Any]]:
        lo, hi = self.box.min, self.box.max
        y = lo.y
        inner = self.inner
        ops: list[dict[str, Any]] = [
            {
                "type": "floor",
                "from": [lo.x, y, lo.z],
                "to": [hi.x, y, hi.z],
                **spec_json(self.ground),
            },
            {
                "type": "fill",
                "from": [lo.x, y + 1, lo.z],
                "to": [hi.x, y + 2, hi.z],
                "block": "minecraft:air",
            },
        ]
        if self.style == "farm":
            ops.append(
                {
                    "type": "floor",
                    "from": inner.min.to_list(),
                    "to": inner.max.to_list(),
                    "block": FARMLAND,
                }
            )
            channels = self.channel_lines()
            for line in channels:
                a = Vec3(inner.min.x, y, line) if self.rows == "x" else Vec3(line, y, inner.min.z)
                b = Vec3(inner.max.x, y, line) if self.rows == "x" else Vec3(line, y, inner.max.z)
                ops.append({"type": "fill", "from": a.to_list(), "to": b.to_list(), "block": WATER})
            crop = {"block": self.crop.to_string()}
            ops.append(
                {
                    "type": "floor",
                    "from": [inner.min.x, y + 1, inner.min.z],
                    "to": [inner.max.x, y + 1, inner.max.z],
                    **crop,
                }
            )
            for line in channels:  # nothing grows over the water
                a = (
                    Vec3(inner.min.x, y + 1, line)
                    if self.rows == "x"
                    else Vec3(line, y + 1, inner.min.z)
                )
                b = (
                    Vec3(inner.max.x, y + 1, line)
                    if self.rows == "x"
                    else Vec3(line, y + 1, inner.max.z)
                )
                ops.append(
                    {
                        "type": "fill",
                        "from": a.to_list(),
                        "to": b.to_list(),
                        "block": "minecraft:air",
                    }
                )
        else:
            assert self.plants is not None
            ops.append(
                {
                    "type": "floor",
                    "from": [inner.min.x, y + 1, inner.min.z],
                    "to": [inner.max.x, y + 1, inner.max.z],
                    **spec_json(self.plants),
                }
            )
        if self.fence is not None:
            ops.extend(self._fence_ops())
        return ops

    def _fence_ops(self) -> list[dict[str, Any]]:
        assert self.fence is not None
        y = self.box.min.y + 1
        ring = self.ring_cells()
        ring_set = set(ring)
        gate = self.gate_cell() if self.gate is not None else None
        ops: list[dict[str, Any]] = []
        for x, z in ring:
            if (x, z) == gate:
                facing = "north" if self.gate_side in ("north", "south") else "east"
                state = self.gate_block
                if state.get("facing") is None:
                    state = state.with_property("facing", facing)
                ops.append({"type": "set", "position": [x, y, z], "block": state.to_string()})
                continue
            joined = {
                side: (x + dx, z + dz) in ring_set for side, (dx, dz) in SIDE_PROPERTY.items()
            }
            state = connected_state(self.fence, joined)
            ops.append({"type": "set", "position": [x, y, z], "block": state.to_string()})
        if self.lanterns is not None:
            for index, (x, z) in enumerate(ring):
                if index % self.lantern_spacing == 0 and (x, z) != gate:
                    ops.append(
                        {
                            "type": "set",
                            "position": [x, y + 1, z],
                            "block": self.lantern_block.to_string(),
                        }
                    )
        return ops
