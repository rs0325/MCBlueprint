import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation, build_operations
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse
AIR = B("air")
WALL = B("white_terracotta")


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


def room(**extra: Any) -> dict[str, Any]:
    return {
        "type": "room",
        "from": [0, 0, 0],
        "to": [10, 5, 8],
        "wall": "white_terracotta",
        **extra,
    }


class TestStructure:
    def test_floor_walls_ceiling_and_interior(self) -> None:
        volume = run(
            {"type": "fill", "from": [0, 0, 0], "to": [10, 5, 8], "block": "stone"},
            room(floor="oak_planks", ceiling="spruce_planks", corners="oak_log"),
        )
        assert volume.get(Vec3(5, 0, 4)) == B("oak_planks")  # floor layer is from.y
        assert volume.get(Vec3(0, 0, 0)) == B("oak_planks")  # under the walls too
        assert volume.get(Vec3(0, 3, 4)) == WALL and volume.get(Vec3(5, 5, 0)) == WALL
        assert volume.get(Vec3(0, 1, 0)) == B("oak_log[axis=y]") or volume.get(Vec3(0, 1, 0)) == B(
            "oak_log"
        )
        assert volume.get(Vec3(10, 5, 8)) in (B("oak_log[axis=y]"), B("oak_log"))
        assert volume.get(Vec3(5, 5, 4)) == B("spruce_planks")  # ceiling inside the walls
        assert volume.get(Vec3(5, 4, 4)) == AIR  # interior cleared
        assert volume.get(Vec3(1, 1, 1)) == AIR
        assert volume.bounds().min == Vec3(0, 0, 0) and volume.bounds().max == Vec3(10, 5, 8)

    def test_without_ceiling_interior_reaches_the_top(self) -> None:
        volume = run(
            {"type": "fill", "from": [0, 0, 0], "to": [10, 5, 8], "block": "stone"}, room()
        )
        assert volume.get(Vec3(5, 5, 4)) == AIR
        assert volume.get(Vec3(5, 0, 4)) == B("stone")  # no floor given: layer untouched

    def test_interior_false_keeps_contents(self) -> None:
        volume = run(
            {"type": "fill", "from": [0, 0, 0], "to": [10, 5, 8], "block": "stone"},
            room(interior=False),
        )
        assert volume.get(Vec3(5, 3, 4)) == B("stone")

    def test_thickness(self) -> None:
        volume = run(room(thickness=2))
        assert volume.get(Vec3(1, 2, 4)) == WALL and volume.get(Vec3(2, 2, 4)) == AIR
        assert volume.get(Vec3(9, 2, 4)) == WALL

    def test_palette_specs(self) -> None:
        ctx = ExecutionContext(BlockVolume(), random.Random(0), {})
        op = build_operation(room(wall={"palette": "p"}, floor={"palette": "p"}), "operations[0]")
        from mcblueprint.model import Palette, PaletteEntry

        ctx = ExecutionContext(
            BlockVolume(), random.Random(0), {"p": Palette("p", (PaletteEntry(B("stone")),))}
        )
        op.apply(ctx)
        assert ctx.volume.get(Vec3(0, 3, 0)) == B("stone")
        assert ctx.volume.get(Vec3(5, 0, 4)) == B("stone")

    @pytest.mark.parametrize(
        ("extra", "match"),
        [
            ({"to": [1, 5, 8]}, "at least 3 blocks wide"),
            ({"to": [10, 1, 8]}, "'to.y' must be at least"),
            ({"wall": 5}, "wall"),
            ({"interior": "yes"}, "interior"),
        ],
    )
    def test_invalid_shapes(self, extra: dict[str, Any], match: str) -> None:
        with pytest.raises(BlueprintError, match=match):
            build_operation(room(**extra), "operations[0]")

    def test_missing_wall(self) -> None:
        data = room()
        del data["wall"]
        with pytest.raises(BlueprintError, match="missing required 'wall'"):
            build_operation(data, "operations[0]")


class TestDoors:
    def test_centered_door_on_each_side(self) -> None:
        volume = run(
            room(
                doors=[
                    {"side": "north", "door": "oak_door"},
                    {"side": "south", "door": "oak_door"},
                    {"side": "east", "door": "oak_door"},
                    {"side": "west", "door": "oak_door"},
                ]
            )
        )
        # interior x 1..9 -> door at x 5; interior z 1..7 -> door at z 4; lower half at from.y + 1
        assert volume.get(Vec3(5, 1, 0)) == B("oak_door[facing=south,half=lower,hinge=left]")
        assert volume.get(Vec3(5, 2, 0)) == B("oak_door[facing=south,half=upper,hinge=left]")
        assert volume.get(Vec3(5, 1, 8)) == B("oak_door[facing=north,half=lower,hinge=left]")
        assert volume.get(Vec3(10, 1, 4)) == B("oak_door[facing=west,half=lower,hinge=left]")
        assert volume.get(Vec3(0, 1, 4)) == B("oak_door[facing=east,half=lower,hinge=left]")
        assert volume.get(Vec3(5, 3, 0)) == WALL

    def test_offset_and_double_door(self) -> None:
        volume = run(room(doors=[{"side": "north", "offset": 2, "width": 2, "door": "oak_door"}]))
        assert volume.get(Vec3(2, 1, 0)) == B("oak_door[facing=south,half=lower,hinge=right]")
        assert volume.get(Vec3(3, 1, 0)) == B("oak_door[facing=south,half=lower,hinge=left]")
        assert volume.get(Vec3(1, 1, 0)) == WALL and volume.get(Vec3(4, 1, 0)) == WALL

    def test_opening_without_door_and_taller(self) -> None:
        volume = run(room(doors=[{"side": "west", "width": 3, "height": 3}]))
        assert volume.get(Vec3(0, 1, 3)) == AIR and volume.get(Vec3(0, 3, 5)) == AIR
        assert volume.get(Vec3(0, 4, 4)) == WALL

    def test_door_goes_through_thick_wall_with_arch(self) -> None:
        volume = run(
            room(
                thickness=2,
                doors=[
                    {
                        "side": "south",
                        "width": 3,
                        "height": 3,
                        "arch": {
                            "style": "round",
                            "block": "stone_bricks",
                            "trim": "stone_brick_stairs",
                        },
                    }
                ],
            )
        )
        # x 2..8 usable -> width 3 centred at 4..6; wall layers z 7 and 8
        for z in (7, 8):
            assert volume.get(Vec3(5, 1, z)) == AIR and volume.get(Vec3(5, 3, z)) == AIR
            assert volume.get(Vec3(4, 4, z)) == AIR
            assert volume.get(Vec3(4, 5, z)) == B("stone_brick_stairs[facing=west,half=top]")
            assert volume.get(Vec3(5, 5, z)) == B("stone_bricks")
            assert volume.get(Vec3(3, 2, z)) == B("stone_bricks")

    @pytest.mark.parametrize(
        ("door", "match"),
        [
            ({"side": "north", "offset": 0}, "does not fit.*usable range 1..9"),
            ({"side": "east", "offset": 7, "width": 2}, "does not fit.*usable range 1..7"),
            ({"side": "north", "height": 6}, "reaches row 6 above the floor but only 5"),
            ({"side": "north", "width": 3, "door": "oak_door"}, "width 1 or 2"),
            ({"side": "north", "door": "stone"}, "must be a door block"),
            ({"side": "up"}, "side"),
            ({"side": "north", "offset": -1}, "offset"),
        ],
    )
    def test_invalid_doors(self, door: dict[str, Any], match: str) -> None:
        with pytest.raises(BlueprintError, match=match):
            build_operation(room(doors=[door]), "operations[0]")

    def test_arch_ring_must_fit_below_the_top(self) -> None:
        # width 3 round arch: rise 1 -> opening top row 4, ring row 5 = wall top: ok
        build_operation(
            room(doors=[{"side": "north", "width": 3, "height": 3, "arch": {"block": "stone"}}]),
            "operations[0]",
        )
        with pytest.raises(BlueprintError, match="only 4 rows"):
            build_operation(
                room(
                    doors=[{"side": "north", "width": 3, "height": 4, "arch": {"block": "stone"}}]
                ),
                "operations[0]",
            )

    def test_with_ceiling_the_opening_stays_below_it(self) -> None:
        with pytest.raises(BlueprintError, match="only 4 rows"):
            build_operation(
                room(ceiling="stone", doors=[{"side": "north", "height": 5}]), "operations[0]"
            )


class TestWindows:
    def test_default_sill_and_pane_connections(self) -> None:
        volume = run(room(windows=[{"side": "north"}, {"side": "east"}]))
        assert volume.get(Vec3(5, 2, 0)) == B("glass_pane[east=true,west=true]")
        assert volume.get(Vec3(5, 1, 0)) == WALL and volume.get(Vec3(5, 3, 0)) == WALL
        assert volume.get(Vec3(10, 2, 4)) == B("glass_pane[north=true,south=true]")

    def test_count_and_spacing_centred(self) -> None:
        volume = run(room(windows=[{"side": "south", "count": 3, "spacing": 2, "height": 2}]))
        # total 3 + 4 = 7 in x 1..9 -> starts at 2, 5, 8
        for x in (2, 5, 8):
            assert volume.get(Vec3(x, 2, 8)).id.endswith("glass_pane")
            assert volume.get(Vec3(x, 3, 8)).id.endswith("glass_pane")
        for x in (1, 3, 4, 6, 7, 9):
            assert volume.get(Vec3(x, 2, 8)) == WALL

    def test_offset_sill_and_block(self) -> None:
        volume = run(
            room(windows=[{"side": "west", "offset": 1, "sill": 3, "width": 2, "block": "glass"}])
        )
        assert volume.get(Vec3(0, 3, 1)) == B("glass") and volume.get(Vec3(0, 3, 2)) == B("glass")
        assert volume.get(Vec3(0, 2, 1)) == WALL and volume.get(Vec3(0, 3, 3)) == WALL

    def test_window_goes_through_thick_wall(self) -> None:
        volume = run(room(thickness=2, windows=[{"side": "east"}, {"side": "north"}]))
        assert volume.get(Vec3(9, 2, 4)).id.endswith("glass_pane")
        assert volume.get(Vec3(10, 2, 4)).id.endswith("glass_pane")
        assert volume.get(Vec3(5, 2, 0)).id.endswith("glass_pane")
        assert volume.get(Vec3(5, 2, 1)).id.endswith("glass_pane")

    def test_arch_window(self) -> None:
        volume = run(
            room(
                windows=[
                    {
                        "side": "north",
                        "width": 3,
                        "height": 1,
                        "arch": {"style": "pointed", "block": "stone_bricks"},
                    }
                ]
            )
        )
        # sill 2, height 1, rise 2 -> panes on rows 2..4 (apex), ring on row 5 = wall top
        assert volume.get(Vec3(4, 2, 0)).id.endswith("glass_pane")
        assert volume.get(Vec3(5, 4, 0)).id.endswith("glass_pane")
        assert volume.get(Vec3(4, 4, 0)) == B("stone_bricks")
        assert volume.get(Vec3(5, 5, 0)) == B("stone_bricks")
        assert volume.get(Vec3(3, 2, 0)) == B("stone_bricks")

    def test_door_wins_over_window(self) -> None:
        volume = run(room(windows=[{"side": "north", "sill": 1}], doors=[{"side": "north"}]))
        assert volume.get(Vec3(5, 1, 0)) == AIR

    def test_windows_must_fit(self) -> None:
        with pytest.raises(BlueprintError, match="does not fit"):
            build_operation(room(windows=[{"side": "north", "count": 4, "spacing": 3}]), "op")
        with pytest.raises(BlueprintError, match="only 5 rows"):
            build_operation(room(windows=[{"side": "north", "sill": 5, "height": 2}]), "op")


class TestDepth:
    def test_doorway_depth_follows_facing(self) -> None:
        volume = run(
            {"type": "fill", "from": [0, 0, 0], "to": [4, 4, 4], "block": "stone"},
            {
                "type": "doorway",
                "position": [2, 1, 4],
                "facing": "north",
                "depth": 3,
                "door": "oak_door",
            },
        )
        assert volume.get(Vec3(2, 1, 4)) == B("oak_door[facing=north,half=lower,hinge=left]")
        assert volume.get(Vec3(2, 1, 3)) == AIR and volume.get(Vec3(2, 2, 2)) == AIR
        assert volume.get(Vec3(2, 1, 1)) == B("stone")

    def test_doorway_arch_spans_depth(self) -> None:
        volume = run(
            {
                "type": "doorway",
                "position": [0, 0, 5],
                "facing": "north",
                "width": 3,
                "depth": 2,
                "arch": {"style": "flat", "block": "stone_bricks"},
            }
        )
        for z in (4, 5):
            assert volume.get(Vec3(1, 2, z)) == B("stone_bricks")
            assert volume.get(Vec3(-1, 0, z)) == B("stone_bricks")
        assert volume.get(Vec3(1, 2, 3)) is None

    def test_window_depth_extends_positive(self) -> None:
        volume = run({"type": "window", "position": [0, 0, 0], "axis": "z", "depth": 2})
        assert volume.get(Vec3(0, 0, 0)).id.endswith("glass_pane")
        assert volume.get(Vec3(1, 0, 0)).id.endswith("glass_pane")
        assert volume.get(Vec3(2, 0, 0)) is None


class TestValidation:
    def test_valid_room_blueprint(self) -> None:
        assert (
            validate(
                blueprint(
                    room(
                        wall={"palette": "p"},
                        floor="oak_planks",
                        doors=[{"side": "north", "door": "oak_door"}],
                        windows=[{"side": "south", "arch": {"block": "stone_bricks"}}],
                    ),
                    palettes={"p": [{"block": "minecraft:stone_bricks", "weight": 1}]},
                )
            )
            == []
        )

    def test_unknown_blocks_and_palettes_are_reported(self) -> None:
        errors = validate(
            blueprint(
                room(
                    wall={"palette": "nope"},
                    floor="no_such_planks",
                    doors=[{"side": "north", "door": "oak_door", "arch": {"block": "bad"}}],
                    windows=[{"side": "south", "block": "bad_pane"}],
                )
            )
        )
        assert {e.path for e in errors} == {
            "operations[0].wall.palette",
            "operations[0].floor",
            "operations[0].doors[0].arch.block",
            "operations[0].windows[0].block",
        }

    def test_schema_rejects_unknown_keys(self) -> None:
        errors = validate(blueprint(room(doors=[{"side": "north", "y": 3}])))
        assert errors and "doors" in errors[0].path

    def test_layout_errors_surface_as_validation_errors(self) -> None:
        errors = validate(blueprint(room(doors=[{"side": "north", "offset": 0}])))
        assert any("does not fit" in e.message for e in errors)
