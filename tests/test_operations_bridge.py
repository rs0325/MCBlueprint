import random
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation, build_operations
from mcblueprint.operations.bridge import connected, profile
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse
AIR = B("air")
DECK = B("stone_bricks")


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


def bridge(**extra: Any) -> dict[str, Any]:
    data = {"type": "bridge", "from": [0, 5, 0], "to": [10, 5, 0], "deck": "stone_bricks", **extra}
    return {k: v for k, v in data.items() if v is not None}


class TestHelpers:
    def test_profile(self) -> None:
        assert profile(7, 0) == [0] * 7
        assert profile(7, 2) == [0, 1, 2, 2, 2, 1, 0]
        assert profile(5, 2) == [0, 1, 2, 1, 0]

    def test_connected_fence_wall_and_explicit(self) -> None:
        fence = connected(B("oak_fence"), "x", True, False)
        assert fence == B("oak_fence[east=false,west=true]")
        wall = connected(B("cobblestone_wall"), "z", True, True)
        assert wall == B("cobblestone_wall[north=low,south=low,up=false]")
        post = connected(B("cobblestone_wall"), "z", False, True)
        assert post.get("up") == "true" and post.get("south") == "low"
        explicit = connected(B("oak_fence[west=false]"), "x", True, True)
        assert explicit.get("west") == "false" and explicit.get("east") == "true"
        assert connected(B("stone_brick_slab"), "x", True, True) == B("stone_brick_slab")


class TestFlat:
    def test_deck_width_and_headroom(self) -> None:
        volume = run(
            {"type": "fill", "from": [0, 0, -3], "to": [10, 9, 3], "block": "stone"},
            bridge(width=3),
        )
        for z in (-1, 0, 1):
            assert volume.get(Vec3(5, 5, z)) == DECK
            assert volume.get(Vec3(5, 6, z)) == AIR and volume.get(Vec3(5, 7, z)) == AIR
        assert volume.get(Vec3(5, 5, 2)) == B("stone")
        assert volume.get(Vec3(5, 8, 0)) == B("stone")
        assert volume.get(Vec3(5, 4, 0)) == B("stone")  # nothing below a flat deck
        assert volume.bounds().min.x == 0 and volume.bounds().max.x == 10

    def test_even_width_leans_positive(self) -> None:
        volume = run(bridge(width=2))
        assert volume.get(Vec3(3, 5, 0)) == DECK and volume.get(Vec3(3, 5, 1)) == DECK
        assert volume.get(Vec3(3, 5, -1)) is None

    def test_along_z_and_reversed(self) -> None:
        volume = run(bridge(**{"from": [0, 5, 8], "to": [0, 5, 2], "width": 1}))
        for z in range(2, 9):
            assert volume.get(Vec3(0, 5, z)) == DECK
        assert volume.get(Vec3(0, 5, 9)) is None

    def test_railings_connect_along_the_deck(self) -> None:
        volume = run(bridge(width=3, railing="oak_fence", railingHeight=2))
        assert volume.get(Vec3(0, 6, -1)) == B("oak_fence[east=true,west=false]")
        assert volume.get(Vec3(5, 6, 1)) == B("oak_fence[east=true,west=true]")
        assert volume.get(Vec3(10, 7, -1)) == B("oak_fence[east=false,west=true]")
        assert volume.get(Vec3(5, 6, 0)) == AIR  # walkway stays clear
        assert volume.get(Vec3(5, 8, 1)) is None

    def test_railing_on_single_column_deck(self) -> None:
        volume = run(bridge(width=1, railing="stone_brick_wall"))
        assert volume.get(Vec3(5, 6, 0)) == B("stone_brick_wall[east=low,up=false,west=low]")
        assert volume.get(Vec3(0, 6, 0)) == B("stone_brick_wall[east=low,up=true,west=none]")

    def test_piers(self) -> None:
        volume = run(bridge(width=3, piers={"spacing": 4, "bottom": 1, "block": "cobblestone"}))
        for x in (4, 8):
            for y in range(1, 5):
                assert volume.get(Vec3(x, y, -1)) == B("cobblestone")
                assert volume.get(Vec3(x, y, 1)) == B("cobblestone")
        assert volume.get(Vec3(0, 4, 0)) is None and volume.get(Vec3(5, 4, 0)) is None
        assert volume.get(Vec3(4, 0, 0)) is None

    def test_palette_deck_and_piers_default_to_deck(self) -> None:
        from mcblueprint.model import Palette, PaletteEntry

        ctx = ExecutionContext(
            BlockVolume(), random.Random(0), {"p": Palette("p", (PaletteEntry(B("andesite")),))}
        )
        op = build_operation(
            bridge(deck={"palette": "p"}, piers={"spacing": 5, "bottom": 3}), "operations[0]"
        )
        op.apply(ctx)
        assert ctx.volume.get(Vec3(5, 5, 0)) == B("andesite")
        assert ctx.volume.get(Vec3(5, 3, 0)) == B("andesite")


class TestArch:
    def test_ramp_plateau_body_and_stairs(self) -> None:
        volume = run(
            bridge(
                **{"to": [12, 5, 0]},
                width=1,
                style="arch",
                rise=2,
                stairs="stone_brick_stairs",
            )
        )
        east, west = (
            "stone_brick_stairs[facing=east,half=bottom]",
            "stone_brick_stairs[facing=west,half=bottom]",
        )
        assert volume.get(Vec3(0, 5, 0)) == DECK
        assert volume.get(Vec3(1, 6, 0)) == B(east) and volume.get(Vec3(2, 7, 0)) == B(east)
        assert volume.get(Vec3(6, 7, 0)) == DECK  # plateau
        assert volume.get(Vec3(10, 7, 0)) == B(west) and volume.get(Vec3(11, 6, 0)) == B(west)
        assert volume.get(Vec3(12, 5, 0)) == DECK
        # solid body under raised cells, clear walking space above each cell
        assert volume.get(Vec3(2, 5, 0)) == DECK and volume.get(Vec3(2, 6, 0)) == DECK
        assert volume.get(Vec3(1, 5, 0)) == DECK
        assert volume.get(Vec3(6, 8, 0)) == AIR and volume.get(Vec3(6, 9, 0)) == AIR
        assert volume.get(Vec3(1, 7, 0)) == AIR

    def test_without_stairs_steps_use_deck(self) -> None:
        volume = run(bridge(style="arch", rise=1, width=1))
        assert volume.get(Vec3(1, 6, 0)) == DECK

    def test_railing_follows_profile_with_posts_at_steps(self) -> None:
        volume = run(
            bridge(
                **{"to": [12, 5, 0]},
                width=3,
                style="arch",
                rise=2,
                stairs="stone_brick_stairs",
                railing="stone_brick_wall",
            )
        )
        assert volume.get(Vec3(1, 7, -1)).id.endswith("stone_brick_wall")
        assert volume.get(Vec3(1, 7, -1)).get("up") == "true"
        assert volume.get(Vec3(6, 8, 1)) == B("stone_brick_wall[east=low,up=false,west=low]")
        assert volume.get(Vec3(6, 8, 0)) == AIR

    def test_piers_stop_under_the_raised_deck(self) -> None:
        volume = run(
            bridge(
                **{"to": [12, 5, 0]},
                width=1,
                style="arch",
                rise=2,
                piers={"spacing": 6, "bottom": 2},
            )
        )
        # the pier at x=6 (height 2) runs from y=2 up to y=4; the body covers 5..6
        for y in (2, 3, 4):
            assert volume.get(Vec3(6, y, 0)) == DECK
        assert volume.get(Vec3(6, 5, 0)) == DECK and volume.get(Vec3(6, 7, 0)) == DECK


class TestErrors:
    @pytest.mark.parametrize(
        ("extra", "match"),
        [
            ({"to": [10, 6, 0]}, "same y"),
            ({"to": [10, 5, 4]}, "straight along x or z"),
            ({"style": "arch"}, "rise of at least 1"),
            ({"style": "arch", "rise": 6}, "at most 5 for a bridge 11 long"),
            ({"piers": {"spacing": 3}}, "'bottom'"),
            ({"piers": {"spacing": 3, "bottom": 5}}, "below the deck"),
            ({"piers": 3}, "piers"),
            ({"deck": None}, "missing required 'deck'"),
            ({"width": 0}, "width"),
        ],
    )
    def test_invalid(self, extra: dict[str, Any], match: str) -> None:
        with pytest.raises(BlueprintError, match=match):
            build_operation(bridge(**extra), "operations[0]")

    def test_single_cell_bridge(self) -> None:
        volume = run(bridge(**{"to": [0, 5, 0]}, width=1))
        assert volume.get(Vec3(0, 5, 0)) == DECK and len(volume) == 3


class TestValidation:
    def test_valid(self) -> None:
        assert (
            validate(
                blueprint(
                    bridge(
                        deck={"palette": "p"},
                        stairs="stone_brick_stairs",
                        railing="oak_fence",
                        piers={"spacing": 3, "bottom": 0, "block": {"palette": "p"}},
                    ),
                    palettes={"p": [{"block": "minecraft:stone_bricks", "weight": 1}]},
                )
            )
            == []
        )

    def test_bad_blocks_reported(self) -> None:
        errors = validate(
            blueprint(
                bridge(
                    deck="bad_deck",
                    stairs="bad_stairs",
                    railing="bad_rail",
                    piers={"spacing": 3, "bottom": 0, "block": {"palette": "nope"}},
                )
            )
        )
        assert {e.path for e in errors} == {
            "operations[0].deck",
            "operations[0].stairs",
            "operations[0].railing",
            "operations[0].piers.block.palette",
        }

    def test_schema_requires_pier_bottom(self) -> None:
        errors = validate(blueprint(bridge(piers={"spacing": 3})))
        assert errors and "piers" in errors[0].path
