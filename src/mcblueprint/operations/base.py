"""Operation base class and execution model (see docs/ARCHITECTURE.md section 5)."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar, Self

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.palette import Palette
from mcblueprint.model.vec import AABB, AXES, Vec3
from mcblueprint.volume import BlockVolume

MAX_DEPTH = 8


@dataclass(frozen=True, slots=True)
class BlockSpec:
    """Either a concrete block or a palette name (exactly one of them)."""

    block: BlockState | None = None
    palette: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> BlockSpec:
        has_block = "block" in data
        has_palette = "palette" in data
        if has_block == has_palette:
            raise BlueprintError(f"{path}: exactly one of 'block' or 'palette' must be given")
        if has_block:
            try:
                return cls(block=BlockState.parse(data["block"]))
            except BlueprintError as exc:
                raise BlueprintError(f"{path}.block: {exc}") from None
        return cls(palette=data["palette"])


@dataclass(frozen=True, slots=True)
class Transform:
    """Per-axis flip followed by a per-axis offset: ``p' = offset ± p``."""

    flip: tuple[bool, bool, bool] = (False, False, False)
    offset: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))

    @classmethod
    def identity(cls) -> Transform:
        return cls()

    @classmethod
    def translation(cls, offset: Vec3) -> Transform:
        return cls(offset=offset)

    @classmethod
    def mirror(cls, axis: str, at: float) -> Transform:
        """Reflection across the plane ``axis = at`` (``at`` may end in .5)."""
        doubled = at * 2
        if doubled != int(doubled):
            raise BlueprintError(f"mirror position must be a multiple of 0.5, got {at}")
        index = AXES.index(axis)
        flip = [False, False, False]
        flip[index] = True
        return cls(tuple(flip), Vec3(0, 0, 0).with_axis(axis, int(doubled)))

    def apply(self, pos: Vec3) -> Vec3:
        return Vec3(
            *(
                (self.offset[i] - pos[i]) if self.flip[i] else (self.offset[i] + pos[i])
                for i in range(3)
            )
        )

    def apply_state(self, state: BlockState) -> BlockState:
        """Flip direction-like properties for each mirrored axis."""
        for i, axis in enumerate(AXES):
            if self.flip[i]:
                state = mirror_state(state, axis)
        return state

    def then(self, outer: Transform) -> Transform:
        """Transform that applies ``self`` first, then ``outer``."""
        flip = tuple(self.flip[i] != outer.flip[i] for i in range(3))
        offset = Vec3(
            *(
                (-self.offset[i] if outer.flip[i] else self.offset[i]) + outer.offset[i]
                for i in range(3)
            )
        )
        return Transform(flip, offset)  # type: ignore[arg-type]

    def bounds(self, box: AABB) -> AABB:
        return AABB.of(self.apply(box.min), self.apply(box.max))


def mirror_state(state: BlockState, axis: str) -> BlockState:
    """Property flips applied when mirroring across ``axis`` (filled in by the mirror op)."""
    return state


class ExecutionContext:
    """Shared state while executing operations: target volume, RNG, palettes, transform."""

    def __init__(
        self,
        volume: BlockVolume,
        rng: random.Random,
        palettes: Mapping[str, Palette],
        transform: Transform | None = None,
        depth: int = 1,
    ) -> None:
        self.volume = volume
        self.rng = rng
        self.palettes = palettes
        self.transform = transform or Transform.identity()
        self.depth = depth

    def resolve(self, spec: BlockSpec) -> BlockState:
        if spec.block is not None:
            return spec.block
        assert spec.palette is not None
        try:
            palette = self.palettes[spec.palette]
        except KeyError:
            raise BlueprintError(f"Unknown palette: {spec.palette!r}") from None
        return palette.choose(self.rng)

    def place(self, pos: Vec3, spec: BlockSpec) -> None:
        state = self.transform.apply_state(self.resolve(spec))
        self.volume.set(self.transform.apply(pos), state)

    def place_all(self, positions: Iterable[Vec3], spec: BlockSpec) -> None:
        for pos in positions:
            self.place(pos, spec)

    def child(self, transform: Transform) -> ExecutionContext:
        """Context for nested operations: composes ``transform`` inside the current one."""
        if self.depth >= MAX_DEPTH:
            raise BlueprintError(f"Operation nesting deeper than {MAX_DEPTH} levels")
        return ExecutionContext(
            self.volume,
            self.rng,
            self.palettes,
            transform.then(self.transform),
            self.depth + 1,
        )


class Operation(ABC):
    """One step of a Blueprint. Subclasses set ``type`` and register themselves."""

    type: ClassVar[str]

    def __init__(self, path: str, comment: str | None = None) -> None:
        self.path = path
        self.comment = comment

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Mapping[str, Any], path: str) -> Self:
        """Build from schema-valid JSON data; ``path`` is used in error messages."""

    @abstractmethod
    def bounds(self) -> AABB:
        """Box containing every cell this operation can write, without executing it."""

    @abstractmethod
    def apply(self, ctx: ExecutionContext) -> None:
        """Write this operation's cells into ``ctx``."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.path}>"


class PlacementOperation(Operation):
    """Operation that writes one block/palette to a set of cells."""

    def __init__(self, path: str, spec: BlockSpec, comment: str | None = None) -> None:
        super().__init__(path, comment)
        self.spec = spec

    @abstractmethod
    def cells(self) -> Iterable[Vec3]:
        """Cells in placement order (see docs/OPERATIONS.md)."""

    def apply(self, ctx: ExecutionContext) -> None:
        ctx.place_all(self.cells(), self.spec)


def parse_vec(data: Mapping[str, Any], key: str, path: str) -> Vec3:
    try:
        return Vec3.from_seq(data[key])
    except KeyError:
        raise BlueprintError(f"{path}: missing required '{key}'") from None
    except (TypeError, ValueError):
        raise BlueprintError(f"{path}.{key}: must be an array of 3 integers") from None


def parse_int(
    data: Mapping[str, Any], key: str, path: str, *, minimum: int, default: int | None = None
) -> int:
    if key not in data:
        if default is None:
            raise BlueprintError(f"{path}: missing required '{key}'")
        return default
    value = data[key]
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise BlueprintError(f"{path}.{key}: must be an integer >= {minimum}")
    return value


def parse_choice(
    data: Mapping[str, Any], key: str, path: str, choices: tuple[str, ...], default: str
) -> str:
    value = data.get(key, default)
    if value not in choices:
        raise BlueprintError(f"{path}.{key}: must be one of {', '.join(choices)}")
    return value
