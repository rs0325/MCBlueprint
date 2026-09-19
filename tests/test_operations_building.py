import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import AABB, BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation, build_operations
from mcblueprint.operations.spiral_stairs import ring_path, tread_cells
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse
AIR = B("air")


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


def solid(a: list[int], b: list[int]) -> dict[str, Any]:
    return {"type": "fill", "from": a, "to": b, "block": "stone"}


class TestStairs:
    def test_steps_headroom_and_landing(self) -> None:
        volume = run(
            solid([0, 0, 0], [2, 9, 9]),
            {
                "type": "stairs",
                "start": [1, 1, 1],
                "direction": "south",
                "height": 4,
                "block": "oak_stairs",
            },
        )
        for i in range(4):
            step = Vec3(1, 1 + i, 1 + i)
            assert volume.get(step) == B("oak_stairs[facing=south,half=bottom]")
            for dy in (1, 2, 3):
                assert volume.get(step + Vec3(0, dy, 0)) == AIR, (i, dy)
            assert volume.get(step + Vec3(0, 4, 0)) == B("stone")
        # landing cell after the last step keeps its floor and has headroom above it
        assert volume.get(Vec3(1, 4, 5)) == B("stone")
        assert [volume.get(Vec3(1, 5 + dy, 5)) for dy in range(3)] == [AIR, AIR, AIR]
        assert volume.get(Vec3(1, 8, 5)) == B("stone")

    def test_width_and_base_and_plain_block(self) -> None:
        volume = run(
            {
                "type": "stairs",
                "start": [0, 0, 0],
                "direction": "east",
                "height": 3,
                "width": 2,
                "headroom": 2,
                "block": "stone_bricks",
                "base": "cobblestone",
            }
        )
        # width extends to the right of east = south (+z)
        assert volume.get(Vec3(2, 2, 0)) == B("stone_bricks")
        assert volume.get(Vec3(2, 2, 1)) == B("stone_bricks")
        assert volume.get(Vec3(2, 0, 0)) == B("cobblestone")
        assert volume.get(Vec3(2, 1, 1)) == B("cobblestone")
        assert volume.get(Vec3(0, 0, 0)) == B("stone_bricks")
        assert volume.get(Vec3(0, 3, 0)) is None  # headroom 2 -> y 1..2 only

    def test_stairs_block_keeps_explicit_facing(self) -> None:
        op = build_operation(
            {
                "type": "stairs",
                "start": [0, 0, 0],
                "direction": "north",
                "height": 1,
                "block": "oak_stairs[facing=east]",
            },
            "operations[0]",
        )
        assert op.expanded[0].spec.block == B("oak_stairs[facing=east,half=bottom]")

    def test_bounds(self) -> None:
        op = build_operation(
            {
                "type": "stairs",
                "start": [0, 0, 0],
                "direction": "west",
                "height": 3,
                "block": "stone",
            },
            "operations[0]",
        )
        assert op.bounds() == AABB(Vec3(-3, 0, 0), Vec3(0, 5, 0))

    def test_invalid(self) -> None:
        with pytest.raises(BlueprintError):
            build_operation(
                {
                    "type": "stairs",
                    "start": [0, 0, 0],
                    "direction": "up",
                    "height": 1,
                    "block": "a",
                },
                "operations[0]",
            )
        with pytest.raises(BlueprintError):
            build_operation(
                {
                    "type": "stairs",
                    "start": [0, 0, 0],
                    "direction": "north",
                    "height": 1,
                    "headroom": 1,
                    "block": "a",
                },
                "operations[0]",
            )


class TestSpiralStairs:
    def test_ring_path_starts_east_and_is_adjacent(self) -> None:
        for radius in (1, 2, 3, 5):
            path = ring_path(radius, clockwise=True)
            assert path[0] == (radius, 0)
            assert path[1][1] > 0  # clockwise from above: east -> south
            for a, b in zip(path, path[1:] + path[:1], strict=True):
                assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1
            ccw = ring_path(radius, clockwise=False)
            assert ccw[0] == (radius, 0) and ccw[1][1] < 0

    @pytest.mark.parametrize("radius", [1, 2, 3, 5, 8])
    def test_treads_partition_the_disc_without_overlap(self, radius: int) -> None:
        treads = tread_cells(radius, clockwise=True)
        cells = [c for tread in treads for c in tread]
        assert len(cells) == len(set(cells))  # no (x, z) is used twice per turn
        assert (0, 0) not in cells
        assert all(
            tread[0] == ring for tread, ring in zip(treads, ring_path(radius, True), strict=True)
        )
        assert all(len(tread) >= 1 for tread in treads)
        expected = (2 * radius + 1) ** 2 if radius == 1 else None
        if radius >= 2:
            assert len(cells) > len(treads)  # inner cells were distributed
        else:
            assert len(cells) == 8 and expected == 9

    def test_no_vertical_stacking_between_consecutive_steps(self) -> None:
        volume = run(
            {
                "type": "spiral_stairs",
                "center": [0, 0, 0],
                "radius": 2,
                "height": 12,
                "block": "stone",
            }
        )
        columns: dict[tuple[int, int], list[int]] = {}
        for pos, state in volume:
            if state != AIR:
                columns.setdefault((pos.x, pos.z), []).append(pos.y)
        assert all(len(ys) == 1 for ys in columns.values())

    def test_rises_one_per_step_with_headroom(self) -> None:
        volume = run(
            solid([-4, 0, -4], [4, 12, 4]),
            {
                "type": "spiral_stairs",
                "center": [0, 0, 0],
                "radius": 2,
                "height": 10,
                "block": "stone_bricks",
                "column": "oak_log",
            },
        )
        path = ring_path(2, True)
        for i in range(10):
            ox, oz = path[i % len(path)]
            step = Vec3(ox, i, oz)
            assert volume.get(step) == B("stone_bricks")
            assert all(volume.get(step + Vec3(0, d, 0)) == AIR for d in (1, 2, 3))
        assert all(volume.get(Vec3(0, y, 0)) == B("oak_log") for y in range(10))

    def test_stairs_blocks_get_facing(self) -> None:
        volume = run(
            {
                "type": "spiral_stairs",
                "center": [0, 0, 0],
                "radius": 1,
                "height": 3,
                "block": "oak_stairs",
            }
        )
        assert volume.get(Vec3(1, 0, 0)).get("facing") in ("south", "east")
        assert volume.get(Vec3(1, 0, 0)).get("half") == "bottom"

    def test_radius_limit(self) -> None:
        with pytest.raises(BlueprintError):
            build_operation(
                {
                    "type": "spiral_stairs",
                    "center": [0, 0, 0],
                    "radius": 9,
                    "height": 1,
                    "block": "a",
                },
                "operations[0]",
            )


class TestRoof:
    def test_gable_layers_ridge_and_overhang(self) -> None:
        volume = run(
            {"type": "roof", "from": [0, 5, 0], "to": [6, 5, 4], "block": "dark_oak_stairs"}
        )
        assert volume.get(Vec3(-1, 5, -1)) == B("dark_oak_stairs[facing=south,half=bottom]")
        assert volume.get(Vec3(7, 5, 5)) == B("dark_oak_stairs[facing=north,half=bottom]")
        assert volume.get(Vec3(3, 6, 0)) == B("dark_oak_stairs[facing=south,half=bottom]")
        assert volume.get(Vec3(3, 7, 1)) == B("dark_oak_stairs[facing=south,half=bottom]")
        assert volume.get(Vec3(3, 7, 3)) == B("dark_oak_stairs[facing=north,half=bottom]")
        assert volume.get(Vec3(3, 8, 2)) == B("dark_oak_slab[type=bottom]")
        assert volume.bounds() == AABB(Vec3(-1, 5, -1), Vec3(7, 8, 5))
        assert volume.get(Vec3(3, 6, 2)) is None  # open underneath the ridge

    def test_gable_even_width_has_no_ridge_and_custom_ridge_block(self) -> None:
        volume = run(
            {
                "type": "roof",
                "from": [0, 0, 0],
                "to": [5, 0, 3],
                "overhang": 0,
                "block": "stone",
                "ridgeBlock": "gold_block",
            }
        )
        assert volume.get(Vec3(2, 1, 1)) == B("stone")
        assert volume.get(Vec3(2, 1, 2)) == B("stone")
        assert volume.bounds().max.y == 1
        odd = run(
            {
                "type": "roof",
                "from": [0, 0, 0],
                "to": [5, 0, 4],
                "overhang": 0,
                "block": "stone",
                "ridgeBlock": "gold_block",
            }
        )
        assert odd.get(Vec3(2, 2, 2)) == B("gold_block")

    def test_gable_walls(self) -> None:
        volume = run(
            {
                "type": "roof",
                "from": [0, 5, 0],
                "to": [6, 5, 4],
                "block": "dark_oak_stairs",
                "gable": "spruce_planks",
            }
        )
        assert volume.get(Vec3(0, 5, 2)) == B("spruce_planks")
        assert volume.get(Vec3(0, 6, 1)) == B("spruce_planks")
        assert volume.get(Vec3(0, 7, 2)) == B("spruce_planks")
        assert volume.get(Vec3(0, 7, 1)) == B("dark_oak_stairs[facing=south,half=bottom]")
        assert volume.get(Vec3(6, 6, 3)) == B("spruce_planks")
        assert volume.get(Vec3(3, 6, 2)) is None

    def test_ridge_axis_z(self) -> None:
        volume = run(
            {
                "type": "roof",
                "from": [0, 0, 0],
                "to": [4, 0, 6],
                "ridge": "x",
                "overhang": 0,
                "block": "stone",
            }
        )
        assert volume.get(Vec3(0, 0, 0)) == B("stone") and volume.get(Vec3(4, 0, 0)) == B("stone")
        assert volume.get(Vec3(2, 3, 3)) == B("stone")  # 7 rows along z -> ridge at layer 3

    def test_hip(self) -> None:
        volume = run(
            {
                "type": "roof",
                "from": [0, 5, 0],
                "to": [6, 5, 4],
                "style": "hip",
                "overhang": 0,
                "block": "dark_oak_stairs",
            }
        )
        assert volume.get(Vec3(0, 5, 2)) == B("dark_oak_stairs[facing=east,half=bottom]")
        assert volume.get(Vec3(6, 5, 2)) == B("dark_oak_stairs[facing=west,half=bottom]")
        assert volume.get(Vec3(3, 5, 0)) == B("dark_oak_stairs[facing=south,half=bottom]")
        assert volume.get(Vec3(3, 5, 4)) == B("dark_oak_stairs[facing=north,half=bottom]")
        assert volume.get(Vec3(2, 7, 2)) == B("dark_oak_slab[type=bottom]")
        assert volume.get(Vec3(4, 7, 2)) == B("dark_oak_slab[type=bottom]")
        assert volume.get(Vec3(1, 7, 2)) is None

    def test_requires_same_y(self) -> None:
        with pytest.raises(BlueprintError):
            build_operation(
                {"type": "roof", "from": [0, 0, 0], "to": [3, 1, 3], "block": "a"}, "operations[0]"
            )


class TestPillar:
    def test_base_and_cap(self) -> None:
        volume = run(
            {
                "type": "pillar",
                "position": [1, 0, 1],
                "height": 4,
                "block": "stone_bricks",
                "base": "chiseled_stone_bricks",
                "cap": "stone_brick_slab",
            }
        )
        assert volume.get(Vec3(1, 0, 1)) == B("chiseled_stone_bricks")
        assert volume.get(Vec3(1, 1, 1)) == B("stone_bricks")
        assert volume.get(Vec3(1, 3, 1)) == B("stone_brick_slab")
        assert len(volume) == 4

    def test_height_one_ignores_cap(self) -> None:
        volume = run(
            {
                "type": "pillar",
                "position": [0, 0, 0],
                "height": 1,
                "block": "stone",
                "base": "gold_block",
                "cap": "diamond_block",
            }
        )
        assert volume.get(Vec3(0, 0, 0)) == B("gold_block")


class TestDoorway:
    def test_single_door(self) -> None:
        volume = run(
            {"type": "wall", "from": [0, 0, 0], "to": [4, 0, 0], "height": 4, "block": "stone"},
            {"type": "doorway", "position": [2, 1, 0], "facing": "south", "door": "oak_door"},
        )
        assert volume.get(Vec3(2, 1, 0)) == B("oak_door[facing=south,half=lower,hinge=left]")
        assert volume.get(Vec3(2, 2, 0)) == B("oak_door[facing=south,half=upper,hinge=left]")
        assert volume.get(Vec3(2, 3, 0)) == B("stone")

    def test_opening_only_with_height(self) -> None:
        volume = run(
            {"type": "wall", "from": [0, 0, 0], "to": [0, 0, 6], "height": 5, "block": "stone"},
            {"type": "doorway", "position": [0, 1, 2], "facing": "east", "width": 3, "height": 3},
        )
        for z in (2, 3, 4):
            for y in (1, 2, 3):
                assert volume.get(Vec3(0, y, z)) == AIR
        assert volume.get(Vec3(0, 4, 3)) == B("stone")
        assert volume.get(Vec3(0, 1, 5)) == B("stone")

    def test_double_door_hinges(self) -> None:
        volume = run(
            {
                "type": "doorway",
                "position": [2, 1, 0],
                "facing": "south",
                "width": 2,
                "door": "spruce_door",
            }
        )
        left, right = volume.get(Vec3(2, 1, 0)), volume.get(Vec3(3, 1, 0))
        assert {left.get("hinge"), right.get("hinge")} == {"left", "right"}
        assert left.get("facing") == right.get("facing") == "south"

    def test_invalid(self) -> None:
        with pytest.raises(BlueprintError):
            build_operation(
                {"type": "doorway", "position": [0, 0, 0], "facing": "south", "door": "stone"},
                "operations[0]",
            )
        with pytest.raises(BlueprintError):
            build_operation(
                {
                    "type": "doorway",
                    "position": [0, 0, 0],
                    "facing": "south",
                    "width": 3,
                    "door": "oak_door",
                },
                "operations[0]",
            )


class TestWindow:
    def test_pane_connections_x(self) -> None:
        volume = run(
            {"type": "window", "position": [1, 2, 0], "axis": "x", "width": 3, "height": 2}
        )
        for x in (1, 2, 3):
            for y in (2, 3):
                assert volume.get(Vec3(x, y, 0)) == B("glass_pane[east=true,west=true]")
        assert len(volume) == 6

    def test_pane_connections_z_and_full_block(self) -> None:
        volume = run(
            {
                "type": "window",
                "position": [0, 2, 1],
                "axis": "z",
                "width": 2,
                "block": "iron_bars",
            },
            {"type": "window", "position": [5, 2, 1], "axis": "z", "block": "glass"},
        )
        assert volume.get(Vec3(0, 2, 1)) == B("iron_bars[north=true,south=true]")
        assert volume.get(Vec3(5, 2, 1)) == B("glass")

    def test_explicit_connection_kept(self) -> None:
        volume = run(
            {
                "type": "window",
                "position": [0, 0, 0],
                "axis": "x",
                "block": "glass_pane[east=false]",
            }
        )
        assert volume.get(Vec3(0, 0, 0)) == B("glass_pane[east=false,west=true]")


class TestValidation:
    def test_schema_and_semantics_accept_all(self) -> None:
        ops = [
            {
                "type": "stairs",
                "start": [0, 0, 0],
                "direction": "south",
                "height": 3,
                "block": "oak_stairs",
                "base": "oak_planks",
            },
            {
                "type": "spiral_stairs",
                "center": [10, 0, 10],
                "radius": 2,
                "height": 8,
                "palette": "p",
                "column": "oak_log",
            },
            {
                "type": "roof",
                "from": [0, 5, 0],
                "to": [6, 5, 4],
                "block": "dark_oak_stairs",
                "gable": "spruce_planks",
                "ridgeBlock": "dark_oak_slab",
            },
            {
                "type": "pillar",
                "position": [0, 0, 0],
                "height": 3,
                "block": "stone_bricks",
                "base": "stone",
                "cap": "stone_brick_slab",
            },
            {
                "type": "doorway",
                "position": [0, 1, 0],
                "facing": "south",
                "width": 2,
                "door": "oak_door",
            },
            {
                "type": "window",
                "position": [3, 2, 0],
                "axis": "x",
                "width": 2,
                "height": 2,
                "block": "glass_pane",
            },
        ]
        assert validate(blueprint(*ops, palettes={"p": [{"block": "stone_bricks"}]})) == []

    def test_extra_block_keys_are_validated(self) -> None:
        errors = validate(
            blueprint(
                {
                    "type": "stairs",
                    "start": [0, 0, 0],
                    "direction": "south",
                    "height": 3,
                    "block": "oak_stairs",
                    "base": "nope",
                },
                {
                    "type": "doorway",
                    "position": [0, 1, 0],
                    "facing": "south",
                    "door": "oak_door[facing=up]",
                },
                {"type": "window", "position": [3, 2, 0], "axis": "x", "block": "not_glass"},
            )
        )
        assert [e.path for e in errors] == [
            "operations[0].base",
            "operations[1].door",
            "operations[2].block",
        ]

    def test_block_palette_exclusive_for_composites(self) -> None:
        errors = validate(blueprint({"type": "pillar", "position": [0, 0, 0], "height": 3}))
        assert [e.message for e in errors] == ["Exactly one of 'block' or 'palette' must be given."]

    def test_roof_same_y(self) -> None:
        errors = validate(
            blueprint({"type": "roof", "from": [0, 0, 0], "to": [3, 1, 3], "block": "stone"})
        )
        assert errors[0].message == "'from' and 'to' must have the same y coordinate."
