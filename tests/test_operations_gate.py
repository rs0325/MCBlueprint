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
STONE = B("stone_bricks")


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


def gate(**extra: Any) -> dict[str, Any]:
    data = {
        "type": "gate",
        "position": [0, 0, 0],
        "axis": "x",
        "width": 3,
        "height": 4,
        "block": "stone_bricks",
        **extra,
    }
    return {k: v for k, v in data.items() if v is not None}


class TestBody:
    def test_body_passage_and_walkway(self) -> None:
        # width 3 round: rise 1 -> passage rows 1..5, crown 6, top 1 -> walkway row 7
        volume = run(gate())
        assert volume.get(Vec3(-3, 1, 0)) == STONE and volume.get(Vec3(3, 7, 2)) == STONE
        assert volume.get(Vec3(-4, 1, 0)) is None and volume.get(Vec3(0, 8, 1)) is None
        for z in range(3):
            assert volume.get(Vec3(0, 1, z)) == AIR and volume.get(Vec3(1, 4, z)) == AIR
            assert volume.get(Vec3(0, 5, z)) == AIR
            assert volume.get(Vec3(0, 6, z)) == STONE  # crown of the arch
        assert volume.get(Vec3(0, 0, 0)) is None  # the ground layer is untouched
        bounds = volume.bounds()
        assert bounds.min == Vec3(-3, 1, 0) and bounds.max == Vec3(3, 7, 2)

    def test_depth_jamb_top_and_axis_z(self) -> None:
        volume = run(gate(axis="z", depth=2, jamb=1, top=2, position=[5, 2, 5]))
        # body: z 3..7, x 5..6, rows 3 .. 2 + 4 + 1 + 1 + 2 = 10
        assert volume.get(Vec3(5, 3, 3)) == STONE and volume.get(Vec3(6, 10, 7)) == STONE
        assert volume.get(Vec3(5, 3, 2)) is None and volume.get(Vec3(7, 3, 5)) is None
        assert volume.get(Vec3(5, 3, 5)) == AIR and volume.get(Vec3(6, 7, 5)) == AIR

    def test_arch_options_and_trim(self) -> None:
        volume = run(
            gate(
                width=5,
                height=5,
                jamb=3,
                arch={
                    "style": "pointed",
                    "block": "bricks",
                    "trim": "brick_stairs",
                    "thickness": 2,
                },
            )
        )
        # pointed width 5: rise 4 -> passage 1..9, ring rows 10 (crown) and 11 (2 thick)
        assert volume.get(Vec3(0, 9, 0)) == AIR and volume.get(Vec3(0, 10, 0)) == B("bricks")
        assert volume.get(Vec3(-3, 1, 0)) == B("bricks")  # ring is 2 thick -> inner jamb column
        assert volume.get(Vec3(-5, 1, 0)) == STONE
        assert any(
            state.id == "minecraft:brick_stairs"
            for _, state in volume
            if state.id.endswith("stairs")
        )

    def test_ring_must_fit_in_jamb(self) -> None:
        with pytest.raises(BlueprintError, match="does not fit in the jambs"):
            build_operation(gate(jamb=1, arch={"thickness": 2}), "operations[0]")


class TestFittings:
    def test_battlement_front_and_back_only(self) -> None:
        volume = run(gate(battlement={"spacing": 1}))
        # walkway row 7: parapet on z=0 and z=2 at row 8, merlons at row 9 on every other x
        for x in range(-3, 4):
            assert volume.get(Vec3(x, 8, 0)) == STONE and volume.get(Vec3(x, 8, 2)) == STONE
            assert volume.get(Vec3(x, 8, 1)) is None
        assert volume.get(Vec3(-3, 9, 0)) == STONE and volume.get(Vec3(-2, 9, 0)) is None
        assert volume.get(Vec3(-1, 9, 2)) == STONE

    def test_portcullis_in_the_middle_layer(self) -> None:
        volume = run(gate(width=3, height=5, portcullis={"height": 2}))
        # width 3 round: rise 1 -> passage rows 1..6; bars on rows 5 and 6 at z=1 only
        bars = B("iron_bars[east=true,west=true]")
        assert volume.get(Vec3(0, 6, 1)) == bars and volume.get(Vec3(0, 5, 1)) == bars
        assert volume.get(Vec3(-1, 5, 1)) == B("iron_bars[east=true,west=false]")
        assert volume.get(Vec3(0, 4, 1)) == AIR and volume.get(Vec3(0, 6, 0)) == AIR
        assert volume.get(Vec3(0, 6, 2)) == AIR

    def test_portcullis_must_leave_headroom(self) -> None:
        with pytest.raises(BlueprintError, match="leave 2 clear rows"):
            build_operation(gate(height=3, portcullis={"height": 2}), "operations[0]")

    def test_door_in_front(self) -> None:
        volume = run(gate(width=2, door="oak_door"))
        assert volume.get(Vec3(0, 1, 0)) == B("oak_door[facing=south,half=lower,hinge=right]")
        assert volume.get(Vec3(1, 2, 0)) == B("oak_door[facing=south,half=upper,hinge=left]")
        assert volume.get(Vec3(0, 1, 1)) == AIR
        with pytest.raises(BlueprintError, match="width 1 or 2"):
            build_operation(gate(width=3, door="oak_door"), "operations[0]")
        with pytest.raises(BlueprintError, match="door block"):
            build_operation(gate(width=2, door="stone"), "operations[0]")


class TestTowers:
    def test_towers_flank_the_body_with_walkway_openings(self) -> None:
        volume = run(gate(width=3, height=4, battlement=True, towers={"height": 12}))
        # body x -3..3; towers size 7 centred at x = -7 and 7, z centred on 1 (z -2..4)
        assert volume.get(Vec3(-10, 1, 1)) == STONE and volume.get(Vec3(10, 12, 4)) == STONE
        assert volume.get(Vec3(-7, 5, 1)) == AIR  # tower interior
        assert volume.get(Vec3(-7, 7, 1)) == STONE  # storey floor level with the walkway (row 7)
        assert volume.get(Vec3(-4, 8, 1)) == AIR and volume.get(Vec3(-4, 9, 1)) == AIR  # opening
        assert volume.get(Vec3(-4, 8, 0)) == STONE  # rest of the tower wall stays
        assert volume.get(Vec3(4, 8, 1)) == AIR
        # the gate's battlement is reused by the towers (roof platform row 13, parapet 14)
        assert volume.get(Vec3(-11, 14, 1)) == STONE

    def test_small_towers_have_no_stairs_and_passthrough(self) -> None:
        volume = run(gate(towers={"size": 5, "windows": {"sides": ["north"], "height": 1}}))
        assert volume.get(Vec3(-6, 2, -1)).id.endswith("glass_pane")
        assert volume.get(Vec3(-6, 3, 1)) == AIR  # no staircase in the centre

    @pytest.mark.parametrize(
        ("towers", "match"),
        [
            ({"size": 6}, "odd"),
            ({"height": 4}, "reach above the walkway"),
            ({"roof": "cone"}, "unknown key"),
            ("yes", "towers"),
        ],
    )
    def test_invalid_towers(self, towers: Any, match: str) -> None:
        with pytest.raises(BlueprintError, match=match):
            build_operation(gate(towers=towers), "operations[0]")


class TestValidation:
    def test_valid_with_palettes(self) -> None:
        data = blueprint(
            gate(
                palette="p",
                block=None,
                arch={"palette": "p", "trim": "stone_brick_stairs"},
                battlement={"block": {"palette": "p"}},
                towers={"wall": {"palette": "p"}, "battlement": {"block": "stone"}},
                portcullis={"block": "iron_bars"},
            ),
            palettes={"p": [{"block": "minecraft:stone_bricks", "weight": 1}]},
        )
        assert validate(data) == []

    def test_bad_blocks_reported(self) -> None:
        errors = validate(
            blueprint(
                gate(
                    arch={"block": "bad_ring", "trim": "bad_trim"},
                    battlement={"block": {"palette": "nope"}},
                    portcullis={"block": "bad_bars"},
                    towers={"wall": "bad_wall"},
                    door="bad_door",
                    width=2,
                )
            )
        )
        assert {e.path for e in errors} == {
            "operations[0].arch.block",
            "operations[0].arch.trim",
            "operations[0].battlement.block.palette",
            "operations[0].portcullis.block",
            "operations[0].towers.wall",
            "operations[0].door",
        }

    def test_schema_rejects_unknown_keys(self) -> None:
        errors = validate(blueprint(gate(moat=True)))
        assert errors and errors[0].path.startswith("operations[0]")
