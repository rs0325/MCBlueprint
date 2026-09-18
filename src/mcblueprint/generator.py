"""Turn a Blueprint into a BlockVolume by executing its operations in order."""

from __future__ import annotations

import random

from mcblueprint.model.blueprint import Blueprint
from mcblueprint.operations.base import ExecutionContext
from mcblueprint.volume import BlockVolume


def generate(blueprint: Blueprint, *, seed: int | None = None) -> BlockVolume:
    """Execute ``blueprint.operations``; ``seed`` overrides the blueprint's own seed."""
    effective_seed = blueprint.seed if seed is None else seed
    volume = BlockVolume()
    ctx = ExecutionContext(volume, random.Random(effective_seed), blueprint.palettes)
    for operation in blueprint.operations:
        operation.apply(ctx)
    return volume
