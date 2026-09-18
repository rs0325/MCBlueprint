import random

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model import AABB, BlockState, Palette, PaletteEntry, Vec3
from mcblueprint.operations import (
    OPERATIONS,
    BlockSpec,
    ExecutionContext,
    Transform,
    build_operation,
    build_operations,
)
from mcblueprint.operations.base import MAX_DEPTH, parse_choice, parse_int, parse_vec
from mcblueprint.volume import BlockVolume

STONE = BlockState.parse("stone")


class TestBlockSpec:
    def test_block(self) -> None:
        spec = BlockSpec.from_dict({"block": "oak_planks"}, "operations[0]")
        assert spec.block == BlockState.parse("minecraft:oak_planks")
        assert spec.palette is None

    def test_palette(self) -> None:
        spec = BlockSpec.from_dict({"palette": "p"}, "operations[0]")
        assert spec.block is None
        assert spec.palette == "p"

    @pytest.mark.parametrize("data", [{}, {"block": "a", "palette": "p"}])
    def test_exactly_one_required(self, data: dict) -> None:
        with pytest.raises(BlueprintError, match="exactly one of"):
            BlockSpec.from_dict(data, "operations[0]")

    def test_invalid_block_reports_path(self) -> None:
        with pytest.raises(BlueprintError, match=r"operations\[0\]\.block"):
            BlockSpec.from_dict({"block": "Bad"}, "operations[0]")


class TestTransform:
    def test_identity_and_translation(self) -> None:
        assert Transform.identity().apply(Vec3(1, 2, 3)) == Vec3(1, 2, 3)
        assert Transform.translation(Vec3(10, 0, -1)).apply(Vec3(1, 2, 3)) == Vec3(11, 2, 2)

    @pytest.mark.parametrize(
        ("axis", "at", "pos", "expected"),
        [
            ("x", 0, Vec3(3, 1, 2), Vec3(-3, 1, 2)),
            ("x", 5, Vec3(3, 1, 2), Vec3(7, 1, 2)),
            ("x", 0.5, Vec3(0, 1, 2), Vec3(1, 1, 2)),
            ("x", 0.5, Vec3(1, 1, 2), Vec3(0, 1, 2)),
            ("y", 10, Vec3(3, 1, 2), Vec3(3, 19, 2)),
            ("z", -1.5, Vec3(3, 1, 2), Vec3(3, 1, -5)),
        ],
    )
    def test_mirror(self, axis: str, at: float, pos: Vec3, expected: Vec3) -> None:
        assert Transform.mirror(axis, at).apply(pos) == expected

    def test_mirror_requires_half_steps(self) -> None:
        with pytest.raises(BlueprintError):
            Transform.mirror("x", 0.3)

    def test_mirror_twice_is_identity(self) -> None:
        m = Transform.mirror("x", 2)
        assert m.then(m) == Transform.identity()

    def test_composition_order(self) -> None:
        # inner: translate by (1,0,0); outer: mirror x at 0 -> p' = -(p + 1)
        inner = Transform.translation(Vec3(1, 0, 0))
        outer = Transform.mirror("x", 0)
        composed = inner.then(outer)
        p = Vec3(2, 5, 7)
        assert composed.apply(p) == outer.apply(inner.apply(p)) == Vec3(-3, 5, 7)
        # the other order: mirror first, then translate -> p' = -p + 1
        composed2 = outer.then(inner)
        assert composed2.apply(p) == inner.apply(outer.apply(p)) == Vec3(-1, 5, 7)

    def test_mirror_in_repeat_moves_mirror_plane(self) -> None:
        # repeat offset (10,0,0) containing mirror x at 0: plane moves to x=10
        mirror = Transform.mirror("x", 0)
        shift = Transform.translation(Vec3(10, 0, 0))
        composed = mirror.then(shift)
        assert composed.apply(Vec3(3, 0, 0)) == Vec3(7, 0, 0)

    def test_bounds(self) -> None:
        box = AABB.of(Vec3(1, 0, 0), Vec3(3, 2, 2))
        assert Transform.mirror("x", 0).bounds(box) == AABB.of(Vec3(-3, 0, 0), Vec3(-1, 2, 2))


class TestExecutionContext:
    def make(self, seed: int = 0, transform: Transform | None = None) -> ExecutionContext:
        palettes = {
            "p": Palette(
                "p",
                (PaletteEntry(BlockState.parse("a"), 1), PaletteEntry(BlockState.parse("b"), 1)),
            )
        }
        return ExecutionContext(BlockVolume(), random.Random(seed), palettes, transform)

    def test_place_applies_transform(self) -> None:
        ctx = self.make(transform=Transform.translation(Vec3(5, 5, 5)))
        ctx.place(Vec3(1, 1, 1), BlockSpec(block=STONE))
        assert ctx.volume.get(Vec3(6, 6, 6)) == STONE

    def test_palette_is_deterministic_and_consumes_rng_only_for_palettes(self) -> None:
        picks = []
        for _ in range(2):
            ctx = self.make(seed=42)
            ctx.place_all([Vec3(x, 0, 0) for x in range(20)], BlockSpec(palette="p"))
            picks.append([ctx.volume.get(Vec3(x, 0, 0)).id for x in range(20)])
        assert picks[0] == picks[1]
        assert len(set(picks[0])) == 2

        ctx = self.make(seed=1)
        state = ctx.rng.getstate()
        ctx.place(Vec3(0, 0, 0), BlockSpec(block=STONE))
        assert ctx.rng.getstate() == state

    def test_unknown_palette(self) -> None:
        ctx = self.make()
        with pytest.raises(BlueprintError, match="Unknown palette"):
            ctx.place(Vec3(0, 0, 0), BlockSpec(palette="missing"))

    def test_child_composes_and_limits_depth(self) -> None:
        ctx = self.make(transform=Transform.translation(Vec3(10, 0, 0)))
        child = ctx.child(Transform.translation(Vec3(1, 0, 0)))
        assert child.depth == 2
        assert child.volume is ctx.volume
        assert child.rng is ctx.rng
        assert child.transform.apply(Vec3(0, 0, 0)) == Vec3(11, 0, 0)

        deepest = ctx
        for _ in range(MAX_DEPTH - 1):
            deepest = deepest.child(Transform.identity())
        assert deepest.depth == MAX_DEPTH
        with pytest.raises(BlueprintError, match="nesting"):
            deepest.child(Transform.identity())


class TestRegistry:
    def test_build_operation(self) -> None:
        assert "test_point" in OPERATIONS
        op = build_operation({"type": "test_point", "position": [1, 2, 3], "block": "a"}, "x[0]")
        assert op.path == "x[0]"
        assert op.bounds() == AABB(Vec3(1, 2, 3), Vec3(1, 2, 3))

    def test_unknown_type(self) -> None:
        with pytest.raises(BlueprintError, match="unknown operation type 'nope'"):
            build_operation({"type": "nope"}, "operations[3]")

    def test_build_operations_paths(self) -> None:
        ops = build_operations(
            [
                {"type": "test_point", "position": [0, 0, 0], "block": "a"},
                {"type": "test_point", "position": [1, 0, 0], "block": "a"},
            ],
            "operations",
        )
        assert [op.path for op in ops] == ["operations[0]", "operations[1]"]


class TestParseHelpers:
    def test_parse_vec(self) -> None:
        assert parse_vec({"p": [1, 2, 3]}, "p", "op") == Vec3(1, 2, 3)
        with pytest.raises(BlueprintError, match="missing required 'p'"):
            parse_vec({}, "p", "op")
        with pytest.raises(BlueprintError, match="3 integers"):
            parse_vec({"p": [1, 2]}, "p", "op")

    def test_parse_int(self) -> None:
        assert parse_int({"n": 3}, "n", "op", minimum=1) == 3
        assert parse_int({}, "n", "op", minimum=1, default=1) == 1
        with pytest.raises(BlueprintError):
            parse_int({"n": 0}, "n", "op", minimum=1)
        with pytest.raises(BlueprintError):
            parse_int({"n": True}, "n", "op", minimum=0)
        with pytest.raises(BlueprintError):
            parse_int({}, "n", "op", minimum=1)

    def test_parse_choice(self) -> None:
        assert parse_choice({}, "mode", "op", ("hollow", "solid"), "hollow") == "hollow"
        assert (
            parse_choice({"mode": "solid"}, "mode", "op", ("hollow", "solid"), "hollow") == "solid"
        )
        with pytest.raises(BlueprintError):
            parse_choice({"mode": "x"}, "mode", "op", ("hollow", "solid"), "hollow")


class TestGenerator:
    def blueprint(self, seed: int | None = None) -> dict:
        data = {
            "formatVersion": 1,
            "minecraftVersion": "1.21.11",
            "name": "gen",
            "palettes": {"p": [{"block": "a", "weight": 1}, {"block": "b", "weight": 1}]},
            "operations": [
                {"type": "test_point", "position": [x, 0, 0], "palette": "p"} for x in range(30)
            ]
            + [{"type": "test_point", "position": [0, 0, 0], "block": "stone"}],
        }
        if seed is not None:
            data["seed"] = seed
        return data

    def test_deterministic_for_same_seed(self) -> None:
        a = generate(load_blueprint_dict(self.blueprint(seed=7)))
        b = generate(load_blueprint_dict(self.blueprint(seed=7)))
        assert list(a) == list(b)
        assert len(a) == 30
        assert a.get(Vec3(0, 0, 0)) == STONE  # later operation overwrites

    def test_seed_override_and_different_seed(self) -> None:
        base = generate(load_blueprint_dict(self.blueprint(seed=7)))
        overridden = generate(load_blueprint_dict(self.blueprint(seed=7)), seed=8)
        same_as_override = generate(load_blueprint_dict(self.blueprint(seed=8)))
        assert list(overridden) == list(same_as_override)
        assert list(overridden) != list(base)

    def test_default_seed_is_zero(self) -> None:
        default = generate(load_blueprint_dict(self.blueprint()))
        explicit = generate(load_blueprint_dict(self.blueprint(seed=0)))
        assert list(default) == list(explicit)
