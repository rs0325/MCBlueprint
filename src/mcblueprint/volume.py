"""Sparse block container produced by the generator and consumed by exporters."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3


class BlockVolume:
    """Maps positions to block states; later ``set`` calls overwrite earlier ones.

    States are interned into ``palette`` so each cell stores only an index.
    Positions never written are absent (exporters treat them as air).
    """

    def __init__(self) -> None:
        self._cells: dict[Vec3, int] = {}
        self._palette: list[BlockState] = []
        self._index: dict[BlockState, int] = {}

    @property
    def palette(self) -> list[BlockState]:
        return list(self._palette)

    def set(self, pos: Vec3, state: BlockState) -> None:
        index = self._index.get(state)
        if index is None:
            index = len(self._palette)
            self._palette.append(state)
            self._index[state] = index
        self._cells[pos] = index

    def get(self, pos: Vec3) -> BlockState | None:
        index = self._cells.get(pos)
        return None if index is None else self._palette[index]

    def __contains__(self, pos: Vec3) -> bool:
        return pos in self._cells

    def __len__(self) -> int:
        return len(self._cells)

    def __iter__(self) -> Iterator[tuple[Vec3, BlockState]]:
        for pos, index in self._cells.items():
            yield pos, self._palette[index]

    def positions(self) -> Iterator[Vec3]:
        return iter(self._cells)

    def bounds(self) -> AABB | None:
        return AABB.from_points(self._cells)

    def count_by_state(self) -> dict[str, int]:
        """Block state string -> number of cells, most frequent first."""
        counts = Counter(self._cells.values())
        ordered = sorted(counts.items(), key=lambda item: (-item[1], self._palette[item[0]].id))
        return {self._palette[index].to_string(): count for index, count in ordered}
