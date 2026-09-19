import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation, build_operations
from mcblueprint.operations.shapes import disc_cells
from mcblueprint.operations.tower import merlon_cells, square_ring
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse
AIR = B("air")
WALL = B("stone_bricks")
FLOOR = B("spruce_planks")


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


def tower(**extra: Any) -> dict[str, Any]:
    """Round 6-radius tower; a ``None`` value removes that key (e.g. ``radius=None``)."""
    data = {
        "type": "tower",
        "position": [0, 0, 0],
        "radius": 6,
        "height": 20,
        "wall": "stone_bricks",
        "floor": "spruce_planks",
        **extra,
    }
    return {k: v for k, v in data.items() if v is not None}


class TestHelpers:
    def test_square_ring(self) -> None:
        ring = square_ring(2)
        assert len(ring) == 16
        assert (2, 0) in ring and (-2, -2) in ring and (1, 1) not in ring

    def test_merlons_alternate_from_east(self) -> None:
        ring = disc_cells(3, "hollow")
        merlons = merlon_cells(ring, 1)
        assert merlons[0] == (3, 0)
        assert len(merlons) == (len(ring) + 1) // 2
        assert len(merlon_cells(ring, 0)) == len(ring)


class TestRoundTower:
    def test_shell_floors_platform(self) -> None:
        volume = run(tower(floors=5, stairs=False))
        # ground floor covers the whole disc, walls from y=1, interior empty
        assert volume.get(Vec3(0, 0, 0)) == FLOOR and volume.get(Vec3(6, 0, 0)) == FLOOR
        assert volume.get(Vec3(6, 1, 0)) == WALL and volume.get(Vec3(6, 20, 0)) == WALL
        assert volume.get(Vec3(0, 1, 0)) == AIR and volume.get(Vec3(4, 12, 0)) == AIR
        # storey floors at 5, 10, 15 (20 would leave no room below the platform)
        for y in (5, 10, 15):
            assert volume.get(Vec3(0, y, 0)) == FLOOR
            assert volume.get(Vec3(6, y, 0)) == WALL  # the wall ring stays wall
        assert volume.get(Vec3(0, 20, 0)) == AIR
        # roof platform one row above the walls, overhanging by one
        assert volume.get(Vec3(0, 21, 0)) == WALL and volume.get(Vec3(7, 21, 0)) == WALL
        assert volume.get(Vec3(7, 20, 0)) is None
        assert volume.get(Vec3(0, 22, 0)) is None
        assert volume.bounds().max.y == 21

    def test_stairs_reach_platform_and_cut_floors(self) -> None:
        volume = run(tower(floors=5))
        stairs = [
            pos
            for pos, state in volume
            if state == FLOOR and pos.y in range(1, 21) and abs(pos.x) <= 2
        ]
        assert stairs, "spiral stairs of floor blocks around the centre"
        assert max(pos.y for pos in stairs) == 20
        # a hole in each storey floor above the stairwell
        for y in (5, 10, 15):
            assert any(volume.get(Vec3(x, y, z)) == AIR for x in range(-2, 3) for z in range(-2, 3))
        assert volume.get(Vec3(0, 21, 0)) == WALL  # the platform itself is intact at the centre

    def test_stairs_options(self) -> None:
        volume = run(
            tower(
                stairs={
                    "radius": 3,
                    "block": "stone_bricks",
                    "column": "oak_log",
                    "turn": "counterclockwise",
                }
            )
        )
        assert volume.get(Vec3(0, 1, 0)) == B("oak_log") or volume.get(Vec3(0, 1, 0)) == B(
            "oak_log[axis=y]"
        )
        assert volume.get(Vec3(0, 21, 0)) in (B("oak_log"), B("oak_log[axis=y]"))
        assert volume.get(Vec3(3, 1, 0)) == WALL  # first step at radius 3, east

    def test_battlement(self) -> None:
        volume = run(tower(stairs=False, battlement={"spacing": 1}))
        assert volume.get(Vec3(7, 22, 0)) == WALL  # parapet ring
        assert volume.get(Vec3(0, 22, 0)) is None
        assert volume.get(Vec3(7, 23, 0)) == WALL  # first merlon is east
        merlons = [pos for pos, _ in volume if pos.y == 23]
        parapet = [pos for pos, _ in volume if pos.y == 22]
        assert len(merlons) == (len(parapet) + 1) // 2
        assert volume.bounds().max.y == 23

    def test_battlement_block_and_solid(self) -> None:
        volume = run(tower(stairs=False, battlement={"block": "deepslate_bricks", "spacing": 0}))
        assert volume.get(Vec3(7, 22, 0)) == B("deepslate_bricks")
        assert len([1 for pos, _ in volume if pos.y == 23]) == len(
            [1 for pos, _ in volume if pos.y == 22]
        )

    def test_windows_and_door(self) -> None:
        volume = run(
            tower(
                floors=5,
                stairs=False,
                windows={"sill": 2, "height": 2},
                door={"side": "north", "block": "spruce_door"},
            )
        )
        pane_x = B("glass_pane[east=true,west=true]")
        pane_z = B("glass_pane[north=true,south=true]")
        for y in (0, 5, 10, 15):
            assert (
                volume.get(Vec3(0, y + 2, 6)) == pane_x and volume.get(Vec3(0, y + 3, 6)) == pane_x
            )
            assert (
                volume.get(Vec3(6, y + 2, 0)) == pane_z and volume.get(Vec3(-6, y + 3, 0)) == pane_z
            )
        # no window above the door on the ground floor; windows above on the upper floors
        assert volume.get(Vec3(0, 3, -6)) == WALL
        assert volume.get(Vec3(0, 7, -6)) == pane_x
        assert volume.get(Vec3(0, 1, -6)) == B("spruce_door[facing=south,half=lower,hinge=left]")
        assert volume.get(Vec3(0, 2, -6)) == B("spruce_door[facing=south,half=upper,hinge=left]")

    def test_window_sides_and_arch(self) -> None:
        volume = run(
            tower(
                stairs=False,
                windows={
                    "sides": ["east"],
                    "width": 3,
                    "arch": {"style": "round", "block": "bricks"},
                },
            )
        )
        assert volume.get(Vec3(6, 2, 0)).id.endswith("glass_pane")
        assert volume.get(Vec3(6, 3, 0)).id.endswith("glass_pane")  # rise of a width-3 round arch
        assert volume.get(Vec3(6, 4, 0)) == B("bricks")
        assert volume.get(Vec3(0, 2, 6)) == WALL  # other sides untouched

    def test_short_top_storey_gets_no_window(self) -> None:
        volume = run(tower(height=17, floors=5, stairs=False, windows={"height": 2}))
        assert volume.get(Vec3(0, 15, 0)) == FLOOR  # 15 <= 17 - 2
        assert volume.get(Vec3(6, 17, 0)) == WALL and volume.get(Vec3(6, 18, 0)) == WALL
        assert volume.get(Vec3(6, 12, 0)).id.endswith("glass_pane")

    def test_door_arch_and_width(self) -> None:
        volume = run(
            tower(
                stairs=False,
                door={
                    "side": "east",
                    "width": 3,
                    "height": 3,
                    "arch": {"block": "bricks", "trim": "brick_stairs"},
                },
            )
        )
        for z in (-1, 0, 1):
            assert volume.get(Vec3(6, 1, z)) == AIR and volume.get(Vec3(6, 3, z)) == AIR
        assert volume.get(Vec3(6, 4, -1)) == AIR
        assert volume.get(Vec3(6, 5, -1)) == B("brick_stairs[facing=north,half=top]")
        assert volume.get(Vec3(6, 5, 0)) == B("bricks")


class TestSquareTower:
    def test_square_shell(self) -> None:
        volume = run(tower(shape="square", size=9, radius=None, floors=4, battlement=True))
        assert volume.get(Vec3(4, 1, 4)) == WALL and volume.get(Vec3(-4, 10, 0)) == WALL
        assert volume.get(Vec3(3, 10, 3)) == AIR
        assert volume.get(Vec3(2, 4, 2)) == FLOOR and volume.get(Vec3(4, 4, 4)) == WALL
        assert volume.get(Vec3(5, 21, 5)) == WALL  # overhanging platform
        assert volume.get(Vec3(5, 22, 5)) == WALL and volume.get(Vec3(4, 22, 4)) is None
        assert volume.get(Vec3(5, 23, 0)) == WALL  # merlon east
        assert volume.bounds().min.x == -5 and volume.bounds().max.x == 5

    def test_square_windows_and_door(self) -> None:
        volume = run(
            tower(
                shape="square", size=9, radius=None, stairs=False, windows={}, door={"side": "west"}
            )
        )
        assert volume.get(Vec3(0, 2, -4)).id.endswith("glass_pane")
        assert volume.get(Vec3(4, 2, 0)).id.endswith("glass_pane")
        assert volume.get(Vec3(-4, 1, 0)) == AIR and volume.get(Vec3(-4, 2, 0)) == AIR


class TestErrors:
    @pytest.mark.parametrize(
        ("extra", "match"),
        [
            ({"radius": 2}, "radius of at least 3"),
            ({"stairs": {"radius": 5}}, "at most 4"),
            ({"height": 2}, "height"),
            ({"floors": 2}, "floors"),
            ({"shape": "square", "size": 8, "radius": None}, "odd"),
            ({"shape": "square", "radius": 6}, "'radius' is only for round"),
            ({"size": 9}, "'size' is only for square"),
            ({"windows": {"sill": 4, "height": 2}, "floors": 5}, "needs 5 rows above a floor"),
            ({"windows": {"sides": ["up"]}}, "sides"),
            ({"door": {"block": "stone"}}, "door block"),
            ({"door": {"width": 3, "block": "oak_door"}}, "width 1 or 2"),
            ({"stairs": "yes"}, "stairs"),
            ({"wall": None}, "missing required 'wall'"),
        ],
    )
    def test_invalid(self, extra: dict[str, Any], match: str) -> None:
        with pytest.raises(BlueprintError, match=match):
            build_operation(tower(**extra), "operations[0]")

    def test_stairs_false_allows_small_radius(self) -> None:
        build_operation(tower(radius=2, stairs=False), "operations[0]")


class TestValidation:
    def test_valid_with_palettes(self) -> None:
        assert (
            validate(
                blueprint(
                    tower(
                        wall={"palette": "p"},
                        floor={"palette": "p"},
                        stairs={"block": {"palette": "p"}},
                        battlement={"block": {"palette": "p"}},
                        windows={"arch": {"palette": "p"}},
                        door={"block": "oak_door", "arch": {"block": "bricks"}},
                    ),
                    palettes={"p": [{"block": "minecraft:stone_bricks", "weight": 1}]},
                )
            )
            == []
        )

    def test_reports_bad_blocks_and_palettes(self) -> None:
        errors = validate(
            blueprint(
                tower(
                    wall={"palette": "nope"},
                    floor="bad_floor",
                    stairs={"block": "bad_step", "column": "oak_log"},
                    battlement={"block": {"palette": "nope2"}},
                    windows={"block": "bad_pane", "arch": {"block": "bricks", "trim": "bad_trim"}},
                    door={"block": "oak_door", "arch": {"block": "bad_ring"}},
                )
            )
        )
        assert {e.path for e in errors} == {
            "operations[0].wall.palette",
            "operations[0].floor",
            "operations[0].stairs.block",
            "operations[0].battlement.block.palette",
            "operations[0].windows.block",
            "operations[0].windows.arch.trim",
            "operations[0].door.arch.block",
        }

    def test_schema_rejects_unknown_keys(self) -> None:
        errors = validate(blueprint(tower(roof="cone")))
        assert errors and errors[0].path.startswith("operations[0]")
