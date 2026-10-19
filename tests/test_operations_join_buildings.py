import random
from collections import Counter, deque
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model import AABB, BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation
from mcblueprint.operations.join_buildings import JoinBuildingsOperation
from mcblueprint.operations.transform import Transform
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse


def building(**changes: Any) -> dict[str, Any]:
    return {
        "type": "building", "position": [0, 0, 0], "width": 7, "depth": 10, "floors": 2,
        "wall": "stone_bricks", "floor": "oak_planks", "roof": "oak_stairs",
        "stairs": "oak_stairs", "window": "glass", "door": "oak_door", **changes,
    }


def joined(**changes: Any) -> dict[str, Any]:
    return {
        "type": "join_buildings",
        "buildings": [building(), building(position=[6, 0, 0], floor="birch_planks")],
        "faces": ["east", "west"], "wall": "bricks",
        "openings": [{"floor": 0, "offset": 7, "width": 2}, {"floor": 1, "offset": 7, "width": 2}],
        **changes,
    }


def blueprint(op: dict[str, Any], version: str = "1.21.11") -> dict[str, Any]:
    return {"formatVersion": 1, "minecraftVersion": version, "name": "joined", "operations": [op]}


def run(raw: dict[str, Any]) -> tuple[JoinBuildingsOperation, BlockVolume]:
    op = build_operation(raw, "operations[0]")
    assert isinstance(op, JoinBuildingsOperation)
    volume = BlockVolume()
    op.apply(ExecutionContext(volume, random.Random(0), {}))
    return op, volume


class CountedVolume(BlockVolume):
    def __init__(self) -> None:
        super().__init__()
        self.writes: Counter[Vec3] = Counter()

    def set(self, pos: Vec3, state: BlockState) -> None:
        self.writes[pos] += 1
        super().set(pos, state)


def test_shared_face_is_written_once_with_openings_and_first_floor_material() -> None:
    raw = joined()
    assert validate(blueprint(raw)) == []
    op = build_operation(raw, "operations[0]")
    volume = CountedVolume()
    op.apply(ExecutionContext(volume, random.Random(0), {}))
    for y in range(9):
        for z in range(10):
            pos = Vec3(6, y, z)
            expected = B("oak_planks") if y % 4 == 0 else B("bricks")
            if z in (7, 8) and y in (1, 2, 5, 6):
                expected = B("air")
            assert volume.get(pos) == expected
            assert volume.writes[pos] == 1
    assert volume.get(Vec3(5, 1, 7)) == B("air")
    assert volume.get(Vec3(7, 1, 7)) == B("air")
    assert volume.get(Vec3(7, 0, 7)) == B("birch_planks")
    assert op.bounds() == volume.bounds()


@pytest.mark.parametrize("angle", (0, 90, 180, 270))
def test_global_rotation_and_translation_preserve_join_geometry(angle: int) -> None:
    raw = joined()
    original_op, original = run(raw)
    transform = Transform.rotation(angle, Vec3(0, 0, 0)).then(
        Transform.translation(Vec3(-13, -2, 7))
    )
    for item in raw["buildings"]:
        item["angle"] = angle
        item["position"] = transform.apply(Vec3.from_seq(item["position"])).to_list()
    raw["faces"] = [transform.apply_direction(side) for side in raw["faces"]]
    if angle in (90, 180):
        for opening in raw["openings"]:
            opening["offset"] = 10 - opening["offset"] - opening.get("width", 1)
    op, rotated = run(raw)
    assert validate(blueprint(raw)) == []
    assert dict(rotated) == {transform.apply(p): transform.apply_state(s) for p, s in original}
    assert op.layout.shared_face.bounds == transform.bounds(original_op.layout.shared_face.bounds)
    assert op.layout.openings == tuple(transform.bounds(box) for box in original_op.layout.openings)


def test_outer_nesting_preserves_cell_ownership_and_depth_budget() -> None:
    raw = joined()
    op, original = run(raw)
    transform = Transform.rotation(90, Vec3(0, 0, 0)).then(Transform.translation(Vec3(4, -2, -7)))
    volume = CountedVolume()
    op.apply(ExecutionContext(volume, random.Random(0), {}, transform))
    assert dict(volume) == {transform.apply(p): transform.apply_state(s) for p, s in original}
    for y in range(9):
        for z in range(10):
            assert volume.writes[transform.apply(Vec3(6, y, z))] == 1
    nested = raw
    for _ in range(7):
        nested = {"type": "translate", "offset": [1, 0, 0], "operations": [nested]}
    assert validate(blueprint(nested)) == []
    expected = {p + Vec3(7, 0, 0): s for p, s in original}
    assert dict(generate(load_blueprint_dict(blueprint(nested)))) == expected
    too_deep = {"type": "translate", "offset": [0, 0, 0], "operations": [nested]}
    assert any("deeper than 8" in e.message for e in validate(blueprint(too_deep)))


def test_partial_shared_face_keeps_nonshared_windows_and_wall() -> None:
    raw = joined(buildings=[building(), building(position=[6, 0, 6])],
                 openings=[{"offset": 1}])
    op, volume = run(raw)
    assert op.layout.shared_face.bounds == AABB(Vec3(6, 1, 6), Vec3(6, 8, 9))
    assert volume.get(Vec3(6, 2, 6)) == B("bricks")
    assert volume.get(Vec3(6, 2, 4)) == B("glass")  # 非共有部分の東窓を残す。
    assert volume.get(Vec3(6, 2, 3)) == B("stone_bricks")
    # 二棟目の北面・東面等、同じ方角でも共通でない部分は生成する。
    assert volume.get(Vec3(6, 2, 14)) == B("stone_bricks")
    assert volume.get(Vec3(12, 2, 10)) == B("glass")


@pytest.mark.parametrize("counts", ((1, 2), (2, 1)))
def test_different_floor_counts_reject_roof_and_upper_facade_interference(counts: tuple) -> None:
    raw = joined(buildings=[building(floors=counts[0]),
                            building(position=[6, 0, 0], floors=counts[1])],
                 openings=[{"offset": 7}])
    assert validate(blueprint(raw))
    with pytest.raises(BlueprintError, match="異階数.*上側外壁・床"):
        run(raw)


def test_minimum_building_and_shared_span() -> None:
    raw = joined(
        buildings=[building(width=5, depth=5, floors=1),
                   building(position=[4, 0, 2], width=5, depth=5, floors=1)],
        openings=[{"offset": 1}],
    )
    assert validate(blueprint(raw)) == []
    op, volume = run(raw)
    assert op.layout.shared_face.bounds.size.z == 3
    assert volume.get(Vec3(4, 1, 3)) == B("air")
    assert volume.get(Vec3(4, 1, 2)) == volume.get(Vec3(4, 1, 4)) == B("bricks")


@pytest.mark.parametrize("change", [
    {"faces": ["east", "east"]},
    {"buildings": [building(), building(position=[7, 0, 0])]},
    {"buildings": [building(), building(position=[6, 1, 0])]},
    {"buildings": [building(), building(position=[6, 0, 0], floorHeight=5)]},
    {"buildings": [building(), building(position=[6, 0, 8])]},
    {"openings": []}, {"openings": [{"offset": 0}]},
    {"openings": [{"offset": 8, "width": 2}]},
    {"openings": [{"offset": 7, "height": 4}]},
    {"openings": [{"offset": 7, "floor": 2}]},
    {"openings": [{"offset": 2}]},  # 二棟目の西内側の階段予約域。
    {"openings": [{"offset": 7}, {"offset": 7}]},
    {"buildings": [building(floors=1), building(position=[6, 0, 0])], "openings": [{"offset": 7}]},
])
def test_rejects_bad_contact_or_interference_before_writing(change: dict[str, Any]) -> None:
    raw = joined(**change)
    assert validate(blueprint(raw))
    with pytest.raises(BlueprintError):
        run(raw)


def test_major_entrance_cannot_be_replaced_by_shared_wall() -> None:
    raw = joined(
        buildings=[building(), building(position=[0, 0, -9])],
        faces=["north", "south"], openings=[{"offset": 2}],
    )
    with pytest.raises(BlueprintError, match="主要入口"):
        run(raw)


@pytest.mark.parametrize("role", ("wall", "floor", "roof", "stairs", "window", "door"))
def test_nested_building_materials_are_validated(role: str) -> None:
    raw = joined()
    raw["buildings"][1][role] = "missing_block"
    assert any(f"buildings[1].{role}" in e.path for e in validate(blueprint(raw)))
    raw["buildings"][1][role] = "oak_planks[missing=true]"
    assert validate(blueprint(raw))


@pytest.mark.parametrize("change", [
    {"buildings": [building()]}, {"buildings": [building()] * 3},
    {"buildings": [building(), {"type": "fill"}]}, {"wall": "missing_block"},
    {"faces": ["up", "down"]}, {"openings": [{"offset": 7, "width": True}]},
    {"openings": [{"offset": 7, "extra": True}]}, {"extra": True},
])
def test_schema_rejects_unsupported_inputs(change: dict[str, Any]) -> None:
    assert validate(blueprint(joined(**change)))


def test_connection_layout_is_immutable() -> None:
    op, _ = run(joined())
    with pytest.raises(FrozenInstanceError):
        op.layout.floor_y = 5


def test_both_buildings_reach_opening_with_feet_and_head_space() -> None:
    op, volume = run(joined())
    # 各階の到着点から水平に歩く対照。階段自体の昇降判定は #106 に委ねる。
    for floor in (0, 1):
        y = floor * 4 + 1
        target = Vec3(6, y, 7)
        for layout in op.layout.buildings:
            start = layout.arrivals[floor]
            pending, seen = deque([start]), {start}
            while pending:
                pos = pending.popleft()
                for delta in (Vec3(1, 0, 0), Vec3(-1, 0, 0), Vec3(0, 0, 1), Vec3(0, 0, -1)):
                    nxt = pos + delta
                    if nxt in seen or not (-1 <= nxt.x <= 13 and -1 <= nxt.z <= 10):
                        continue
                    if volume.get(nxt) != B("air") or volume.get(nxt + Vec3(0, 1, 0)) != B("air"):
                        continue
                    if volume.get(nxt - Vec3(0, 1, 0)) not in (B("oak_planks"), B("birch_planks")):
                        continue
                    seen.add(nxt)
                    pending.append(nxt)
            assert target in seen


@pytest.mark.parametrize("width", (5, 6, 7, 8))
@pytest.mark.parametrize("floors", (1, 2))
@pytest.mark.parametrize("floor_height", (4, 5, 6))
def test_dimension_matrix_keeps_connection_and_reserved_space_separate(
    width: int, floors: int, floor_height: int,
) -> None:
    depth = floor_height + 6
    raw = joined(
        buildings=[building(width=width, depth=depth, floors=floors, floorHeight=floor_height),
                   building(position=[width - 1, 0, 0], width=width, depth=depth,
                            floors=floors, floorHeight=floor_height)],
        openings=[{"floor": floor, "offset": floor_height + 3, "height": floor_height - 1}
                  for floor in range(floors)],
    )
    assert validate(blueprint(raw)) == []
    op, volume = run(raw)
    for box in op.layout.openings:
        for y in range(box.min.y, box.max.y + 1):
            assert volume.get(Vec3(width - 1, y, box.min.z)) == B("air")
    assert op.bounds() == volume.bounds()


def test_individually_rotated_building_keeps_shared_face_in_placement_coordinates() -> None:
    raw = joined(
        buildings=[building(), building(position=[15, 0, 0], angle=90)],
        openings=[{"offset": 2, "width": 2}],
    )
    assert validate(blueprint(raw)) == []
    op, volume = run(raw)
    assert op.layout.shared_face.bounds == AABB(Vec3(6, 1, 0), Vec3(6, 8, 6))
    assert volume.get(Vec3(6, 1, 2)) == volume.get(Vec3(7, 1, 2)) == B("air")


def test_shared_material_uses_selected_block_version() -> None:
    raw = joined(wall="poplar_planks")
    assert validate(blueprint(raw, "1.21.11"))
    assert validate(blueprint(raw, "26.3")) == []


def test_direct_failure_preserves_preexisting_volume() -> None:
    volume = CountedVolume()
    volume.set(Vec3(100, 0, 100), B("gold_block"))
    ctx = ExecutionContext(volume, random.Random(0), {})
    with pytest.raises(BlueprintError, match="階段"):
        build_operation(joined(openings=[{"offset": 2}]), "operations[0]").apply(ctx)
    assert dict(volume) == {Vec3(100, 0, 100): B("gold_block")}
    assert sum(volume.writes.values()) == 1


def test_fixed_fixture_and_independent_control_are_valid() -> None:
    from mcblueprint.loader import load_blueprint, read_blueprint_json

    root = Path(__file__).parent / "data"
    for name in ("joined_buildings.json", "joined_buildings_independent.json"):
        path = root / name
        assert validate(read_blueprint_json(path)) == []
        assert generate(load_blueprint(path)).bounds() is not None


@pytest.mark.parametrize("angle", (0, 90, 180, 270))
@pytest.mark.parametrize("height", (4, 5, 6))
def test_stairs_reservation_includes_transition_headroom_three(angle: int, height: int) -> None:
    from mcblueprint.operations.building import BuildingOperation

    raw = building(position=[-3, 2, 7], floorHeight=height, depth=height + 6, angle=angle)
    op = build_operation(raw, "operations[0]")
    assert isinstance(op, BuildingOperation)
    transform = Transform.rotation(angle, Vec3(0, 0, 0)).then(
        Transform.translation(Vec3(-3, 2, 7))
    )
    expected = AABB(Vec3(1, 1, 2), Vec3(1, height + 3, height + 2))
    assert op.stairs_bounds == transform.bounds(expected)
    volume = generate(load_blueprint_dict(blueprint(raw)))
    assert volume.get(transform.apply(Vec3(1, height + 3, height + 1))) == B("air")
    assert volume.get(transform.apply(Vec3(1, height, height - 2))) == B("air")
