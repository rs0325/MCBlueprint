import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.model import AABB, BlockState, Vec3
from mcblueprint.operations.transform import Transform

B = BlockState.parse


class TestRotation:
    @pytest.mark.parametrize(
        ("angle", "pos", "expected"),
        [
            (0, Vec3(3, 1, 0), Vec3(3, 1, 0)),
            (90, Vec3(3, 1, 0), Vec3(0, 1, 3)),  # east -> south
            (180, Vec3(3, 1, 0), Vec3(-3, 1, 0)),  # east -> west
            (270, Vec3(3, 1, 0), Vec3(0, 1, -3)),  # east -> north
            (90, Vec3(0, 5, 2), Vec3(-2, 5, 0)),  # south -> west
            (-90, Vec3(3, 1, 0), Vec3(0, 1, -3)),
            (360, Vec3(3, 1, 0), Vec3(3, 1, 0)),
        ],
    )
    def test_about_origin(self, angle: int, pos: Vec3, expected: Vec3) -> None:
        assert Transform.rotation(angle, Vec3(0, 0, 0)).apply(pos) == expected

    def test_about_center(self) -> None:
        t = Transform.rotation(90, Vec3(10, 0, 10))
        assert t.apply(Vec3(10, 0, 10)) == Vec3(10, 0, 10)
        assert t.apply(Vec3(12, 3, 10)) == Vec3(10, 3, 12)

    def test_four_quarters_are_identity(self) -> None:
        q = Transform.rotation(90, Vec3(4, 0, -2))
        t = q.then(q).then(q).then(q)
        assert t == Transform.identity()

    def test_invalid_angle(self) -> None:
        with pytest.raises(BlueprintError):
            Transform.rotation(45, Vec3(0, 0, 0))

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("oak_stairs[facing=east]", "minecraft:oak_stairs[facing=south]"),
            (
                "oak_stairs[facing=north,shape=inner_left]",
                "minecraft:oak_stairs[facing=east,shape=inner_left]",
            ),
            ("oak_log[axis=x]", "minecraft:oak_log[axis=z]"),
            ("oak_log[axis=y]", "minecraft:oak_log[axis=y]"),
            (
                "glass_pane[east=true,north=false,south=false,west=true]",
                "minecraft:glass_pane[east=false,north=true,south=true,west=false]",
            ),
            ("piston[facing=up]", "minecraft:piston[facing=up]"),
            ("oak_slab[type=top]", "minecraft:oak_slab[type=top]"),
            ("oak_door[facing=north,hinge=left]", "minecraft:oak_door[facing=east,hinge=left]"),
        ],
    )
    def test_state_rotation_90(self, text: str, expected: str) -> None:
        assert Transform.rotation(90, Vec3(0, 0, 0)).apply_state(B(text)).to_string() == expected

    def test_bounds(self) -> None:
        box = AABB.of(Vec3(0, 0, 0), Vec3(4, 2, 1))
        assert Transform.rotation(90, Vec3(0, 0, 0)).bounds(box) == AABB.of(
            Vec3(-1, 0, 0), Vec3(0, 2, 4)
        )


class TestComposition:
    def test_rotation_then_mirror_is_reflection(self) -> None:
        t = Transform.rotation(90, Vec3(0, 0, 0)).then(Transform.mirror("x", 0))
        assert t.is_reflection
        assert not Transform.rotation(180, Vec3(0, 0, 0)).is_reflection
        assert Transform.mirror("y", 0).flips_y

    def test_translation_inside_rotation(self) -> None:
        inner = Transform.translation(Vec3(1, 0, 0))
        outer = Transform.rotation(90, Vec3(0, 0, 0))
        p = Vec3(2, 0, 0)
        assert inner.then(outer).apply(p) == outer.apply(inner.apply(p)) == Vec3(0, 0, 3)

    def test_identity_state_untouched(self) -> None:
        state = B("oak_stairs[facing=east,shape=inner_left]")
        assert Transform.translation(Vec3(5, 5, 5)).apply_state(state) is state
