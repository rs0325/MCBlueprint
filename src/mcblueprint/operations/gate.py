"""``gate``: a gatehouse through a wall: a solid block with an arched passage, a
walkway on top with battlements along the front and back, an optional portcullis
and door in the passage, and optional square towers on both sides.

``position`` is the centre of the ground layer under the passage on the gate's front
face; the body extends ``depth`` blocks backwards (+z for a wall along x, +x for a
wall along z) like a wall's thickness. Expands into ``fill``, ``arch``, ``set``,
``doorway`` and ``tower``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import Vec3
from mcblueprint.operations.arch import STYLES as ARCH_STYLES
from mcblueprint.operations.arch import ArchSpec, opening_cells
from mcblueprint.operations.base import BlockSpec, parse_choice, parse_int, parse_vec
from mcblueprint.operations.bridge import connected
from mcblueprint.operations.composite import CompositeOperation, parse_block, spec_json
from mcblueprint.operations.registry import register
from mcblueprint.operations.room import parse_spec
from mcblueprint.operations.tower import DEFAULT_MERLON_SPACING, _sub

AXES_H = ("x", "z")
DEFAULT_DEPTH = 3
DEFAULT_JAMB = 2
DEFAULT_TOP = 1
DEFAULT_TOWER_SIZE = 7  # size 5 leaves no room for a spiral staircase
DEFAULT_PORTCULLIS = "minecraft:iron_bars"
TOWER_PASSTHROUGH = ("floors", "stairs", "battlement", "windows", "door", "floor")


@register
class GateOperation(CompositeOperation):
    type = "gate"

    def __init__(
        self,
        path: str,
        position: Vec3,
        axis: str,
        width: int,
        height: int,
        spec: BlockSpec,
        depth: int = DEFAULT_DEPTH,
        jamb: int = DEFAULT_JAMB,
        top: int = DEFAULT_TOP,
        arch: ArchSpec | None = None,
        battlement: Mapping[str, Any] | None = None,
        portcullis: Mapping[str, Any] | None = None,
        door: BlockState | None = None,
        towers: Mapping[str, Any] | None = None,
        comment: str | None = None,
    ) -> None:
        super().__init__(path, comment)
        self.position = position
        self.axis = axis
        self.width = width
        self.height = height
        self.spec = spec
        self.depth = depth
        self.jamb = jamb
        self.top = top
        self.arch = arch or ArchSpec("round", spec)
        if self.arch.thickness > jamb:
            raise BlueprintError(
                f"{path}: the arch ring ({self.arch.thickness} thick) does not fit in the jambs "
                f"({jamb} wide); raise 'jamb' or lower 'arch.thickness'"
            )
        if door is not None and not door.id.endswith("_door"):
            raise BlueprintError(f"{path}.door: must be a door block (e.g. oak_door)")
        if door is not None and width > 2:
            raise BlueprintError(f"{path}: a door needs width 1 or 2")
        self.door = door
        self.rise = self.arch.rise(width)
        self._parse_battlement(battlement, path)
        self._parse_portcullis(portcullis, path)
        self._parse_towers(towers, path)

    def _parse_battlement(self, data: Mapping[str, Any] | None, path: str) -> None:
        self.battlement = data
        if data is None:
            return
        sub = f"{path}.battlement"
        self.battlement_spec = parse_spec(data, "block", sub) or self.spec
        self.merlon_spacing = parse_int(
            data, "spacing", sub, minimum=0, default=DEFAULT_MERLON_SPACING
        )

    def _parse_portcullis(self, data: Mapping[str, Any] | None, path: str) -> None:
        self.portcullis = data
        if data is None:
            return
        sub = f"{path}.portcullis"
        self.portcullis_block = parse_block(data, "block", sub) or BlockState.of(DEFAULT_PORTCULLIS)
        self.portcullis_height = parse_int(data, "height", sub, minimum=1, default=1)
        if self.portcullis_height > self.height - 2:
            raise BlueprintError(
                f"{sub}.height: must leave 2 clear rows in the passage "
                f"(at most {self.height - 2} for a passage {self.height} high)"
            )

    def _parse_towers(self, data: Mapping[str, Any] | None, path: str) -> None:
        self.towers = data
        if data is None:
            return
        sub = f"{path}.towers"
        size = parse_int(data, "size", sub, minimum=5, default=DEFAULT_TOWER_SIZE)
        if size % 2 == 0:
            raise BlueprintError(f"{sub}.size: must be odd so the centre is a block")
        self.tower_size = size
        self.tower_height = parse_int(
            data, "height", sub, minimum=3, default=self.walkway_y - self.position.y + 4
        )
        if self.tower_height < self.walkway_y - self.position.y + 1:
            raise BlueprintError(
                f"{sub}.height: must reach above the walkway "
                f"(at least {self.walkway_y - self.position.y + 1})"
            )
        self.tower_spec = parse_spec(data, "wall", sub) or self.spec
        unknown = set(data) - {"size", "height", "wall", *TOWER_PASSTHROUGH}
        if unknown:
            raise BlueprintError(f"{sub}: unknown key(s) {', '.join(sorted(unknown))}")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        arch = data.get("arch")
        spec = BlockSpec.from_dict(data, path)
        arch_spec: ArchSpec | None = None
        if arch is not None:
            if not isinstance(arch, Mapping):
                raise BlueprintError(f"{path}.arch: must be an object")
            sub = f"{path}.arch"
            ring = BlockSpec.from_dict(arch, sub) if "block" in arch or "palette" in arch else spec
            arch_spec = ArchSpec(
                parse_choice(arch, "style", sub, ARCH_STYLES, "round"),
                ring,
                parse_block(arch, "trim", sub),
                parse_int(arch, "thickness", sub, minimum=1, default=1),
            )
        return cls(
            path,
            parse_vec(data, "position", path),
            parse_choice(data, "axis", path, AXES_H, "x"),
            parse_int(data, "width", path, minimum=1),
            parse_int(data, "height", path, minimum=2),
            spec,
            parse_int(data, "depth", path, minimum=1, default=DEFAULT_DEPTH),
            parse_int(data, "jamb", path, minimum=1, default=DEFAULT_JAMB),
            parse_int(data, "top", path, minimum=0, default=DEFAULT_TOP),
            arch_spec,
            _sub(data, "battlement", path),
            _sub(data, "portcullis", path),
            parse_block(data, "door", path),
            _sub(data, "towers", path),
            data.get("comment"),
        )

    # --- geometry -------------------------------------------------------------

    @property
    def half(self) -> tuple[int, int]:
        """Passage extent across the axis: (cells before the centre, cells after)."""
        return (self.width - 1) // 2, self.width // 2

    @property
    def walkway_y(self) -> int:
        """Top row of the body (the walkway surface)."""
        return self.position.y + self.height + self.rise + 1 + self.top

    def _cell(self, u: int, y: int, d: int) -> Vec3:
        """World cell from ``u`` across the axis (0 = centre), ``y`` and depth ``d``."""
        c = self.position
        return Vec3(c.x + u, y, c.z + d) if self.axis == "x" else Vec3(c.x + d, y, c.z + u)

    def _box(self, u0: int, u1: int, y0: int, y1: int, d0: int, d1: int, block: dict[str, Any]):
        a, b = self._cell(u0, y0, d0), self._cell(u1, y1, d1)
        if a == b:
            return {"type": "set", "position": a.to_list(), **block}
        return {"type": "fill", "from": a.to_list(), "to": b.to_list(), **block}

    def expand(self) -> list[dict[str, Any]]:
        y0 = self.position.y
        before, after = self.half
        u_min, u_max = -before - self.jamb, after + self.jamb
        top_y = self.walkway_y
        ops: list[dict[str, Any]] = [
            self._box(u_min, u_max, y0 + 1, top_y, 0, self.depth - 1, spec_json(self.spec))
        ]
        # the passage: an arch through the whole depth
        arch = self.arch.operation(
            f"{self.path}.arch",
            self._cell(-before, y0 + 1, 0),
            self.axis,
            self.width,
            self.height + self.rise,
            depth=self.depth,
        )
        ops.extend(arch.expand())
        if self.battlement is not None:
            block = spec_json(self.battlement_spec)
            for d in (0, self.depth - 1):
                ops.append(self._box(u_min, u_max, top_y + 1, top_y + 1, d, d, block))
                cells = range(u_min, u_max + 1)
                for index, u in enumerate(cells):
                    if index % (self.merlon_spacing + 1) == 0:
                        ops.append(self._box(u, u, top_y + 2, top_y + 2, d, d, block))
        if self.portcullis is not None:
            d = self.depth // 2
            opening = opening_cells(self.width, self.height + self.rise, self.arch.style)
            top_v = max(v for _, v in opening)
            rows = range(top_v - self.portcullis_height + 1, top_v + 1)
            for v in rows:
                us = sorted(u for u, vv in opening if vv == v)
                for u in us:
                    state = connected(
                        self.portcullis_block, self.axis, (u - 1) in us, (u + 1) in us
                    )
                    ops.append(
                        self._box(
                            u - before,
                            u - before,
                            y0 + 1 + v,
                            y0 + 1 + v,
                            d,
                            d,
                            {"block": state.to_string()},
                        )
                    )
        if self.door is not None:
            ops.append(
                {
                    "type": "doorway",
                    "position": self._cell(-before, y0 + 1, 0).to_list(),
                    "facing": self._inward(),
                    "width": self.width,
                    "height": 2,
                    "door": self.door.to_string(),
                }
            )
        if self.towers is not None:
            ops.extend(self._tower_ops(u_min, u_max, top_y))
        return ops

    def _inward(self) -> str:
        return "south" if self.axis == "x" else "east"

    def _tower_ops(self, u_min: int, u_max: int, top_y: int) -> list[dict[str, Any]]:
        assert self.towers is not None
        size = self.tower_size
        half = (size - 1) // 2
        d_centre = (self.depth - 1) // 2
        ops: list[dict[str, Any]] = []
        for u_centre, side in ((u_min - 1 - half, -1), (u_max + 1 + half, 1)):
            centre = self._cell(u_centre, self.position.y, d_centre)
            tower: dict[str, Any] = {
                "type": "tower",
                "position": centre.to_list(),
                "shape": "square",
                "size": size,
                "height": self.tower_height,
                "wall": spec_json(self.tower_spec),
                "floors": top_y - self.position.y,
            }
            if self.battlement is not None and "battlement" not in self.towers:
                tower["battlement"] = {
                    **spec_json(self.battlement_spec),
                    "spacing": self.merlon_spacing,
                }
            for key in TOWER_PASSTHROUGH:
                if key in self.towers:
                    tower[key] = self.towers[key]
            if size < 7 and "stairs" not in self.towers:
                tower["stairs"] = False  # a 5-wide tower has no room for the staircase
            ops.append(tower)
            # an opening from the tower onto the walkway
            wall_u = u_centre - side * half
            ops.append(
                {
                    "type": "doorway",
                    "position": self._cell(wall_u, top_y + 1, d_centre).to_list(),
                    "facing": self._towards(side),
                    "width": 1,
                    "height": 2,
                }
            )
        return ops

    def _towards(self, side: int) -> str:
        """Direction from a tower on ``side`` towards the gate (along the axis)."""
        if self.axis == "x":
            return "east" if side < 0 else "west"
        return "south" if side < 0 else "north"
