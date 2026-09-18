"""Weighted random block palettes (see docs/FORMAT.md section 5)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from mcblueprint.model.block import BlockState


@dataclass(frozen=True, slots=True)
class PaletteEntry:
    block: BlockState
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    entries: tuple[PaletteEntry, ...]

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError(f"palette {self.name!r} has no entries")

    def choose(self, rng: random.Random) -> BlockState:
        """Pick one block; consumes exactly one draw from ``rng``."""
        if len(self.entries) == 1:
            rng.random()
            return self.entries[0].block
        weights = [entry.weight for entry in self.entries]
        return rng.choices(self.entries, weights=weights, k=1)[0].block
