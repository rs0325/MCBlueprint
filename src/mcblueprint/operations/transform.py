"""Rigid coordinate transforms (translation, mirror, 90-degree rotation) and how
they act on block-state properties (docs/ARCHITECTURE.md section 5)."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, AXES, Vec3

Row = tuple[int, int, int]
Matrix = tuple[Row, Row, Row]

IDENTITY_ROWS: Matrix = ((1, 0, 0), (0, 1, 0), (0, 0, 1))

DIRECTIONS: dict[str, Vec3] = {
    "north": Vec3(0, 0, -1),
    "south": Vec3(0, 0, 1),
    "east": Vec3(1, 0, 0),
    "west": Vec3(-1, 0, 0),
    "up": Vec3(0, 1, 0),
    "down": Vec3(0, -1, 0),
}
DIRECTION_NAMES: dict[Vec3, str] = {v: k for k, v in DIRECTIONS.items()}
HORIZONTAL = ("north", "east", "south", "west")

LEFT_RIGHT_SWAPS = {
    "left": "right",
    "right": "left",
    "inner_left": "inner_right",
    "inner_right": "inner_left",
    "outer_left": "outer_right",
    "outer_right": "outer_left",
}
TOP_BOTTOM_SWAPS = {"top": "bottom", "bottom": "top"}


def _mul(rows: Matrix, v: Vec3) -> Vec3:
    return Vec3(*(r[0] * v.x + r[1] * v.y + r[2] * v.z for r in rows))


def _compose(outer: Matrix, inner: Matrix) -> Matrix:
    cols = [
        _mul(outer, _mul(inner, Vec3(*[1 if i == j else 0 for i in range(3)]))) for j in range(3)
    ]
    return tuple(tuple(cols[j][i] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def _det(rows: Matrix) -> int:
    (a, b, c), (d, e, f), (g, h, i) = rows
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


@dataclass(frozen=True, slots=True)
class Transform:
    """``p' = rows · p + offset`` where ``rows`` is a signed permutation matrix.

    Covers translations, reflections across axis-aligned planes and rotations by
    multiples of 90 degrees about the vertical axis, and their compositions.
    """

    rows: Matrix = IDENTITY_ROWS
    offset: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))

    @classmethod
    def identity(cls) -> Transform:
        return cls()

    @classmethod
    def translation(cls, offset: Vec3) -> Transform:
        return cls(IDENTITY_ROWS, offset)

    @classmethod
    def mirror(cls, axis: str, at: float) -> Transform:
        """Reflection across the plane ``axis = at`` (``at`` may end in .5)."""
        doubled = at * 2
        if doubled != int(doubled):
            raise BlueprintError(f"mirror position must be a multiple of 0.5, got {at}")
        index = AXES.index(axis)
        rows = [list(r) for r in IDENTITY_ROWS]
        rows[index][index] = -1
        offset = Vec3(0, 0, 0).with_axis(axis, int(doubled))
        return cls(tuple(tuple(r) for r in rows), offset)  # type: ignore[arg-type]

    @classmethod
    def rotation(cls, angle: int, center: Vec3) -> Transform:
        """Rotate ``angle`` degrees clockwise (seen from above) about the vertical
        axis through ``center``; ``angle`` is 0, 90, 180 or 270."""
        if angle % 90 != 0:
            raise BlueprintError(f"rotation angle must be a multiple of 90, got {angle}")
        turns = (angle // 90) % 4
        # clockwise from above: east -> south -> west -> north, i.e. (x, z) -> (-z, x)
        rows: Matrix = IDENTITY_ROWS
        quarter: Matrix = ((0, 0, -1), (0, 1, 0), (1, 0, 0))
        for _ in range(turns):
            rows = _compose(quarter, rows)
        # keep the centre fixed: offset = center - rows · center
        offset = center - _mul(rows, center)
        return cls(rows, offset)

    @property
    def flips_y(self) -> bool:
        return self.rows[1][1] < 0

    @property
    def is_reflection(self) -> bool:
        return _det(self.rows) < 0

    def apply(self, pos: Vec3) -> Vec3:
        return _mul(self.rows, pos) + self.offset

    def apply_direction(self, name: str) -> str:
        """Map a direction name (``north`` ...) through the linear part."""
        vec = DIRECTIONS.get(name)
        if vec is None:
            return name
        return DIRECTION_NAMES.get(_mul(self.rows, vec), name)

    def apply_axis(self, name: str) -> str:
        if name not in AXES:
            return name
        unit = Vec3(0, 0, 0).with_axis(name, 1)
        moved = _mul(self.rows, unit)
        for axis in AXES:
            if moved.axis(axis) != 0:
                return axis
        return name

    def apply_state(self, state: BlockState) -> BlockState:
        """Rewrite direction-like properties so the block keeps its orientation."""
        if self.rows == IDENTITY_ROWS:
            return state
        props = dict(state.properties)
        new_props: dict[str, str] = {}
        for name, value in props.items():
            if name in DIRECTIONS:
                # connection flags / wall sides: the property *name* is a direction
                new_props[self.apply_direction(name)] = value
            elif name == "facing":
                new_props[name] = self.apply_direction(value)
            elif name == "axis":
                new_props[name] = self.apply_axis(value)
            elif name in ("half", "type") and self.flips_y and value in TOP_BOTTOM_SWAPS:
                new_props[name] = TOP_BOTTOM_SWAPS[value]
            elif name in ("shape", "hinge") and self.is_reflection and value in LEFT_RIGHT_SWAPS:
                new_props[name] = LEFT_RIGHT_SWAPS[value]
            else:
                new_props[name] = value
        return BlockState(state.id, tuple(sorted(new_props.items())))

    def then(self, outer: Transform) -> Transform:
        """Transform that applies ``self`` first, then ``outer``."""
        return Transform(
            _compose(outer.rows, self.rows), _mul(outer.rows, self.offset) + outer.offset
        )

    def bounds(self, box: AABB) -> AABB:
        return AABB.of(self.apply(box.min), self.apply(box.max))


def mirror_state(state: BlockState, axis: str) -> BlockState:
    """Property rewrite for a reflection across ``axis`` (position independent)."""
    return Transform.mirror(axis, 0).apply_state(state)
