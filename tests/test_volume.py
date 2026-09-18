from mcblueprint.model import AABB, BlockState, Vec3
from mcblueprint.volume import BlockVolume

STONE = BlockState.parse("stone")
BRICKS = BlockState.parse("stone_bricks")
AIR = BlockState.parse("air")


def test_empty_volume() -> None:
    volume = BlockVolume()
    assert len(volume) == 0
    assert volume.bounds() is None
    assert volume.get(Vec3(0, 0, 0)) is None
    assert volume.palette == []
    assert volume.count_by_state() == {}
    assert list(volume) == []


def test_set_get_and_overwrite() -> None:
    volume = BlockVolume()
    volume.set(Vec3(1, 2, 3), STONE)
    assert volume.get(Vec3(1, 2, 3)) == STONE
    assert Vec3(1, 2, 3) in volume
    assert Vec3(0, 0, 0) not in volume

    volume.set(Vec3(1, 2, 3), BRICKS)
    assert volume.get(Vec3(1, 2, 3)) == BRICKS
    assert len(volume) == 1

    volume.set(Vec3(1, 2, 3), AIR)
    assert volume.get(Vec3(1, 2, 3)) == AIR
    assert len(volume) == 1


def test_palette_interns_states() -> None:
    volume = BlockVolume()
    volume.set(Vec3(0, 0, 0), STONE)
    volume.set(Vec3(1, 0, 0), BlockState.parse("minecraft:stone"))
    volume.set(Vec3(2, 0, 0), BRICKS)
    assert volume.palette == [STONE, BRICKS]
    assert len(volume) == 3


def test_bounds() -> None:
    volume = BlockVolume()
    volume.set(Vec3(-3, 0, 2), STONE)
    volume.set(Vec3(5, 7, -1), STONE)
    volume.set(Vec3(0, 1, 0), BRICKS)
    assert volume.bounds() == AABB(Vec3(-3, 0, -1), Vec3(5, 7, 2))


def test_count_by_state_is_ordered_by_frequency() -> None:
    volume = BlockVolume()
    for x in range(5):
        volume.set(Vec3(x, 0, 0), STONE)
    for x in range(3):
        volume.set(Vec3(x, 1, 0), BRICKS)
    volume.set(Vec3(0, 2, 0), AIR)
    volume.set(Vec3(0, 1, 0), STONE)  # overwrite one brick with stone
    counts = volume.count_by_state()
    assert counts == {"minecraft:stone": 6, "minecraft:stone_bricks": 2, "minecraft:air": 1}
    assert list(counts) == ["minecraft:stone", "minecraft:stone_bricks", "minecraft:air"]


def test_iteration_yields_positions_and_states() -> None:
    volume = BlockVolume()
    volume.set(Vec3(0, 0, 0), STONE)
    volume.set(Vec3(1, 0, 0), BRICKS)
    assert set(volume) == {(Vec3(0, 0, 0), STONE), (Vec3(1, 0, 0), BRICKS)}
    assert set(volume.positions()) == {Vec3(0, 0, 0), Vec3(1, 0, 0)}
