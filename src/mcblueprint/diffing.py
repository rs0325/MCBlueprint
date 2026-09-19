"""Compare two generated BlockVolumes (``mcblueprint diff``)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from mcblueprint import blockdata
from mcblueprint.model.blueprint import Blueprint
from mcblueprint.model.vec import Vec3
from mcblueprint.volume import BlockVolume

SAMPLE_LIMIT = 10


@dataclass
class VolumeDiff:
    added: dict[Vec3, str] = field(default_factory=dict)
    removed: dict[Vec3, str] = field(default_factory=dict)
    changed: dict[Vec3, tuple[str, str]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def state_deltas(self) -> dict[str, int]:
        """Net change in cell count per block state, largest absolute change first."""
        counts: Counter[str] = Counter()
        for state in self.added.values():
            counts[state] += 1
        for state in self.removed.values():
            counts[state] -= 1
        for before, after in self.changed.values():
            counts[before] -= 1
            counts[after] += 1
        nonzero = ((k, v) for k, v in counts.items() if v)
        return dict(sorted(nonzero, key=lambda kv: (-abs(kv[1]), kv[0])))

    def to_json(self) -> dict[str, Any]:
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "changed": len(self.changed),
            "stateDeltas": self.state_deltas(),
            "samples": {
                "added": [{"position": p.to_list(), "block": s} for p, s in _sample(self.added)],
                "removed": [
                    {"position": p.to_list(), "block": s} for p, s in _sample(self.removed)
                ],
                "changed": [
                    {"position": p.to_list(), "before": b, "after": a}
                    for p, (b, a) in _sample(self.changed)
                ],
            },
        }


def _sample(cells: dict[Vec3, Any]) -> list[tuple[Vec3, Any]]:
    ordered = sorted(cells.items(), key=lambda kv: (kv[0].y, kv[0].z, kv[0].x))
    return ordered[:SAMPLE_LIMIT]


AIR_IDS = frozenset({"minecraft:air", "minecraft:cave_air", "minecraft:void_air"})


def normalize(volume: BlockVolume, blueprint: Blueprint) -> BlockVolume:
    """Paste-equivalent form: coordinates relative to ``origin``, explicit air
    dropped, block properties completed with defaults."""
    blocks = blockdata.load_block_data(blueprint.minecraft_version)
    result = BlockVolume()
    for pos, state in volume:
        if state.id in AIR_IDS:
            continue
        result.set(pos - blueprint.origin, blocks.complete(state))
    return result


def diff_volumes(before: BlockVolume, after: BlockVolume) -> VolumeDiff:
    result = VolumeDiff()
    seen: set[Vec3] = set()
    for pos, state in before:
        seen.add(pos)
        other = after.get(pos)
        if other is None:
            result.removed[pos] = state.to_string()
        elif other != state:
            result.changed[pos] = (state.to_string(), other.to_string())
    for pos, state in after:
        if pos not in seen:
            result.added[pos] = state.to_string()
    return result


def format_diff(diff: VolumeDiff) -> str:
    if diff.is_empty:
        return "No differences."
    lines = [
        f"Added: {len(diff.added)}  Removed: {len(diff.removed)}  Changed: {len(diff.changed)}",
        "",
    ]
    deltas = diff.state_deltas()
    if deltas:
        width = max(len(f"{v:+d}") for v in deltas.values())
        lines.extend(f"{v:+{width}d}  {k}" for k, v in deltas.items())
        lines.append("")
    for label, cells in (("Added", diff.added), ("Removed", diff.removed)):
        if cells:
            lines.append(f"{label} (first {min(len(cells), SAMPLE_LIMIT)}):")
            lines.extend(f"  {p} {s}" for p, s in _sample(cells))
    if diff.changed:
        lines.append(f"Changed (first {min(len(diff.changed), SAMPLE_LIMIT)}):")
        lines.extend(f"  {p} {b} -> {a}" for p, (b, a) in _sample(diff.changed))
    return "\n".join(lines).rstrip()
