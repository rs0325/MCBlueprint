"""``bridge``: straight deck between two points, flat or humped (``arch``), with
optional railings on the outer edges and piers down to a given level.

``from`` / ``to`` are the two ends of the deck's centre line (the walking-surface
layer); the deck spans ``width`` cells across it. Expands into ``fill`` / ``set``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import Vec3
from mcblueprint.operations.base import BlockSpec, parse_choice, parse_int, parse_vec
from mcblueprint.operations.composite import (
    CompositeOperation,
    oriented,
    parse_block,
    spec_json,
)
from mcblueprint.operations.registry import register
from mcblueprint.operations.room import parse_spec

STYLES = ("flat", "arch")
DEFAULT_WIDTH = 3
CONNECTING_SUFFIXES = ("_fence", "_pane", "_bars")
WALL_SUFFIX = "_wall"


def connected(state: BlockState, axis: str, before: bool, after: bool) -> BlockState:
    """Fence / pane / bars / wall state joined to its neighbours along ``axis``
    (``before`` = towards -axis, ``after`` = towards +axis); explicit values win."""
    sides = ("west", "east") if axis == "x" else ("north", "south")
    if state.id.endswith(CONNECTING_SUFFIXES):
        for side, joined in zip(sides, (before, after), strict=True):
            if state.get(side) is None:
                state = state.with_property(side, "true" if joined else "false")
    elif state.id.endswith(WALL_SUFFIX):
        for side, joined in zip(sides, (before, after), strict=True):
            if state.get(side) is None:
                state = state.with_property(side, "low" if joined else "none")
        if state.get("up") is None:
            state = state.with_property("up", "false" if before and after else "true")
    return state


def profile(length: int, rise: int) -> list[int]:
    """Deck height above the ends for each cell: a 1:1 ramp up to ``rise``, a
    plateau, and a ramp down."""
    return [min(i, rise, length - 1 - i) for i in range(length)]


@register
class BridgeOperation(CompositeOperation):
    type = "bridge"

    def __init__(
        self,
        path: str,
        start: Vec3,
        end: Vec3,
        deck: BlockSpec,
        width: int = DEFAULT_WIDTH,
        style: str = "flat",
        rise: int = 0,
        stairs: BlockState | None = None,
        railing: BlockState | None = None,
        railing_height: int = 1,
        piers: Mapping[str, Any] | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        if start.y != end.y:
            raise BlueprintError(f"{path}: 'from' and 'to' must have the same y coordinate")
        if start.x != end.x and start.z != end.z:
            raise BlueprintError(f"{path}: the bridge must run straight along x or z")
        self.start = start
        self.end = end
        self.deck = deck
        self.width = width
        self.style = style
        self.stairs = stairs
        self.railing = railing
        self.railing_height = railing_height
        self.axis = "z" if start.x == end.x else "x"
        delta = end - start
        self.length = abs(delta.x) + abs(delta.z) + 1
        step = (delta.x + delta.z) // max(self.length - 1, 1) if self.length > 1 else 1
        self.along = Vec3(step, 0, 0) if self.axis == "x" else Vec3(0, 0, step)
        self.across = Vec3(0, 0, 1) if self.axis == "x" else Vec3(1, 0, 0)
        if style == "arch":
            if rise < 1:
                raise BlueprintError(f"{path}.rise: an arch bridge needs a rise of at least 1")
            if 2 * rise + 1 > self.length:
                raise BlueprintError(
                    f"{path}.rise: must be at most {(self.length - 1) // 2} for a bridge "
                    f"{self.length} long (ramp up, at least one flat block, ramp down)"
                )
            self.rise = rise
        else:
            self.rise = 0
        self.heights = profile(self.length, self.rise)
        self.piers = piers
        if piers is not None:
            sub = f"{path}.piers"
            self.pier_spacing = parse_int(piers, "spacing", sub, minimum=1)
            bottom = piers.get("bottom")
            if not isinstance(bottom, int) or isinstance(bottom, bool):
                raise BlueprintError(f"{sub}: missing required integer 'bottom'")
            if bottom >= start.y:
                raise BlueprintError(f"{sub}.bottom: must be below the deck (y {start.y})")
            self.pier_bottom = bottom
            self.pier_spec = parse_spec(piers, "block", sub) or deck

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        piers = data.get("piers")
        if piers is not None and not isinstance(piers, Mapping):
            raise BlueprintError(f"{path}.piers: must be an object with 'spacing' and 'bottom'")
        deck = parse_spec(data, "deck", path)
        if deck is None:
            raise BlueprintError(f"{path}: missing required 'deck'")
        return cls(
            path,
            parse_vec(data, "from", path),
            parse_vec(data, "to", path),
            deck,
            parse_int(data, "width", path, minimum=1, default=DEFAULT_WIDTH),
            parse_choice(data, "style", path, STYLES, "flat"),
            parse_int(data, "rise", path, minimum=0, default=0),
            parse_block(data, "stairs", path),
            parse_block(data, "railing", path),
            parse_int(data, "railingHeight", path, minimum=1, default=1),
            piers,
            data.get("comment"),
        )

    # --- geometry -------------------------------------------------------------

    @property
    def across_range(self) -> range:
        """Offsets across the deck; odd widths are centred, even widths lean +."""
        return range(-((self.width - 1) // 2), self.width // 2 + 1)

    def _cell(self, i: int, k: int, dy: int) -> Vec3:
        return self.start + self.along * i + self.across * k + Vec3(0, dy, 0)

    def _row(
        self, i: int, dy: int, block: dict[str, str], dy_to: int | None = None
    ) -> dict[str, Any]:
        """One row across the deck at cell ``i`` (optionally a column dy..dy_to)."""
        r = self.across_range
        a = self._cell(i, r.start, dy)
        b = self._cell(i, r.stop - 1, dy if dy_to is None else dy_to)
        if a == b:
            return {"type": "set", "position": a.to_list(), **block}
        return {"type": "fill", "from": a.to_list(), "to": b.to_list(), **block}

    def _surface(self, i: int) -> dict[str, str]:
        h = self.heights
        ascending = i > 0 and h[i] > h[i - 1]
        descending = i + 1 < len(h) and h[i] > h[i + 1]
        if not (ascending or descending):
            return spec_json(self.deck)
        # a step: stairs whose full side faces the centre of the bridge
        direction = self.along if ascending else -self.along
        facing = {
            (1, 0): "east",
            (-1, 0): "west",
            (0, 1): "south",
            (0, -1): "north",
        }[(direction.x, direction.z)]
        if self.stairs is not None:
            return oriented(BlockSpec(block=self.stairs), facing=facing, half="bottom")
        return spec_json(self.deck)

    def _railing_cells(self) -> list[dict[str, Any]]:
        assert self.railing is not None
        ops = []
        r = self.across_range
        edges = [r.start, r.stop - 1] if self.width > 1 else [r.start]
        for i in range(self.length):
            same_before = i > 0 and self.heights[i - 1] == self.heights[i]
            same_after = i + 1 < self.length and self.heights[i + 1] == self.heights[i]
            state = connected(self.railing, self.axis, same_before, same_after)
            for k in edges:
                a = self._cell(i, k, self.heights[i] + 1)
                b = self._cell(i, k, self.heights[i] + self.railing_height)
                op: dict[str, Any] = (
                    {"type": "set", "position": a.to_list()}
                    if a == b
                    else {"type": "fill", "from": a.to_list(), "to": b.to_list()}
                )
                ops.append({**op, "block": state.to_string()})
        return ops

    def expand(self) -> list[dict[str, Any]]:
        air = {"block": "minecraft:air"}
        ops: list[dict[str, Any]] = []
        for i, h in enumerate(self.heights):
            if h > 0:  # solid body under a raised deck cell
                ops.append(self._row(i, 0, spec_json(self.deck), h - 1))
            ops.append(self._row(i, h, self._surface(i)))
        for i, h in enumerate(self.heights):  # walking space: two rows above the deck
            ops.append(self._row(i, h + 1, air, h + 2))
        if self.railing is not None:
            ops.extend(self._railing_cells())
        if self.piers is not None:
            for i in range(self.pier_spacing, self.length - 1, self.pier_spacing):
                ops.append(
                    self._row(i, self.pier_bottom - self.start.y, spec_json(self.pier_spec), -1)
                )
        return ops
