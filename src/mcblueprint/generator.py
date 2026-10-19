"""Turn a Blueprint into a BlockVolume by executing its operations in order."""

from __future__ import annotations

import random

from mcblueprint.errors import BlueprintError
from mcblueprint.model.blueprint import Blueprint
from mcblueprint.operations.base import ExecutionContext
from mcblueprint.operations.box_like import iter_box
from mcblueprint.volume import MAX_VOLUME, BlockVolume


def generate(blueprint: Blueprint, *, seed: int | None = None) -> BlockVolume:
    """元地形の施工範囲（指定時）へOperationを順に適用し、新しいvolumeを返す。

    seedはBlueprintのseedを上書きする。snapshotは変更・再読込せず、呼出すたびに
    元状態から生成する。施工セル総数の上限超過・範囲外配置はBlueprintErrorになる。
    """
    effective_seed = blueprint.seed if seed is None else seed
    terrain = blueprint.terrain
    if terrain is not None and terrain.region.volume > MAX_VOLUME:
        raise BlueprintError(f"施工範囲が {MAX_VOLUME:,} セルを超えています（airを含む）")
    volume = BlockVolume(write_bounds=terrain.region if terrain is not None else None)
    if terrain is not None:
        for pos in iter_box(terrain.region):
            state = terrain.snapshot.get(terrain.snapshot.to_local(pos))
            assert state is not None
            volume.set(pos, state)
    ctx = ExecutionContext(volume, random.Random(effective_seed), blueprint.palettes)
    for operation in blueprint.operations:
        operation.apply(ctx)
    return volume
