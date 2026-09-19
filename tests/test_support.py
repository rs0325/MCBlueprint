import pytest

from mcblueprint.model import BlockState, Vec3
from mcblueprint.support import (
    check_support,
    format_warnings,
    supports_from_bottom,
    supports_from_side,
    supports_from_top,
)
from mcblueprint.volume import BlockVolume

B = BlockState.parse


def volume_with(*cells: tuple[tuple[int, int, int], str]) -> BlockVolume:
    volume = BlockVolume()
    for (x, y, z), block in cells:
        volume.set(Vec3(x, y, z), B(block))
    return volume


def messages(volume: BlockVolume) -> list[tuple[Vec3, str]]:
    return [(w.position, w.message) for w in check_support(volume)]


class TestPredicates:
    @pytest.mark.parametrize(
        ("block", "expected"),
        [
            ("stone", True),
            ("oak_planks", True),
            ("glass", True),
            ("oak_leaves", True),
            ("oak_slab[type=top]", True),
            ("oak_slab[type=double]", True),
            ("oak_slab[type=bottom]", False),
            ("oak_stairs[half=top]", True),
            ("oak_stairs[half=bottom]", False),
            ("oak_trapdoor[half=top,open=false]", True),
            ("oak_trapdoor[half=top,open=true]", False),
            ("oak_fence", True),
            ("cobblestone_wall", True),
            ("oak_fence_gate", False),
            ("glass_pane", False),
            ("air", False),
            ("water", False),
            ("torch", False),
            ("snow[layers=8]", True),
            ("snow[layers=3]", False),
            ("white_carpet", False),
            ("oak_door[half=lower]", False),
        ],
    )
    def test_supports_from_top(self, block: str, expected: bool) -> None:
        assert supports_from_top(B(block)) is expected

    @pytest.mark.parametrize(
        ("block", "expected"),
        [
            ("stone", True),
            ("oak_slab[type=bottom]", True),
            ("oak_slab[type=top]", False),
            ("oak_stairs[half=bottom]", True),
            ("oak_stairs[half=top]", False),
            ("chain", True),
            ("iron_bars", True),
            ("oak_fence", True),
            ("glass_pane", False),
            ("air", False),
            ("lantern", False),
        ],
    )
    def test_supports_from_bottom(self, block: str, expected: bool) -> None:
        assert supports_from_bottom(B(block)) is expected

    @pytest.mark.parametrize(
        ("block", "facing", "expected"),
        [
            ("stone", "east", True),
            ("oak_stairs[facing=east]", "east", True),
            ("oak_stairs[facing=north]", "east", False),
            ("oak_slab[type=top]", "east", False),
            ("oak_fence", "east", False),
            ("glass_pane", "east", False),
            ("air", "east", False),
        ],
    )
    def test_supports_from_side(self, block: str, facing: str, expected: bool) -> None:
        assert supports_from_side(B(block), facing) is expected


class TestLanternsAndTorches:
    def test_hanging_lantern_under_top_slab_warns(self) -> None:
        volume = volume_with(
            ((0, 2, 0), "oak_slab[type=top]"), ((0, 1, 0), "lantern[hanging=true]")
        )
        assert messages(volume) == [
            (Vec3(0, 1, 0), "Needs a solid block above; found minecraft:oak_slab[type=top].")
        ]

    def test_hanging_lantern_under_full_block_or_chain_is_fine(self) -> None:
        volume = volume_with(
            ((0, 2, 0), "oak_planks"),
            ((0, 1, 0), "lantern[hanging=true]"),
            ((2, 2, 0), "chain"),
            ((2, 1, 0), "soul_lantern[hanging=true]"),
        )
        assert messages(volume) == []

    def test_hanging_lantern_with_nothing_above_inside_structure_warns(self) -> None:
        volume = volume_with(((0, 3, 0), "stone"), ((0, 1, 0), "lantern[hanging=true]"))
        assert messages(volume) == [
            (Vec3(0, 1, 0), "Needs a solid block above; found minecraft:air.")
        ]

    def test_floor_lantern_and_torch(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "oak_slab[type=bottom]"),
            ((0, 1, 0), "lantern"),
            ((1, 0, 0), "oak_slab[type=top]"),
            ((1, 1, 0), "torch"),
            ((2, 0, 0), "oak_fence"),
            ((2, 1, 0), "soul_torch"),
            ((3, 0, 0), "stone"),
            ((3, 1, 0), "white_candle[candles=2]"),
        )
        assert messages(volume) == [
            (Vec3(0, 1, 0), "Needs a solid block below; found minecraft:oak_slab[type=bottom].")
        ]

    def test_outside_structure_is_unknown(self) -> None:
        # torch at the bottom of the structure: the supporting block would be outside
        volume = volume_with(((0, 0, 0), "torch"), ((5, 5, 5), "stone"))
        assert messages(volume) == []


class TestWallMounted:
    def test_wall_torch_needs_block_behind(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "stone"),
            ((1, 0, 0), "wall_torch[facing=east]"),
            ((3, 0, 0), "wall_torch[facing=east]"),
            ((2, 0, 0), "glass_pane"),
        )
        expected = (
            "Needs a solid block behind it (opposite to facing=east); found minecraft:glass_pane."
        )
        assert messages(volume) == [(Vec3(3, 0, 0), expected)]

    def test_ladder_and_wall_sign(self) -> None:
        volume = volume_with(
            ((0, 0, 1), "oak_planks"),
            ((0, 0, 0), "ladder[facing=north]"),
            ((0, 1, 1), "oak_slab[type=top]"),
            ((0, 1, 0), "oak_wall_sign[facing=north]"),
        )
        assert [pos for pos, _ in messages(volume)] == [Vec3(0, 1, 0)]

    def test_button_faces(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "stone"),
            ((0, 1, 0), "stone_button[face=floor,facing=north]"),
            ((1, 1, 0), "stone_button[face=floor,facing=north]"),
            ((2, 2, 0), "stone"),
            ((2, 1, 0), "lever[face=ceiling,facing=north]"),
            ((3, 1, 0), "lever[face=ceiling,facing=north]"),
            ((3, 2, 0), "glass_pane"),
        )
        assert [pos for pos, _ in messages(volume)] == [Vec3(1, 1, 0), Vec3(3, 1, 0)]


class TestDoorsAndBeds:
    def test_door_pair(self) -> None:
        good = volume_with(
            ((0, 0, 0), "stone"),
            ((0, 1, 0), "oak_door[facing=south,half=lower,hinge=left]"),
            ((0, 2, 0), "oak_door[facing=south,half=upper,hinge=left]"),
        )
        assert messages(good) == []

    def test_door_missing_upper(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "stone"),
            ((0, 1, 0), "oak_door[facing=south,half=lower,hinge=left]"),
            ((0, 2, 0), "stone"),
        )
        assert messages(volume) == [
            (Vec3(0, 1, 0), "Upper half of the door is missing above; found minecraft:stone.")
        ]

    def test_door_halves_with_different_facing(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "stone"),
            ((0, 1, 0), "oak_door[facing=south,half=lower,hinge=left]"),
            ((0, 2, 0), "oak_door[facing=north,half=upper,hinge=left]"),
        )
        assert len(messages(volume)) == 2

    def test_door_on_slab(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "oak_slab[type=bottom]"),
            ((0, 1, 0), "oak_door[facing=south,half=lower,hinge=left]"),
            ((0, 2, 0), "oak_door[facing=south,half=upper,hinge=left]"),
        )
        assert [pos for pos, _ in messages(volume)] == [Vec3(0, 1, 0)]

    def test_bed_pair(self) -> None:
        good = volume_with(
            ((0, 0, 0), "red_bed[facing=north,part=foot]"),
            ((0, 0, -1), "red_bed[facing=north,part=head]"),
        )
        assert messages(good) == []
        bad = volume_with(
            ((0, 0, 0), "red_bed[facing=north,part=foot]"),
            ((0, 0, -1), "stone"),
        )
        assert messages(bad) == [
            (Vec3(0, 0, 0), "Bed head is missing at [0, 0, -1]; found minecraft:stone.")
        ]


class TestPlantsAndCarpets:
    def test_flower_on_stone_warns(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "stone"),
            ((0, 1, 0), "poppy"),
            ((1, 0, 0), "grass_block"),
            ((1, 1, 0), "red_tulip"),
            ((2, 0, 0), "farmland"),
            ((2, 1, 0), "wheat[age=7]"),
            ((3, 0, 0), "dirt"),
            ((3, 1, 0), "wheat[age=7]"),
            ((4, 0, 0), "moss_block"),
            ((4, 1, 0), "oak_sapling"),
        )
        assert [pos for pos, _ in messages(volume)] == [Vec3(0, 1, 0), Vec3(3, 1, 0)]

    def test_carpet_needs_any_block(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "oak_slab[type=bottom]"),
            ((0, 1, 0), "red_carpet"),
            ((1, 2, 0), "red_carpet"),
            ((1, 0, 0), "stone"),
        )
        assert messages(volume) == [(Vec3(1, 2, 0), "Needs a block below; found air.")]


class TestFormat:
    def test_format(self) -> None:
        volume = volume_with(
            ((0, 2, 0), "oak_slab[type=top]"), ((0, 1, 0), "lantern[hanging=true]")
        )
        text = format_warnings(check_support(volume))
        assert text == (
            "WARNING [0, 1, 0] minecraft:lantern[hanging=true]\n"
            "  Needs a solid block above; found minecraft:oak_slab[type=top].\n"
            "\n"
            "1 warning found."
        )
        assert format_warnings([]) == ""

    def test_sorted_bottom_up(self) -> None:
        volume = volume_with(
            ((0, 5, 0), "torch"),
            ((0, 1, 0), "torch"),
            ((0, 0, 0), "stone"),
            ((0, 4, 0), "oak_slab[type=bottom]"),
            ((0, 6, 0), "glass_pane"),
            ((0, 2, 0), "glass_pane"),
        )
        assert [pos for pos, _ in messages(volume)] == [Vec3(0, 5, 0)]
