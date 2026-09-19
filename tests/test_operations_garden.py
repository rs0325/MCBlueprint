import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Palette, PaletteEntry, Vec3
from mcblueprint.operations import ExecutionContext, build_operation, build_operations
from mcblueprint.operations.garden import channel_indices, connected_state
from mcblueprint.support import check_support
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse
AIR = B("air")
FARMLAND = B("farmland[moisture=7]")
WATER = B("water")
WHEAT = B("wheat[age=7]")


def run(*ops: dict[str, Any], palettes: dict[str, Palette] | None = None) -> BlockVolume:
    ctx = ExecutionContext(BlockVolume(), random.Random(0), palettes or {})
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


def garden(**extra: Any) -> dict[str, Any]:
    data = {"type": "garden", "from": [0, 0, 0], "to": [12, 0, 8], **extra}
    return {k: v for k, v in data.items() if v is not None}


class TestHelpers:
    def test_channel_indices(self) -> None:
        assert channel_indices(9, 4) == [4]
        assert channel_indices(14, 4) == [4, 9]
        assert channel_indices(15, 4) == [4, 9, 14]
        assert channel_indices(3, 4) == [2]  # too short for the pattern: last row
        assert channel_indices(1, 4) == [] and channel_indices(9, 0) == []
        # every row is within `spacing` of a channel
        for count in range(2, 30):
            channels = channel_indices(count, 3)
            assert all(min(abs(i - c) for c in channels) <= 3 for i in range(count))

    def test_connected_state(self) -> None:
        joined = {"north": True, "south": True, "east": False, "west": False}
        assert connected_state(B("oak_fence"), joined) == B(
            "oak_fence[east=false,north=true,south=true,west=false]"
        )
        wall = connected_state(B("cobblestone_wall"), joined)
        assert wall.get("north") == "low" and wall.get("up") == "false"
        corner = connected_state(B("cobblestone_wall"), {**joined, "south": False, "east": True})
        assert corner.get("up") == "true"
        assert connected_state(B("stone"), joined) == B("stone")


class TestFarm:
    def test_unfenced_farm_covers_the_rectangle(self) -> None:
        volume = run(garden(**{"to": [8, 0, 8]}))
        # rows along x (square -> x); channels at z 4 (9 rows)
        for x in range(9):
            assert volume.get(Vec3(x, 0, 0)) == FARMLAND and volume.get(Vec3(x, 1, 0)) == WHEAT
            assert volume.get(Vec3(x, 0, 4)) == WATER and volume.get(Vec3(x, 1, 4)) == AIR
        assert volume.get(Vec3(4, 2, 4)) == AIR
        assert volume.get(Vec3(9, 0, 0)) is None
        assert check_support(volume) == []

    def test_fenced_farm_with_gate_and_lanterns(self) -> None:
        volume = run(garden(fence="oak_fence", gate={"side": "south"}, lanterns={"spacing": 4}))
        grass = B("grass_block")
        # ring: grass under the fence, farmland inside; 7 inner rows -> channel at index 4 (z 5)
        assert volume.get(Vec3(0, 0, 0)) == grass and volume.get(Vec3(6, 0, 0)) == grass
        assert volume.get(Vec3(1, 0, 1)) == FARMLAND and volume.get(Vec3(1, 1, 1)) == WHEAT
        assert volume.get(Vec3(6, 0, 5)) == WATER
        assert volume.get(Vec3(0, 1, 0)) == B(
            "oak_fence[east=true,north=false,south=true,west=false]"
        )
        assert volume.get(Vec3(6, 1, 0)) == B(
            "oak_fence[east=true,north=false,south=false,west=true]"
        )
        assert volume.get(Vec3(6, 1, 8)) == B("oak_fence_gate[facing=north]")
        assert volume.get(Vec3(0, 2, 0)) == B("lantern") and volume.get(Vec3(4, 2, 0)) == B(
            "lantern"
        )
        assert volume.get(Vec3(1, 2, 0)) == AIR
        assert check_support(volume) == []

    def test_crop_rows_and_water_spacing(self) -> None:
        volume = run(garden(**{"to": [6, 0, 10]}, crop="carrots[age=7]", rows="z", water=2))
        # rows along z: channels are columns x = 2, 5 (7 columns, spacing 2)
        assert volume.get(Vec3(2, 0, 3)) == WATER and volume.get(Vec3(5, 0, 3)) == WATER
        assert volume.get(Vec3(3, 0, 3)) == FARMLAND and volume.get(Vec3(3, 1, 3)) == B(
            "carrots[age=7]"
        )

    def test_no_water(self) -> None:
        volume = run(garden(water=0))
        assert not any(state == WATER for _, state in volume)


class TestFlowers:
    def test_plants_from_palette(self) -> None:
        palette = Palette("p", (PaletteEntry(B("poppy")), PaletteEntry(B("air"))))
        volume = run(
            garden(style="flowers", plants={"palette": "p"}, fence="cobblestone_wall"),
            palettes={"p": palette},
        )
        plants = {volume.get(Vec3(x, 1, z)) for x in range(1, 12) for z in range(1, 8)}
        assert plants == {B("poppy"), AIR}
        assert volume.get(Vec3(1, 0, 1)) == B("grass_block")
        assert volume.get(Vec3(0, 1, 4)).id.endswith("cobblestone_wall")
        assert check_support(volume) == []

    def test_single_plant_and_ground(self) -> None:
        volume = run(garden(style="flowers", plants="dandelion", ground="moss_block"))
        assert volume.get(Vec3(3, 1, 3)) == B("dandelion")
        assert volume.get(Vec3(3, 0, 3)) == B("moss_block")

    def test_flowers_need_plants(self) -> None:
        with pytest.raises(BlueprintError, match="'plants'"):
            build_operation(garden(style="flowers"), "operations[0]")


class TestErrors:
    @pytest.mark.parametrize(
        ("extra", "match"),
        [
            ({"to": [12, 1, 8]}, "same y"),
            ({"to": [1, 0, 8], "fence": "oak_fence"}, "at least 3 x 3"),
            ({"gate": {"side": "north"}}, "needs a 'fence'"),
            ({"lanterns": {}}, "need a 'fence'"),
            ({"fence": "oak_fence", "gate": {"offset": 12}}, "between 1 and 11"),
            ({"style": "orchard"}, "style"),
        ],
    )
    def test_invalid(self, extra: dict[str, Any], match: str) -> None:
        with pytest.raises(BlueprintError, match=match):
            build_operation(garden(**extra), "operations[0]")


class TestValidation:
    def test_valid(self) -> None:
        data = blueprint(
            garden(fence="oak_fence", gate={"side": "east", "offset": 3}, lanterns={"spacing": 3}),
            garden(
                **{"from": [0, 0, 12], "to": [6, 0, 16]},
                style="flowers",
                plants={"palette": "p"},
                ground={"palette": "p"},
            ),
            palettes={"p": [{"block": "minecraft:poppy", "weight": 1}]},
        )
        assert validate(data) == []

    def test_bad_blocks_reported(self) -> None:
        errors = validate(
            blueprint(
                garden(
                    crop="bad_crop",
                    fence="bad_fence",
                    ground={"palette": "nope"},
                    gate={"block": "bad_gate"},
                    lanterns={"block": "bad_lantern"},
                )
            )
        )
        assert {e.path for e in errors} == {
            "operations[0].crop",
            "operations[0].fence",
            "operations[0].ground.palette",
            "operations[0].gate.block",
            "operations[0].lanterns.block",
        }
