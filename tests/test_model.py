import random

import pytest

from mcblueprint.errors import BlueprintError, BlueprintValidationError, ValidationError
from mcblueprint.model import AABB, BlockState, Palette, PaletteEntry, Vec3


class TestVec3:
    def test_arithmetic(self) -> None:
        a = Vec3(1, 2, 3)
        b = Vec3(10, 20, 30)
        assert a + b == Vec3(11, 22, 33)
        assert b - a == Vec3(9, 18, 27)
        assert a * 2 == Vec3(2, 4, 6)
        assert 2 * a == Vec3(2, 4, 6)
        assert -a == Vec3(-1, -2, -3)

    def test_min_max_and_axis(self) -> None:
        a = Vec3(1, 20, 3)
        b = Vec3(10, 2, 30)
        assert Vec3.min(a, b) == Vec3(1, 2, 3)
        assert Vec3.max(a, b) == Vec3(10, 20, 30)
        assert a.axis("y") == 20
        assert a.with_axis("y", 0) == Vec3(1, 0, 3)
        assert a[2] == 3
        assert list(a) == [1, 20, 3]

    def test_from_seq_and_hashable(self) -> None:
        assert Vec3.from_seq([1, 2, 3]) == Vec3(1, 2, 3)
        assert {Vec3(0, 0, 0): 1}[Vec3(0, 0, 0)] == 1
        with pytest.raises(ValueError):
            Vec3.from_seq([1, 2])
        assert str(Vec3(1, -2, 3)) == "[1, -2, 3]"


class TestAABB:
    def test_of_any_corner_order(self) -> None:
        box = AABB.of(Vec3(5, 0, -2), Vec3(-1, 3, 4))
        assert box.min == Vec3(-1, 0, -2)
        assert box.max == Vec3(5, 3, 4)
        assert box.size == Vec3(7, 4, 7)
        assert box.volume == 7 * 4 * 7

    def test_union_contains_from_points(self) -> None:
        a = AABB.of(Vec3(0, 0, 0), Vec3(1, 1, 1))
        b = AABB.of(Vec3(5, 5, 5), Vec3(6, 6, 6))
        u = a.union(b)
        assert u == AABB(Vec3(0, 0, 0), Vec3(6, 6, 6))
        assert u.contains(Vec3(3, 3, 3))
        assert not a.contains(Vec3(3, 3, 3))
        assert AABB.from_points([]) is None
        assert AABB.from_points([Vec3(2, 0, 1), Vec3(-1, 4, 1)]) == AABB(
            Vec3(-1, 0, 1), Vec3(2, 4, 1)
        )

    def test_invalid_box(self) -> None:
        with pytest.raises(ValueError):
            AABB(Vec3(1, 0, 0), Vec3(0, 0, 0))

    def test_str(self) -> None:
        assert str(AABB.of(Vec3(-5, 0, -5), Vec3(5, 7, 5))) == "X -5..5  Y 0..7  Z -5..5"


class TestBlockState:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("minecraft:stone", "minecraft:stone"),
            ("stone", "minecraft:stone"),
            ("mymod:thing", "mymod:thing"),
            ("oak_stairs[half=top,facing=north]", "minecraft:oak_stairs[facing=north,half=top]"),
            ("minecraft:oak_slab[type=top]", "minecraft:oak_slab[type=top]"),
        ],
    )
    def test_parse_normalises(self, text: str, expected: str) -> None:
        state = BlockState.parse(text)
        assert state.to_string() == expected
        assert str(state) == expected

    def test_parse_fields(self) -> None:
        state = BlockState.parse("oak_stairs[half=top,facing=north]")
        assert state.id == "minecraft:oak_stairs"
        assert state.properties == (("facing", "north"), ("half", "top"))
        assert state.get("half") == "top"
        assert state.get("shape") is None

    @pytest.mark.parametrize(
        "text",
        ["", "Stone", "minecraft:stone[]", "stone[facing]", "stone[a=1,a=2]", "a b"],
    )
    def test_parse_rejects_invalid(self, text: str) -> None:
        with pytest.raises(BlueprintError):
            BlockState.parse(text)

    def test_of_with_property_with_defaults(self) -> None:
        state = BlockState.of("oak_stairs", facing="north")
        assert state == BlockState.parse("minecraft:oak_stairs[facing=north]")
        flipped = state.with_property("facing", "south")
        assert flipped.get("facing") == "south"
        assert state.get("facing") == "north"
        full = state.with_defaults({"facing": "east", "half": "bottom", "shape": "straight"})
        assert full.to_string() == "minecraft:oak_stairs[facing=north,half=bottom,shape=straight]"

    def test_equality_and_hash(self) -> None:
        assert BlockState.parse("stone") == BlockState.parse("minecraft:stone")
        assert len({BlockState.parse("stone"), BlockState.parse("minecraft:stone")}) == 1


class TestPalette:
    def test_choose_is_deterministic_for_seed(self) -> None:
        palette = Palette(
            "p",
            (
                PaletteEntry(BlockState.parse("a"), 70),
                PaletteEntry(BlockState.parse("b"), 20),
                PaletteEntry(BlockState.parse("c"), 10),
            ),
        )
        first = [palette.choose(random.Random(123)).id for _ in range(1)]
        again = [palette.choose(random.Random(123)).id for _ in range(1)]
        assert first == again
        rng = random.Random(7)
        picks = [palette.choose(rng).id for _ in range(500)]
        assert picks.count("minecraft:a") > picks.count("minecraft:b") > picks.count("minecraft:c")

    def test_single_entry_still_consumes_rng(self) -> None:
        palette = Palette("p", (PaletteEntry(BlockState.parse("a")),))
        rng = random.Random(1)
        before = rng.getstate()
        assert palette.choose(rng).id == "minecraft:a"
        assert rng.getstate() != before

    def test_empty_palette_rejected(self) -> None:
        with pytest.raises(ValueError):
            Palette("p", ())


class TestErrors:
    def test_validation_error_format(self) -> None:
        err = ValidationError("operations[4]", "radius must be greater than 0.", "cylinder", -5)
        assert err.format() == (
            "ERROR operations[4] (cylinder)\n  radius must be greater than 0.\n  Current value: -5"
        )
        assert ValidationError("", "bad").format() == "ERROR (top level)\n  bad"

    def test_validation_exception_message(self) -> None:
        one = BlueprintValidationError([ValidationError("", "x")])
        two = BlueprintValidationError([ValidationError("", "x"), ValidationError("", "y")])
        assert str(one) == "1 error found."
        assert str(two) == "2 errors found."
        assert isinstance(one, BlueprintError)
