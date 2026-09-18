"""Integer 3D vector and axis-aligned bounding box."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

AXES = ("x", "y", "z")


@dataclass(frozen=True, slots=True)
class Vec3:
    x: int
    y: int
    z: int

    @classmethod
    def from_seq(cls, values: Sequence[int]) -> Vec3:
        if len(values) != 3:
            raise ValueError(f"expected 3 integers, got {list(values)!r}")
        return cls(int(values[0]), int(values[1]), int(values[2]))

    def to_list(self) -> list[int]:
        return [self.x, self.y, self.z]

    def __iter__(self) -> Iterator[int]:
        yield self.x
        yield self.y
        yield self.z

    def __getitem__(self, index: int) -> int:
        return (self.x, self.y, self.z)[index]

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: int) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    def axis(self, name: str) -> int:
        return getattr(self, name)

    def with_axis(self, name: str, value: int) -> Vec3:
        values = self.to_list()
        values[AXES.index(name)] = value
        return Vec3(*values)

    @staticmethod
    def min(a: Vec3, b: Vec3) -> Vec3:
        return Vec3(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))

    @staticmethod
    def max(a: Vec3, b: Vec3) -> Vec3:
        return Vec3(max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))

    def __str__(self) -> str:
        return f"[{self.x}, {self.y}, {self.z}]"


@dataclass(frozen=True, slots=True)
class AABB:
    """Inclusive axis-aligned bounding box."""

    min: Vec3
    max: Vec3

    def __post_init__(self) -> None:
        if self.min.x > self.max.x or self.min.y > self.max.y or self.min.z > self.max.z:
            raise ValueError(f"min {self.min} must not exceed max {self.max}")

    @classmethod
    def of(cls, a: Vec3, b: Vec3) -> AABB:
        """Box spanning two corners given in any order."""
        return cls(Vec3.min(a, b), Vec3.max(a, b))

    @classmethod
    def from_points(cls, points: Iterable[Vec3]) -> AABB | None:
        it = iter(points)
        try:
            first = next(it)
        except StopIteration:
            return None
        lo = hi = first
        for p in it:
            lo = Vec3.min(lo, p)
            hi = Vec3.max(hi, p)
        return cls(lo, hi)

    @property
    def size(self) -> Vec3:
        return self.max - self.min + Vec3(1, 1, 1)

    @property
    def volume(self) -> int:
        s = self.size
        return s.x * s.y * s.z

    def union(self, other: AABB) -> AABB:
        return AABB(Vec3.min(self.min, other.min), Vec3.max(self.max, other.max))

    def contains(self, pos: Vec3) -> bool:
        return (
            self.min.x <= pos.x <= self.max.x
            and self.min.y <= pos.y <= self.max.y
            and self.min.z <= pos.z <= self.max.z
        )

    def __str__(self) -> str:
        return (
            f"X {self.min.x}..{self.max.x}  Y {self.min.y}..{self.max.y}  "
            f"Z {self.min.z}..{self.max.z}"
        )
