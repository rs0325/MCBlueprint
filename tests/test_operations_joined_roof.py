import copy
import random
from collections import Counter
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model import BlockState, Vec3
from mcblueprint.operations import ExecutionContext, build_operation
from mcblueprint.operations.join_buildings import JoinBuildingsOperation
from mcblueprint.operations.roof import RoofOperation
from mcblueprint.operations.transform import Transform
from mcblueprint.validator import validate
from mcblueprint.volume import BlockVolume

B = BlockState.parse


def joined_roof(
    width: int = 7, depths: tuple[int, int] = (10, 11), floors: int = 2,
) -> dict[str, Any]:
    a = {
        "type": "building", "position": [0, 0, 0], "width": width, "depth": depths[0],
        "floors": floors, "floorHeight": 4, "wall": "stone_bricks", "floor": "oak_planks",
        "roof": "oak_stairs", "stairs": "oak_stairs", "window": "glass", "door": "oak_door",
    }
    b = {**a, "position": [width - 1, 0, sum(depths) - 2], "angle": 180,
         "depth": depths[1], "wall": "bricks"}
    return {
        "type": "join_buildings", "buildings": [a, b], "faces": ["south", "north"],
        "wall": "quartz_block", "openings": [
            {"floor": floor, "offset": (width - 1) // 2} for floor in range(floors)
        ], "joinRoof": True,
    }


def blueprint(op: dict[str, Any]) -> dict[str, Any]:
    return {"formatVersion": 1, "minecraftVersion": "1.21.11", "name": "joined_roof",
            "operations": [op]}


def run(
    raw: dict[str, Any], volume: BlockVolume | None = None,
) -> tuple[JoinBuildingsOperation, BlockVolume]:
    op = build_operation(raw, "operations[0]")
    assert isinstance(op, JoinBuildingsOperation)
    volume = volume if volume is not None else BlockVolume()
    op.apply(ExecutionContext(volume, random.Random(0), {}))
    return op, volume


class CountedVolume(BlockVolume):
    def __init__(self) -> None:
        super().__init__()
        self.writes: Counter[Vec3] = Counter()

    def set(self, pos: Vec3, state: BlockState) -> None:
        self.writes[pos] += 1
        super().set(pos, state)


def expected_roof(width: int, length: int, y: int) -> dict[Vec3, BlockState]:
    # 既存roofの段勾配を、外周2面の材質を分けた独立した期待形状として表す。
    expected = {}
    for layer in range((width + 3) // 2):
        left, right = -1 + layer, width - layer
        if left > right:
            break
        for z in range(-1, length + 1):
            if left == right:
                expected[Vec3(left, y + layer, z)] = B("oak_slab[type=bottom]")
            else:
                expected[Vec3(left, y + layer, z)] = B("oak_stairs[facing=east,half=bottom]")
                expected[Vec3(right, y + layer, z)] = B("oak_stairs[facing=west,half=bottom]")
    for layer in range((width + 1) // 2):
        for x in range(layer, width - layer):
            expected[Vec3(x, y + layer, 0)] = B("stone_bricks")
            expected[Vec3(x, y + layer, length - 1)] = B("bricks")
    return expected


@pytest.mark.parametrize("width", (5, 6, 7, 8))
@pytest.mark.parametrize("depths", ((8, 8), (10, 13)))
@pytest.mark.parametrize("floors", (1, 2))
def test_surface_ridge_outer_gables_and_seam_match_continuous_roof(
    width: int, depths: tuple[int, int], floors: int,
) -> None:
    raw = joined_roof(width, depths, floors)
    assert validate(blueprint(raw)) == []
    counted = CountedVolume()
    op, volume = run(raw, counted)
    top, length = floors * 4, sum(depths) - 1
    expected = expected_roof(width, length, top)
    actual = {p: s for p, s in volume if p.y > top}
    assert actual == {p: s for p, s in expected.items() if p.y > top}
    for pos, state in expected.items():
        assert volume.get(pos) == state
        if pos.y > top:
            assert counted.writes[pos] == 1
    # 内部妻面にairで削除するセルを作らず、共通屋根だけを配置する。
    assert not any(s.id == "minecraft:air" and p.y >= top for p, s in volume)
    for x in range(width):
        for y in range(top + 1):
            assert counted.writes[Vec3(x, y, depths[0] - 1)] == 1
    assert op.bounds() == volume.bounds()


def test_individual_roof_operations_are_not_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    paths = []
    original = RoofOperation.apply

    def tracked(self: RoofOperation, ctx: ExecutionContext) -> None:
        paths.append(self.path)
        original(self, ctx)

    monkeypatch.setattr(RoofOperation, "apply", tracked)
    run(joined_roof())
    assert paths == ["operations[0]<joined-roof>"]


def test_disabled_or_omitted_option_preserves_independent_roofs() -> None:
    raw = joined_roof()
    raw["joinRoof"] = False
    _, explicit = run(raw)
    del raw["joinRoof"]
    _, implicit = run(raw)
    assert dict(explicit) == dict(implicit)
    assert implicit.get(Vec3(3, 10, 9)) == B("bricks")


@pytest.mark.parametrize("reverse", (False, True))
def test_connecting_either_end_preserves_outer_owner_materials(reverse: bool) -> None:
    raw = joined_roof(depths=(9, 12))
    if reverse:
        raw["buildings"].reverse()
        raw["faces"].reverse()
    assert validate(blueprint(raw)) == []
    _, volume = run(raw)
    top, length = 8, 20
    expected = expected_roof(7, length, top)
    actual = {p: s for p, s in volume if p.y > top}
    assert actual == {p: s for p, s in expected.items() if p.y > top}


@pytest.mark.parametrize("angle", (0, 90, 180, 270))
def test_individual_180_and_whole_rotation_keep_states_and_layout(angle: int) -> None:
    raw = joined_roof()
    op, original = run(raw)
    transform = Transform.rotation(angle, Vec3(0, 0, 0)).then(
        Transform.translation(Vec3(-8, -3, 4))
    )
    changed = copy.deepcopy(raw)
    for item in changed["buildings"]:
        item["position"] = transform.apply(Vec3.from_seq(item["position"])).to_list()
        item["angle"] = (item.get("angle", 0) + angle) % 360
    changed["faces"] = [transform.apply_direction(face) for face in changed["faces"]]
    if angle in (180, 270):
        for opening in changed["openings"]:
            opening["offset"] = 7 - opening["offset"] - opening.get("width", 1)
    assert validate(blueprint(changed)) == []
    rotated_op, rotated = run(changed)
    assert dict(rotated) == {transform.apply(p): transform.apply_state(s) for p, s in original}
    assert rotated_op.layout.shared_face.bounds == transform.bounds(op.layout.shared_face.bounds)


def test_outer_transform_and_maximum_nesting_do_not_consume_internal_depth() -> None:
    raw = joined_roof()
    _, original = run(raw)
    nested = {"type": "rotate", "angle": 90, "center": [0, 0, 0], "operations": [raw]}
    for _ in range(6):
        nested = {"type": "translate", "offset": [1, 0, -1], "operations": [nested]}
    assert validate(blueprint(nested)) == []
    volume = generate(load_blueprint_dict(blueprint(nested)))
    transform = Transform.rotation(90, Vec3(0, 0, 0)).then(Transform.translation(Vec3(6, 0, -6)))
    assert dict(volume) == {transform.apply(p): transform.apply_state(s) for p, s in original}
    too_deep = {"type": "translate", "offset": [0, 0, 0], "operations": [nested]}
    assert validate(blueprint(too_deep))


@pytest.mark.parametrize(
    "kind",
    ("width", "material", "offset", "ridge", "side", "floors", "height", "stairs", "entrance"),
)
def test_unsupported_or_interfering_layout_fails_before_any_placement(kind: str) -> None:
    raw = joined_roof()
    if kind == "width":
        raw["buildings"][1]["width"] = 6
    elif kind == "material":
        raw["buildings"][1]["roof"] = "spruce_stairs"
    elif kind == "offset":
        raw["buildings"][1]["position"][0] += 1
    elif kind == "ridge":
        raw = joined_roof(floors=1)
        raw["buildings"][1].update(angle=90, position=[6, 0, 9])
    elif kind == "side":
        raw["buildings"][1].update(angle=0, position=[6, 0, 0])
        raw["faces"] = ["east", "west"]
        raw["openings"] = [{"offset": 7}]
    elif kind == "floors":
        raw["buildings"][1]["floors"] = 1
    elif kind == "height":
        raw["buildings"][1]["floorHeight"] = 5
    elif kind == "stairs":
        raw = joined_roof(width=5, depths=(8, 8))
        raw["openings"] = [{"offset": 1}]
    else:
        raw["buildings"][1].update(angle=0, position=[0, 0, 9])
    volume = CountedVolume()
    with pytest.raises(BlueprintError):
        build_operation(raw, "operations[0]").apply(ExecutionContext(volume, random.Random(0), {}))
    assert len(volume) == 0 and not volume.writes
    assert validate(blueprint(raw))


@pytest.mark.parametrize("value", (1, "true", {}, None))
def test_schema_rejects_non_boolean_switch(value: Any) -> None:
    raw = joined_roof()
    raw["joinRoof"] = value
    assert validate(blueprint(raw))


@pytest.mark.parametrize("field", ("pitch", "overhang", "style"))
def test_unexposed_roof_parameters_are_not_silently_approximated(field: str) -> None:
    raw = joined_roof()
    raw["buildings"][0][field] = 2
    assert validate(blueprint(raw))


@pytest.mark.parametrize("name", ("odd", "even", "odd_independent", "even_independent"))
def test_fixed_joined_roof_fixtures(name: str) -> None:
    from pathlib import Path

    from mcblueprint.loader import load_blueprint, read_blueprint_json

    path = Path(__file__).parent / "data" / f"joined_roof_{name}.json"
    assert validate(read_blueprint_json(path)) == []
    volume = generate(load_blueprint(path))
    assert volume.bounds() is not None


def test_joining_roof_keeps_living_floors_openings_and_headroom_unchanged() -> None:
    raw = joined_roof()
    _, joined = run(raw)
    raw["joinRoof"] = False
    _, independent = run(raw)
    assert {p: s for p, s in joined if p.y <= 8} == {
        p: s for p, s in independent if p.y <= 8
    }
