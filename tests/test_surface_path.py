import json
from dataclasses import replace

import pytest

from mcblueprint import loader
from mcblueprint.cli import main
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters.schem import SchemExporter
from mcblueprint.foundation import FoundationSpec, plan_foundation
from mcblueprint.generator import generate, generate_with_report
from mcblueprint.model.block import BlockState
from mcblueprint.model.blueprint import Blueprint
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import BlockSpec
from mcblueprint.operations.path import PathOperation
from mcblueprint.operations.registry import build_operations
from mcblueprint.surface_path import SurfacePathError, SurfacePathSpec, plan_surface_path
from mcblueprint.terrain import TerrainPlacement, TerrainSnapshot
from mcblueprint.validator import validate_and_load, validate_schema

B = BlockState.parse


def terrain(height=lambda x, z: x // 3, *, cells=None) -> TerrainPlacement:
    offset = Vec3(-5, -4, -5)
    blocks = {
        Vec3(x, y, z) - offset: B("stone")
        for x in range(-5, 6) for z in range(-5, 6) for y in range(-4, height(x, z) + 1)
    }
    for pos, state in (cells or {}).items():
        blocks[pos - offset] = B(state)
    snapshot = TerrainSnapshot(AABB(Vec3(0, 0, 0), Vec3(10, 14, 10)), offset,
                               4671, "1.21.11", "0" * 64, blocks)
    return TerrainPlacement(snapshot, snapshot.source_bounds)


def raw_spec(**overrides) -> dict:
    return {
        "points": [[-4, 0], [3, 0]], "entrance": [4, 3, 0], "width": 3,
        "block": "cobblestone", "stairs": "stone_brick_stairs", "clearance": 2,
        "scan": {"minY": -4, "maxY": 10}, "ground": ["stone", "cobblestone"],
        "maxCut": 3, "maxFill": 3, "maxSupportDepth": 3, **overrides,
    }


def spec(**overrides) -> SurfacePathSpec:
    return SurfacePathSpec.from_dict(raw_spec(**overrides))


def model(source, plan, operations=(), foundation=None) -> Blueprint:
    return Blueprint(1, "1.21.11", "surface_path", list(operations), terrain=source,
                     foundation=foundation, surface_path=plan)


@pytest.mark.parametrize("width,expected", [(1, {0}), (2, {0, 1}), (3, {-1, 0, 1})])
def test_flat_full_width_and_existing_generate_contract(width: int, expected: set[int]) -> None:
    source = terrain(lambda x, z: 0)
    plan = plan_surface_path(spec(width=width, entrance=[4, 1, 0]), source)
    assert {pos.z for pos, _ in plan.surfaces} == expected
    assert plan.result.surface_cells == 8 * width + 1
    volume, foundation_result = generate_with_report(model(source, plan))
    assert foundation_result is None
    assert dict(generate(model(source, plan))) == dict(volume)
    assert plan.result.points == (Vec3(-4, 0, 0), Vec3(3, 0, 0))
    assert plan.result.changed_cells == len(plan.writes) == 8 * width + 1
    assert all(state == B("cobblestone") for _, state in plan.surfaces)


def test_slope_stairs_orientation_support_and_counts() -> None:
    source = terrain()
    before = dict(source.snapshot.blocks)
    plan = plan_surface_path(spec(), source)
    volume = generate(model(source, plan))
    assert plan.result.points == (Vec3(-4, -2, 0), Vec3(3, 2, 0))
    stairs = [(pos, state) for pos, state in plan.surfaces if state.id.endswith("_stairs")]
    assert stairs and all(state.get("facing") == "east" for _, state in stairs)
    assert all(volume.get(pos - Vec3(0, 1, 0)).id in {"minecraft:stone", "minecraft:cobblestone"}
               for pos, _ in plan.surfaces)
    assert len({pos for pos, _ in plan.writes}) == len(plan.writes)
    assert sum(volume.get(pos) != source.snapshot.get(source.snapshot.to_local(pos))
               for pos in volume.positions()) == plan.result.changed_cells
    assert dict(source.snapshot.blocks) == before
    assert all(volume.get(Vec3(pos.x, y, pos.z)) == B("air")
               for pos, top in plan.head_tops for y in range(pos.y + 1, top + 1))


def test_descending_stairs_face_uphill() -> None:
    source = terrain()
    plan = plan_surface_path(spec(points=[[3, 0], [-4, 0]], entrance=[-5, -1, 0]), source)
    stairs = [state for _, state in plan.surfaces if state.id.endswith("_stairs")]
    assert stairs and all(state.get("facing") == "east" for state in stairs)
    generate(model(source, plan))


@pytest.mark.parametrize("width", [1, 2, 3])
def test_flat_corner(width: int) -> None:
    source = terrain(lambda x, z: 0)
    plan = plan_surface_path(spec(points=[[-4, 0], [0, 0], [0, 4]],
                                   entrance=[0, 1, 5], width=width), source)
    assert all(pos.y == 0 for pos, _ in plan.surfaces)
    generate(model(source, plan))


def test_sloping_corner_needs_flat_landing() -> None:
    with pytest.raises(SurfacePathError, match="踊り場"):
        plan_surface_path(spec(points=[[-4, 0], [0, 0], [0, 4]], entrance=[0, 1, 5]),
                          terrain(lambda x, z: x // 2))


def test_corner_square_conflict_cannot_be_hidden_by_existing_path_skip() -> None:
    points = [Vec3(*pos) for pos in [
        [0, 0, 0], [9, 0, 0], [9, 1, 7], [18, 1, 7],
        [18, 2, -1], [10, 2, -1], [10, 2, -8],
    ]]
    path = PathOperation("p", points, BlockSpec(block=B("cobblestone")),
                         width=4, stairs=B("stone_brick_stairs"), clearance=2)
    heights = {(op["position"][0], op["position"][2]): op["position"][1]
               for op in path.expand() if op["type"] == "set"}
    offset = Vec3(-3, -4, -12)
    blocks = {
        Vec3(x, y, z) - offset: B("stone")
        for x in range(-3, 23) for z in range(-12, 11)
        for y in range(-4, heights.get((x, z), 0) + 1)
    }
    snapshot = TerrainSnapshot(AABB(Vec3(0, 0, 0), Vec3(25, 14, 22)), offset,
                               4671, "1.21.11", "0" * 64, blocks)
    source = TerrainPlacement(snapshot, snapshot.source_bounds)
    existing = generate(Blueprint(1, "1.21.11", "original", [], terrain=source))
    before = dict(existing)
    with pytest.raises(SurfacePathError, match="角square") as caught:
        plan_surface_path(spec(points=[[p.x, p.z] for p in points], entrance=[10, 3, -9],
                               width=4, maxCut=4, maxFill=4, maxSupportDepth=4), source)
    assert Vec3(10, 0, -1) in {issue.position for issue in caught.value.issues}
    assert dict(snapshot.blocks) == blocks and dict(existing) == before


def test_centre_line_success_does_not_hide_cliff_at_edge() -> None:
    source = terrain(lambda x, z: 0 if z == 0 else -4)
    plan_surface_path(spec(width=1, entrance=[4, 1, 0]), source)
    with pytest.raises(SurfacePathError) as caught:
        plan_surface_path(spec(entrance=[4, 1, 0]), source)
    assert any(issue.position.z != 0 and "fill=4" in issue.reason for issue in caught.value.issues)


@pytest.mark.parametrize("pos,state,reason", [
    (Vec3(-2, 0, 1), "water", "水"), (Vec3(-2, 0, 1), "sand", "対応外"),
    (Vec3(-2, 0, 1), "gravel", "対応外"), (Vec3(-2, 1, 1), "short_grass", "対応外"),
    (Vec3(-2, -2, 1), "air", "空洞"), (Vec3(4, 0, 0), "water", "水"),
])
def test_whole_width_and_final_connection_are_scanned(pos, state, reason) -> None:
    source = terrain(lambda x, z: 0, cells={pos: state})
    before = dict(source.snapshot.blocks)
    with pytest.raises(SurfacePathError, match=reason) as caught:
        plan_surface_path(spec(entrance=[4, 1, 0]), source)
    assert any(issue.position == pos for issue in caught.value.issues)
    assert dict(source.snapshot.blocks) == before


def test_width_outside_acquired_region() -> None:
    source = terrain(lambda x, z: 0)
    source = replace(source, region=AABB(Vec3(-5, -4, 0), Vec3(5, 10, 0)))
    with pytest.raises(SurfacePathError, match="取得範囲外"):
        plan_surface_path(spec(entrance=[4, 1, 0]), source)


def test_cut_and_final_connection_limits() -> None:
    source = terrain(lambda x, z: 4 if x == 0 else 0)
    with pytest.raises(SurfacePathError, match="cut=4"):
        plan_surface_path(spec(entrance=[4, 1, 0]), source)
    with pytest.raises(SurfacePathError, match="fill=4"):
        plan_surface_path(spec(entrance=[4, 5, 0]), terrain(lambda x, z: 0))


def test_exact_cut_limit_and_support_limit() -> None:
    source = terrain(lambda x, z: 4 if x == 0 else 0)
    plan = plan_surface_path(spec(entrance=[4, 1, 0], maxCut=4), source)
    assert plan.result.required_cut == 4
    with pytest.raises(SurfacePathError, match="support=2"):
        plan_surface_path(spec(maxSupportDepth=1), terrain(lambda x, z: 0))


def test_steep_resolved_profile_is_not_automatically_rerouted() -> None:
    with pytest.raises(SurfacePathError, match="rises"):
        plan_surface_path(spec(entrance=[4, 10, 0], maxFill=10, maxSupportDepth=10), terrain())


@pytest.mark.parametrize("scan", [{"minY": -4, "maxY": 4}, {"minY": -5, "maxY": 10}])
def test_scan_must_include_headroom_and_support(scan) -> None:
    with pytest.raises(SurfacePathError):
        plan_surface_path(spec(scan=scan), terrain())


def test_foundation_overlay_used_without_mutation() -> None:
    source = terrain(lambda x, z: 0)
    foundation = plan_foundation(FoundationSpec.from_dict({
        "from": [2, 2, -2], "to": [5, 2, 2], "scan": {"minY": -4, "maxY": 10},
        "maxCut": 2, "maxFill": 2, "maxSupportDepth": 2,
        "ground": ["stone"], "block": "cobblestone",
    }), source)
    before = foundation.writes
    plain = plan_surface_path(spec(), source)
    plan = plan_surface_path(spec(), source, foundation)
    assert plan.result.required_fill < plain.result.required_fill
    assert foundation.writes == before
    blueprint = model(source, plan, foundation=foundation)
    volume, result = generate_with_report(blueprint)
    assert result is foundation.result
    assert volume.get(Vec3(4, 1, 0)) == B("cobblestone")


def test_transition_headroom_checked_after_operations() -> None:
    source = terrain()
    plan = plan_surface_path(spec(), source)
    lower, top = next((pos, top) for pos, top in plan.head_tops if top > pos.y + 2)
    obstruction = lower.with_axis("y", top)
    ops = build_operations([{"type": "set", "position": obstruction.to_list(), "block": "stone"}],
                           "operations")
    with pytest.raises(SurfacePathError, match="昇降遷移") as caught:
        generate(model(source, plan, ops))
    assert obstruction in {issue.position for issue in caught.value.issues}


@pytest.mark.parametrize("block,upper,facing,success", [
    ("oak_door", True, "east", True), ("oak_door", True, "north", False),
    ("oak_door", False, "east", False), ("iron_door", True, "east", False),
    ("copper_door", True, "east", True),
    ("exposed_copper_door", True, "east", True),
    ("weathered_copper_door", True, "east", True),
    ("oxidized_copper_door", True, "east", True),
    ("waxed_copper_door", True, "east", True),
    ("waxed_exposed_copper_door", True, "east", True),
    ("waxed_weathered_copper_door", True, "east", True),
    ("waxed_oxidized_copper_door", True, "east", True),
])
def test_explicit_entrance_door_scope(block, upper, facing, success) -> None:
    source = terrain(lambda x, z: 0)
    plan = plan_surface_path(spec(entrance=[4, 1, 0]), source)
    data = [
        {"type": "set", "position": [4, 0, 0], "block": "oak_planks"},
        {"type": "set", "position": [4, 1, 0], "block": f"{block}[facing={facing}]"},
    ]
    if upper:
        data.append({"type": "set", "position": [4, 2, 0],
                     "block": f"{block}[facing={facing},half=upper]"})
    blueprint = model(source, plan, build_operations(data, "operations"))
    if success:
        generate(blueprint)
    else:
        with pytest.raises(SurfacePathError):
            generate(blueprint)


@pytest.mark.parametrize("field,value", [
    ("facing", "north"), ("open", "true"), ("hinge", "right"), ("powered", "true"),
])
@pytest.mark.parametrize("block", ["oak_door", "copper_door"])
def test_entrance_door_upper_state_must_match(block: str, field: str, value: str) -> None:
    source = terrain(lambda x, z: 0)
    plan = plan_surface_path(spec(entrance=[4, 1, 0]), source)
    upper = B(f"{block}[facing=east,half=upper]").with_property(field, value)
    ops = build_operations([
        {"type": "set", "position": [4, 1, 0], "block": f"{block}[facing=east]"},
        {"type": "set", "position": [4, 2, 0], "block": str(upper)},
    ], "operations")
    with pytest.raises(SurfacePathError, match="上下状態"):
        generate(model(source, plan, ops))


@pytest.mark.parametrize("lower,upper", [
    ("oak_door[facing=east]",
     "oak_door[facing=east,half=upper,open=false,hinge=left,powered=false]"),
    ("oak_door[facing=east,open=true,hinge=right,powered=true]",
     "oak_door[facing=east,half=upper,open=true,hinge=right,powered=true]"),
])
@pytest.mark.parametrize("block", ["oak_door", "copper_door"])
def test_matching_door_states_with_default_properties(block: str, lower: str, upper: str) -> None:
    source = terrain(lambda x, z: 0)
    plan = plan_surface_path(spec(entrance=[4, 1, 0]), source)
    ops = build_operations([
        {"type": "set", "position": [4, 1, 0], "block": lower.replace("oak_door", block)},
        {"type": "set", "position": [4, 2, 0], "block": upper.replace("oak_door", block)},
    ], "operations")
    generate(model(source, plan, ops))


@pytest.mark.parametrize("block", ["oak_door", "copper_door"])
def test_door_facing_and_state_defaults_can_all_be_omitted(block: str) -> None:
    source = terrain(lambda x, z: 0)
    plan = plan_surface_path(spec(points=[[0, 4], [0, -3]], entrance=[0, 1, -4]), source)
    ops = build_operations([
        {"type": "set", "position": [0, 1, -4], "block": block},
        {"type": "set", "position": [0, 2, -4], "block": f"{block}[half=upper]"},
    ], "operations")
    generate(model(source, plan, ops))


@pytest.mark.parametrize("overrides", [
    {"points": [[-4, 0], [3, 1]]}, {"points": [[0, 0], [0, 0]]},
    {"points": [[-4, 0], [0, 0], [3, 0]]}, {"entrance": [5, 3, 0]},
    {"stairs": "stone_brick_stairs[facing=east]"}, {"ground": ["water"]},
    {"stairs": "stone_brick_stairs[waterlogged=true]"}, {"block": "sand"},
])
def test_invalid_spec(overrides) -> None:
    with pytest.raises(BlueprintError):
        spec(**overrides)


def test_unknown_stairs_rejected() -> None:
    with pytest.raises(SurfacePathError, match="Unknown block"):
        plan_surface_path(spec(stairs="unknown_stairs"), terrain())


def test_cli_source_read_once_and_post_operation_failure_is_validation_error(
    tmp_path, monkeypatch, capsys,
):
    source = terrain(lambda x, z: 0)
    volume = generate(Blueprint(1, "1.21.11", "source", [], terrain=source))
    SchemExporter().export(volume, Blueprint(1, "1.21.11", "source", [], terrain=source),
                           tmp_path / "source.schem")
    data = {"formatVersion": 1, "minecraftVersion": "1.21.11", "name": "road",
            "terrain": {"source": "source.schem", "region": {
                "from": [-5, -4, -5], "to": [5, 10, 5]}},
            "surfacePath": raw_spec(entrance=[4, 1, 0]),
            "operations": [{"type": "set", "position": [-4, 0, 0], "block": "cobblestone"}]}
    path = tmp_path / "road.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    original = loader.read_terrain
    reads = []
    def read(path):
        reads.append(path)
        return original(path)
    monkeypatch.setattr(loader, "read_terrain", read)
    assert main(["validate", str(path)]) == 0
    assert len(reads) == 1 and "SurfacePath:" in capsys.readouterr().out
    out = tmp_path / "road.schem"
    assert main(["build", str(path), "-o", str(out), "--strict"]) == 0
    before = out.read_bytes()
    capsys.readouterr()
    before_reads = len(reads)
    assert main(["build", str(path), "--region-size", "4", "8", "4",
                 "-o", str(tmp_path / "regions")]) == 0
    assert len(reads) == before_reads + 1
    assert "SurfacePath:" in capsys.readouterr().out
    data["operations"] = [{"type": "set", "position": [-4, 1, 0], "block": "stone"}]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["build", str(path), "-o", str(out)]) == 1
    assert out.read_bytes() == before and "頭上" in capsys.readouterr().err
    data["terrain"]["protected"] = [{"from": [-2, 0, 1], "to": [-2, 1, 1]}]
    assert "保護" in validate_and_load(data, base_dir=tmp_path)[1][0].message


def test_schema_requires_terrain_and_xz_points() -> None:
    data = {"formatVersion": 1, "minecraftVersion": "1.21.11", "name": "road",
            "surfacePath": raw_spec(),
            "operations": [{"type": "set", "position": [0, 0, 0], "block": "air"}]}
    assert validate_schema(data)
    data["terrain"] = {"source": "a.schem", "region": {"from": [0, 0, 0], "to": [3, 3, 3]}}
    data["surfacePath"]["points"] = [[0, 0, 0], [3, 0, 0]]
    assert validate_schema(data)


def test_final_connection_support_checked_after_operations() -> None:
    source = terrain(lambda x, z: 0)
    plan = plan_surface_path(spec(entrance=[4, 1, 0]), source)
    ops = build_operations([{"type": "set", "position": [4, -1, 0], "block": "air"}],
                           "operations")
    with pytest.raises(SurfacePathError, match="入口接続セルの支持"):
        generate(model(source, plan, ops))
