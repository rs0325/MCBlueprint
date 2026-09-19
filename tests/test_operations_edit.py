import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model import AABB, BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation, build_operations
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse


def run(*ops: dict[str, Any]) -> BlockVolume:
    ctx = ExecutionContext(BlockVolume(), random.Random(0), {})
    for op in build_operations(list(ops), "operations"):
        op.apply(ctx)
    return ctx.volume


def blueprint(*operations: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "n",
        "operations": list(operations),
        **extra,
    }


def fill(a: list[int], b: list[int], block: str) -> dict[str, Any]:
    return {"type": "fill", "from": a, "to": b, "block": block}


def point(x: int, y: int, z: int, block: str = "stone") -> dict[str, Any]:
    return {"type": "set", "position": [x, y, z], "block": block}


class TestReplace:
    def test_replace_by_id(self) -> None:
        volume = run(
            fill([0, 0, 0], [3, 0, 0], "stone"),
            point(1, 0, 0, "oak_planks"),
            {
                "type": "replace",
                "from": [0, 0, 0],
                "to": [2, 0, 0],
                "match": "stone",
                "block": "bricks",
            },
        )
        assert [volume.get(Vec3(x, 0, 0)).id for x in range(4)] == [
            "minecraft:bricks",
            "minecraft:oak_planks",
            "minecraft:bricks",
            "minecraft:stone",
        ]

    def test_match_properties_and_list(self) -> None:
        volume = run(
            point(0, 0, 0, "oak_stairs[facing=east]"),
            point(1, 0, 0, "oak_stairs[facing=west]"),
            point(2, 0, 0, "oak_planks"),
            {
                "type": "replace",
                "from": [0, 0, 0],
                "to": [2, 0, 0],
                "match": ["oak_stairs[facing=east]", "oak_planks"],
                "block": "stone",
            },
        )
        assert volume.get(Vec3(0, 0, 0)) == B("stone")
        assert volume.get(Vec3(1, 0, 0)) == B("oak_stairs[facing=west]")
        assert volume.get(Vec3(2, 0, 0)) == B("stone")

    def test_replace_air_fills_unset_cells(self) -> None:
        volume = run(
            point(0, 0, 0, "stone"),
            point(2, 0, 0, "stone"),
            {
                "type": "replace",
                "from": [0, 0, 0],
                "to": [2, 0, 0],
                "match": "air",
                "block": "glass",
            },
        )
        assert volume.get(Vec3(1, 0, 0)) == B("glass")
        assert volume.get(Vec3(0, 0, 0)) == B("stone")

    def test_replace_with_palette_and_bounds(self) -> None:
        bp = load_blueprint_dict(
            blueprint(
                fill([0, 0, 0], [9, 0, 0], "stone"),
                {
                    "type": "replace",
                    "from": [0, 0, 0],
                    "to": [9, 0, 0],
                    "match": "stone",
                    "palette": "p",
                },
                palettes={"p": [{"block": "a"}, {"block": "b"}]},
                seed=1,
            )
        )
        volume = generate(bp)
        assert {s.id for _, s in volume} == {"minecraft:a", "minecraft:b"}
        assert bp.operations[1].bounds() == AABB(Vec3(0, 0, 0), Vec3(9, 0, 0))

    def test_inside_mirror_uses_world_cells(self) -> None:
        volume = run(
            point(-3, 0, 0, "stone"),
            {
                "type": "mirror",
                "axis": "x",
                "at": 0,
                "keepOriginal": False,
                "operations": [
                    {
                        "type": "replace",
                        "from": [3, 0, 0],
                        "to": [3, 0, 0],
                        "match": "stone",
                        "block": "bricks",
                    }
                ],
            },
        )
        assert volume.get(Vec3(-3, 0, 0)) == B("bricks")

    @pytest.mark.parametrize(
        "op",
        [
            {"type": "replace", "from": [0, 0, 0], "to": [1, 0, 0], "block": "a"},
            {"type": "replace", "from": [0, 0, 0], "to": [1, 0, 0], "match": [], "block": "a"},
            {"type": "replace", "from": [0, 0, 0], "to": [1, 0, 0], "match": "Bad", "block": "a"},
            {"type": "replace", "from": [0, 0, 0], "to": [1, 0, 0], "match": "stone"},
        ],
    )
    def test_invalid(self, op: dict[str, Any]) -> None:
        with pytest.raises(BlueprintError):
            build_operation(op, "operations[0]")

    def test_validator_checks_match_blocks(self) -> None:
        op = {
            "type": "replace",
            "from": [0, 0, 0],
            "to": [1, 0, 0],
            "match": ["stone", "nope"],
            "block": "bricks",
        }
        errors = validate(blueprint(op))
        assert [e.path for e in errors] == ["operations[0].match[1]"]
        assert errors[0].message == "Unknown block id."


class TestTranslate:
    def test_shifts_nested(self) -> None:
        volume = run({"type": "translate", "offset": [5, 1, -2], "operations": [point(1, 0, 0)]})
        assert set(volume.positions()) == {Vec3(6, 1, -2)}

    def test_bounds_and_nesting(self) -> None:
        op = build_operation(
            {
                "type": "translate",
                "offset": [10, 0, 0],
                "operations": [
                    {"type": "mirror", "axis": "x", "at": 0, "operations": [point(2, 0, 0)]}
                ],
            },
            "operations[0]",
        )
        assert op.bounds() == AABB(Vec3(8, 0, 0), Vec3(12, 0, 0))


class TestRotate:
    def test_rotates_positions_and_states(self) -> None:
        volume = run(
            {
                "type": "rotate",
                "angle": 90,
                "center": [0, 0, 0],
                "operations": [
                    point(3, 0, 0, "oak_stairs[facing=east]"),
                    point(0, 0, 2, "oak_log[axis=z]"),
                ],
            }
        )
        assert volume.get(Vec3(0, 0, 3)) == B("oak_stairs[facing=south]")
        assert volume.get(Vec3(-2, 0, 0)) == B("oak_log[axis=x]")

    def test_center_and_bounds(self) -> None:
        op = build_operation(
            {
                "type": "rotate",
                "angle": 180,
                "center": [5, 0, 5],
                "operations": [fill([5, 0, 5], [8, 2, 6], "stone")],
            },
            "operations[0]",
        )
        assert op.bounds() == AABB(Vec3(2, 0, 4), Vec3(5, 2, 5))

    def test_four_rotations_via_repeat_make_symmetric_cross(self) -> None:
        arm = fill([1, 0, 0], [3, 0, 0], "stone")
        volume = run(
            arm,
            {"type": "rotate", "angle": 90, "center": [0, 0, 0], "operations": [arm]},
            {"type": "rotate", "angle": 180, "center": [0, 0, 0], "operations": [arm]},
            {"type": "rotate", "angle": 270, "center": [0, 0, 0], "operations": [arm]},
        )
        cells = set(volume.positions())
        assert len(cells) == 12
        assert (
            cells == {Vec3(-p.x, p.y, -p.z) for p in cells} == {Vec3(-p.z, p.y, p.x) for p in cells}
        )

    @pytest.mark.parametrize("angle", [45, 0, 360, "90"])
    def test_invalid_angle(self, angle: Any) -> None:
        with pytest.raises(BlueprintError):
            build_operation(
                {
                    "type": "rotate",
                    "angle": angle,
                    "center": [0, 0, 0],
                    "operations": [point(0, 0, 0)],
                },
                "operations[0]",
            )


class TestCopy:
    def test_copies_set_cells_only(self) -> None:
        volume = run(
            point(0, 0, 0, "stone"),
            point(2, 0, 0, "oak_planks"),
            {"type": "copy", "from": [0, 0, 0], "to": [2, 0, 0], "offset": [0, 5, 0]},
        )
        assert volume.get(Vec3(0, 5, 0)) == B("stone")
        assert volume.get(Vec3(1, 5, 0)) is None
        assert volume.get(Vec3(2, 5, 0)) == B("oak_planks")
        assert len(volume) == 4

    def test_overlapping_destination_uses_snapshot(self) -> None:
        volume = run(
            fill([0, 0, 0], [2, 0, 0], "stone"),
            point(0, 0, 0, "bricks"),
            {"type": "copy", "from": [0, 0, 0], "to": [2, 0, 0], "offset": [1, 0, 0]},
        )
        assert [volume.get(Vec3(x, 0, 0)).id.split(":")[1] for x in range(4)] == [
            "bricks",
            "bricks",
            "stone",
            "stone",
        ]

    def test_bounds(self) -> None:
        op = build_operation(
            {"type": "copy", "from": [0, 0, 0], "to": [2, 1, 2], "offset": [-5, 0, 3]},
            "operations[0]",
        )
        assert op.bounds() == AABB(Vec3(-5, 0, 0), Vec3(2, 1, 5))

    def test_copy_inside_repeat_chains(self) -> None:
        volume = run(
            point(0, 0, 0, "stone"),
            {
                "type": "repeat",
                "count": 3,
                "offset": [0, 0, 0],
                "operations": [
                    {"type": "copy", "from": [0, 0, 0], "to": [0, 0, 0], "offset": [1, 0, 0]}
                ],
            },
        )
        # each iteration copies (0,0,0) -> (1,0,0) again; the volume stays at two cells
        assert set(volume.positions()) == {Vec3(0, 0, 0), Vec3(1, 0, 0)}


def test_schema_accepts_all_edit_operations() -> None:
    ops = [
        {
            "type": "replace",
            "from": [0, 0, 0],
            "to": [1, 1, 1],
            "match": "stone",
            "block": "bricks",
        },
        {
            "type": "replace",
            "from": [0, 0, 0],
            "to": [1, 1, 1],
            "match": ["stone", "dirt"],
            "palette": "p",
        },
        {"type": "translate", "offset": [1, 0, 0], "operations": [point(0, 0, 0)]},
        {"type": "copy", "from": [0, 0, 0], "to": [1, 1, 1], "offset": [3, 0, 0]},
        {"type": "rotate", "angle": 270, "center": [0, 0, 0], "operations": [point(0, 0, 0)]},
    ]
    assert validate(blueprint(*ops, palettes={"p": [{"block": "stone"}]})) == []
