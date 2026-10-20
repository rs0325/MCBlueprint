import random
from typing import Any

import pytest

from mcblueprint import blockdata
from mcblueprint.errors import BlueprintError
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model import AABB, BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation
from mcblueprint.operations.building import BuildingOperation
from mcblueprint.operations.transform import Transform
from mcblueprint.support import check_support
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse
AIR = B("air")


def building(**changes: Any) -> dict[str, Any]:
    return {
        "type": "building", "position": [0, 0, 0], "width": 7, "depth": 8, "floors": 2,
        "wall": "stone_bricks", "floor": "oak_planks", "roof": "oak_stairs",
        "stairs": "oak_stairs", "window": "glass", "door": "oak_door", **changes,
    }


def blueprint(*ops: dict[str, Any], version: str = "1.21.11") -> dict[str, Any]:
    return {"formatVersion": 1, "minecraftVersion": version, "name": "building",
            "operations": list(ops)}


def run(data: dict[str, Any]) -> tuple[BuildingOperation, BlockVolume]:
    op = build_operation(data, "operations[0]")
    assert isinstance(op, BuildingOperation)
    ctx = ExecutionContext(BlockVolume(), random.Random(0), {})
    op.apply(ctx)
    return op, ctx.volume


@pytest.mark.parametrize("width", [5, 6, 7, 8])
@pytest.mark.parametrize("floors", [1, 2])
@pytest.mark.parametrize("floor_height", [4, 5, 6])
def test_supported_dimensions_keep_openings_stairs_and_roof_separate(
    width: int, floors: int, floor_height: int
) -> None:
    depth = floor_height + 4 if floors == 2 else 5
    raw = building(width=width, depth=depth, floors=floors, floorHeight=floor_height)
    assert validate(blueprint(raw)) == []
    op, volume = run(raw)
    assert op.bounds() == volume.bounds()
    assert check_support(volume) == []
    x = (width - 1) // 2
    assert op.layout.entrance == Vec3(x, 1, 0)
    assert volume.get(Vec3(x, 1, 0)) == B("oak_door[facing=south,half=lower,hinge=left]")
    assert volume.get(Vec3(x, 2, 0)).get("half") == "upper"
    for arrival in op.layout.arrivals:
        assert volume.get(arrival) == AIR
        assert volume.get(arrival + Vec3(0, 1, 0)) == AIR
        assert volume.get(arrival - Vec3(0, 1, 0)) == B("oak_planks")
    for level in range(floors):
        y = level * floor_height
        # 東・南の窓と、窓下の壁を階段の処理が上書きしない。
        for pos in (Vec3(width - 1, y + 2, (depth - 1) // 2), Vec3(x, y + 2, depth - 1)):
            assert volume.get(pos) == B("glass")
            assert volume.get(pos + Vec3(0, 1, 0)) == B("glass")
            assert volume.get(pos - Vec3(0, 1, 0)) == B("stone_bricks")
        assert volume.get(Vec3(0, y + 2, (depth - 1) // 2)) == B("stone_bricks")
    if floors == 2:
        for i in range(floor_height):
            step = Vec3(1, i + 1, i + 2)
            assert volume.get(step) == B("oak_stairs[facing=south,half=bottom]")
            assert volume.get(step + Vec3(0, 1, 0)) == AIR
            assert volume.get(step + Vec3(0, 2, 0)) == AIR
        assert volume.get(Vec3(1, floor_height, floor_height - 2)) == AIR
        assert volume.get(Vec3(1, floor_height, floor_height - 1)) == AIR
        assert volume.get(Vec3(1, floor_height, floor_height)) == AIR
        assert volume.get(Vec3(2, floor_height, floor_height)) == B("oak_planks")
    # 最上階天井は居住床を覆い、軒は壁から1ブロック張り出す。
    top = floors * floor_height
    assert volume.get(Vec3(2, top, 2)) == B("oak_planks")
    assert op.layout.roof_bounds.min == Vec3(-1, top, -1)
    assert op.layout.roof_bounds.max.x == width
    assert op.layout.roof_bounds.max.z == depth
    assert volume.get(Vec3(-1, top, 0)).id == "minecraft:oak_stairs"


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_rotation_preserves_layout_cells_and_directional_states(angle: int) -> None:
    _, original = run(building())
    position = Vec3(-8, -3, 12)
    op, rotated = run(building(angle=angle, position=position.to_list()))
    transform = Transform.rotation(angle, Vec3(0, 0, 0)).then(Transform.translation(position))
    expected = {transform.apply(pos): transform.apply_state(state) for pos, state in original}
    assert dict(rotated) == expected
    assert op.bounds() == rotated.bounds()
    assert op.layout.entrance == transform.apply(Vec3(3, 1, 0))
    assert op.layout.entry_direction == transform.apply_direction("south")
    assert op.layout.arrivals == tuple(transform.apply(p) for p in (Vec3(3, 1, 1), Vec3(1, 5, 6)))
    assert op.layout.roof_ridge == transform.apply_axis("z")
    assert tuple(face.direction for face in op.layout.faces) == tuple(
        transform.apply_direction(side) for side in ("north", "east", "south", "west")
    )
    assert op.layout.faces[0].bounds == transform.bounds(AABB(Vec3(0, 1, 0), Vec3(6, 8, 0)))


@pytest.mark.parametrize("change", [
    {"width": 4}, {"depth": 4}, {"depth": 7}, {"floorHeight": 3}, {"floors": 0},
    {"floors": 3}, {"angle": 45}, {"roof": "oak_planks"}, {"stairs": "oak_planks"},
    {"roof": "oak_stairs[facing=east]"}, {"stairs": "oak_stairs[half=top]"},
    {"stairs": "oak_stairs[shape=outer_left]"}, {"door": "stone"},
])
def test_rejects_nonfitting_layout_or_material_shape(change: dict[str, Any]) -> None:
    data = building(**change)
    with pytest.raises(BlueprintError):
        build_operation(data, "operations[0]")
    assert validate(blueprint(data))


@pytest.mark.parametrize("key,value", [("angle", True), ("floorHeight", 4.5), ("width", "7"),
                                      ("position", [0.5, 0, 0]), ("extra", 1)])
def test_schema_rejects_invalid_input(key: str, value: Any) -> None:
    assert validate(blueprint(building(**{key: value})))


@pytest.mark.parametrize("role", ["wall", "floor", "roof", "stairs", "window", "door"])
def test_material_is_required_and_validated_against_selected_version(role: str) -> None:
    data = building()
    del data[role]
    assert validate(blueprint(data))
    assert validate(blueprint(building(**{role: "missing_block"})))
    assert validate(blueprint(building(**{role: "oak_planks[missing=true]"})))


def test_version_specific_material() -> None:
    versions = blockdata.supported_versions()
    material = "minecraft:poplar_planks"
    assert validate(blueprint(building(wall=material), version=versions[0]))
    assert validate(blueprint(building(wall=material), version=versions[-1])) == []


def test_matches_independent_handwritten_operation_sequence() -> None:
    raw = building()
    manual = [
        {"type": "room", "from": [0, 0, 0], "to": [6, 4, 7],
         "wall": "stone_bricks", "floor": "oak_planks", "ceiling": "oak_planks",
         "doors": [{"side": "north", "offset": 3, "door": "oak_door"}],
         "windows": [{"side": "east", "height": 2, "block": "glass"},
                     {"side": "south", "height": 2, "block": "glass"}]},
        {"type": "room", "from": [0, 4, 0], "to": [6, 8, 7],
         "wall": "stone_bricks", "floor": "oak_planks", "ceiling": "oak_planks",
         "windows": [{"side": "east", "height": 2, "block": "glass"},
                     {"side": "south", "height": 2, "block": "glass"},
                     {"side": "north", "height": 2, "block": "glass"}]},
        {"type": "stairs", "start": [1, 1, 2], "direction": "south", "height": 4,
         "headroom": 3, "block": "oak_stairs", "base": "oak_planks"},
        {"type": "roof", "from": [0, 8, 0], "to": [6, 8, 7], "style": "gable",
         "ridge": "z", "overhang": 1, "block": "oak_stairs", "gable": "stone_bricks"},
    ]
    assert validate(blueprint(*manual)) == []
    assert dict(generate(load_blueprint_dict(blueprint(raw)))) == dict(
        generate(load_blueprint_dict(blueprint(*manual)))
    )


def test_nested_transform_remains_composable() -> None:
    direct = blueprint(building(position=[3, 2, -7], angle=90))
    nested = blueprint({"type": "translate", "offset": [3, 2, -7], "operations": [
        {"type": "rotate", "angle": 90, "center": [0, 0, 0], "operations": [building()]},
    ]})
    assert validate(nested) == []
    assert dict(generate(load_blueprint_dict(direct))) == dict(
        generate(load_blueprint_dict(nested))
    )


@pytest.mark.parametrize("floors", [None, 1])
def test_unused_stairs_can_be_omitted_for_one_storey(floors: int | None) -> None:
    data = building(floors=1, depth=5)
    del data["stairs"]
    if floors is None:
        del data["floors"]
    assert validate(blueprint(data)) == []
    op, volume = run(data)
    assert len(op.layout.arrivals) == 1
    assert volume.get(Vec3(1, 1, 2)) == AIR


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_internal_transform_preserves_maximum_valid_nesting_depth(angle: int) -> None:
    op = building(position=[3, 2, -7], angle=angle)
    for _ in range(7):
        op = {"type": "translate", "offset": [2, 0, -1], "operations": [op]}
    nested = blueprint(op)
    direct = blueprint(building(position=[17, 2, -14], angle=angle))
    assert validate(nested) == []
    assert dict(generate(load_blueprint_dict(nested))) == dict(
        generate(load_blueprint_dict(direct))
    )


def test_external_nesting_still_rejects_depth_above_limit() -> None:
    op = building()
    for _ in range(8):
        op = {"type": "translate", "offset": [2, 0, -1], "operations": [op]}
    data = blueprint(op)
    assert any("deeper than 8" in error.message for error in validate(data))
    with pytest.raises(BlueprintError, match="deeper than 8"):
        generate(load_blueprint_dict(data))


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("height", [4, 5, 6])
def test_stair_transition_keeps_lower_column_headroom_clear(angle: int, height: int) -> None:
    position = Vec3(-8, 3, 12)
    _, volume = run(building(angle=angle, position=position.to_list(),
                             floorHeight=height, depth=height + 4))
    transform = Transform.rotation(angle, Vec3(0, 0, 0)).then(Transform.translation(position))
    # 昇降境界で身体が残る低い列の追加頭上セルも空ける。
    for lower_feet in (Vec3(1, 1, 1), *(Vec3(1, i + 2, i + 2) for i in range(height - 1))):
        assert volume.get(transform.apply(lower_feet + Vec3(0, 2, 0))) == AIR
