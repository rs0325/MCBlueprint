import json
from pathlib import Path

import pytest

from mcblueprint import loader
from mcblueprint.cli import main
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters.schem import SchemExporter
from mcblueprint.foundation import FoundationError, FoundationSpec, plan_foundation
from mcblueprint.generator import generate, generate_with_report
from mcblueprint.model.block import BlockState
from mcblueprint.model.blueprint import Blueprint
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.box_like import iter_box
from mcblueprint.terrain import TerrainPlacement, TerrainSnapshot
from mcblueprint.validator import validate, validate_and_load, validate_schema

B = BlockState.parse


def terrain(
    heights: tuple[int, ...] = (-1, 0, 1), *, cells: dict | None = None,
) -> TerrainPlacement:
    offset = Vec3(-2, -3, 4)
    blocks = {
        Vec3(x, y + 3, z): B("stone")
        for x, height in enumerate(heights) for z in range(2) for y in range(-3, height + 1)
    }
    if cells:
        for pos, state in cells.items():
            blocks[pos - offset] = B(state)
    snapshot = TerrainSnapshot(AABB(Vec3(0, 0, 0), Vec3(len(heights) - 1, 7, 1)),
                               offset, 4671, "1.21.11", "0" * 64, blocks)
    return TerrainPlacement(snapshot, snapshot.source_bounds)


def raw_spec() -> dict:
    return {
        "from": [-2, 0, 4], "to": [0, 0, 5], "scan": {"minY": -3, "maxY": 4},
        "maxCut": 1, "maxFill": 1, "maxSupportDepth": 1,
        "ground": ["stone"], "block": "cobblestone",
    }


def spec(**overrides) -> FoundationSpec:
    return FoundationSpec.from_dict({**raw_spec(), **overrides})


def blueprint_data() -> dict:
    return {
        "formatVersion": 1, "minecraftVersion": "1.21.11", "name": "foundation",
        "terrain": {"source": "source.schem", "region": {
            "from": [-2, -3, 4], "to": [0, 4, 5],
        }}, "foundation": raw_spec(),
        "operations": [{"type": "set", "position": [-1, 1, 4], "block": "air"}],
    }


def save_source(tmp_path: Path, source: TerrainPlacement) -> Path:
    volume = generate(Blueprint(1, "1.21.11", "source", [], terrain=source))
    path = tmp_path / "source.schem"
    SchemExporter().export(volume, Blueprint(1, "1.21.11", "source", [], terrain=source), path)
    return path


def test_plan_counts_and_flat_supported_floor() -> None:
    original = terrain()
    before = dict(original.snapshot.blocks)
    plan = plan_foundation(spec(), original)
    assert dict(original.snapshot.blocks) == before
    assert plan.result.to_json() == {
        "from": [-2, 0, 4], "to": [0, 0, 5], "floorY": 0, "entranceY": 1,
        "cutCells": 2, "fillCells": 0, "floorCells": 6, "changedCells": 8,
        "requiredCut": 1, "requiredFill": 1, "requiredSupportDepth": 1,
    }
    assert len(plan.writes) == len({pos for pos, _ in plan.writes}) == plan.result.changed_cells
    assert {state for _, state in plan.writes} == {B("air"), B("cobblestone")}
    blueprint = Blueprint(1, "1.21.11", "foundation", [], terrain=original, foundation=plan)
    volume, result = generate_with_report(blueprint)
    assert result is plan.result
    assert dict(generate(blueprint)) == dict(volume)
    changed = 0
    for pos in iter_box(original.region):
        if volume.get(pos) != original.snapshot.get(original.snapshot.to_local(pos)):
            changed += 1
    assert changed == 8
    for x in range(-2, 1):
        for z in (4, 5):
            assert volume.get(Vec3(x, 0, z)) == B("cobblestone")
            assert volume.get(Vec3(x, 1, z)) == B("air")
            assert volume.get(Vec3(x, -1, z)).id in {"minecraft:stone", "minecraft:cobblestone"}


@pytest.mark.parametrize("heights,expected", [((0, 0, 0), (0, 0, 6, 1)),
                                                    ((-2, -2, -2), (0, 6, 6, 2))])
def test_flat_and_fill_depth(heights: tuple[int, ...], expected: tuple[int, ...]) -> None:
    plan = plan_foundation(spec(maxFill=2, maxSupportDepth=2), terrain(heights))
    result = plan.result
    assert (result.cut_cells, result.fill_cells, result.floor_cells,
            result.required_support_depth) == expected


def test_existing_equal_material_is_not_counted_as_changed() -> None:
    plan = plan_foundation(spec(block="stone"), terrain((0, 0, 0)))
    assert plan.writes == () and plan.result.changed_cells == 0


@pytest.mark.parametrize("overrides,heights,expected", [
    ({"maxCut": 0}, (0, 0, 1), (1, 0, 1)),
    ({"maxFill": 0}, (0, 0, -1), (0, 1, 1)),
    ({"maxFill": 2}, (0, 0, -2), (0, 2, 2)),
])
def test_depth_limit_rejections_are_atomic(
    overrides: dict, heights: tuple, expected: tuple,
) -> None:
    original = terrain(heights)
    blueprint = Blueprint(1, "1.21.11", "old", [], terrain=original)
    volume = generate(blueprint)
    before = dict(volume)
    with pytest.raises(FoundationError) as caught:
        plan_foundation(spec(**overrides), original)
    assert dict(volume) == before
    assert len(caught.value.issues) == 2
    issue = caught.value.issues[0]
    assert issue.position.x == 0
    assert (issue.required_cut, issue.required_fill, issue.required_support_depth) == expected


@pytest.mark.parametrize("position,state,reason", [
    (Vec3(-2, -2, 4), "air", "空洞"),
    (Vec3(-2, -1, 4), "water", "対応外"),
    (Vec3(-2, -1, 4), "sand", "対応外"),
    (Vec3(-2, -1, 4), "gravel", "対応外"),
    (Vec3(-2, 0, 4), "short_grass", "対応外"),
    (Vec3(-2, -1, 4), "unknown_block", "対応外"),
])
def test_unsupported_cells(position: Vec3, state: str, reason: str) -> None:
    original = terrain(cells={position: state})
    before = dict(original.snapshot.blocks)
    with pytest.raises(FoundationError, match=reason) as caught:
        plan_foundation(spec(), original)
    assert caught.value.issues[0].position == position
    assert dict(original.snapshot.blocks) == before


def test_all_columns_are_checked_before_any_changes() -> None:
    original = terrain(cells={Vec3(-2, -1, 4): "water", Vec3(0, 2, 5): "short_grass"})
    with pytest.raises(FoundationError) as caught:
        plan_foundation(spec(), original)
    assert {issue.position for issue in caught.value.issues} == {Vec3(-2, -1, 4), Vec3(0, 2, 5)}


@pytest.mark.parametrize("overrides", [
    {"from": [-2, 1, 4]}, {"scan": {"minY": 0, "maxY": 4}},
    {"scan": {"minY": -3, "maxY": 0}}, {"ground": ["sand"]},
    {"ground": ["water"]}, {"block": "gravel"}, {"ground": ["stone[bad=true]"]},
])
def test_invalid_spec(overrides: dict) -> None:
    with pytest.raises(BlueprintError):
        spec(**overrides)


@pytest.mark.parametrize("scan", [{"minY": -4, "maxY": 4}, {"minY": -3, "maxY": 5}])
def test_scan_must_be_acquired(scan: dict) -> None:
    with pytest.raises(FoundationError, match="範囲外") as caught:
        plan_foundation(spec(scan=scan), terrain())
    assert not terrain().region.contains(caught.value.issues[0].position)


def test_surface_must_be_inside_declared_scan() -> None:
    with pytest.raises(FoundationError, match="地表未確定"):
        plan_foundation(spec(maxCut=5), terrain((4, 4, 4)))
    with pytest.raises(FoundationError, match="支持地盤"):
        plan_foundation(spec(maxFill=5, maxSupportDepth=5), terrain((-4, -4, -4)))


def test_plan_used_once_and_source_frozen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = save_source(tmp_path, terrain())
    data = blueprint_data()
    reads = []
    reader = loader.read_terrain
    def read(path):
        reads.append(path)
        return reader(path)
    monkeypatch.setattr(loader, "read_terrain", read)
    blueprint, errors = validate_and_load(data, base_dir=tmp_path)
    assert not errors and blueprint is not None
    assert reads == [source]
    source.unlink()
    first, result = generate_with_report(blueprint)
    second, second_result = generate_with_report(blueprint)
    assert dict(first) == dict(second) and result is second_result
    assert reads == [source]


def test_cli_report_and_refusal_preserves_output(tmp_path: Path, capsys) -> None:
    save_source(tmp_path, terrain())
    path = tmp_path / "foundation.json"
    data = blueprint_data()
    path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "result.schem"
    assert main(["validate", str(path), "--strict"]) == 0
    assert '"entranceY": 1' in capsys.readouterr().out
    assert main(["build", str(path), "-o", str(out)]) == 0
    previous = out.read_bytes()
    capsys.readouterr()
    assert main(["build", str(path), "--region-size", "4", "8", "4",
                 "-o", str(tmp_path / "regions")]) == 0
    output = capsys.readouterr().out
    assert "Foundation:" in output and '"entranceY": 1' in output
    data["foundation"]["maxCut"] = 0
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["build", str(path), "-o", str(out)]) == 1
    assert out.read_bytes() == previous
    assert "cut=1" in capsys.readouterr().out


def test_protected_footprint_rejected(tmp_path: Path) -> None:
    save_source(tmp_path, terrain())
    data = blueprint_data()
    data["terrain"]["protected"] = [{"from": [-2, 0, 4], "to": [-2, 1, 4]}]
    assert "保護" in validate(data, base_dir=tmp_path)[0].message


@pytest.mark.parametrize("edit", ["terrain", "from", "maxCut", "unknown"])
def test_foundation_schema(edit: str) -> None:
    data = blueprint_data()
    if edit == "terrain":
        data.pop("terrain")
    elif edit == "from":
        data["foundation"]["from"] = [0, 0]
    elif edit == "maxCut":
        data["foundation"]["maxCut"] = -1
    else:
        data["foundation"]["search"] = True
    assert validate_schema(data)
