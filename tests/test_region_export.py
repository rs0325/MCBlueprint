import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import jsonschema
import pytest

from mcblueprint import blockdata
from mcblueprint.cli import main
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters import EXPORTERS
from mcblueprint.generator import generate
from mcblueprint.importers import read_terrain
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.box_like import iter_box
from mcblueprint.region_export import export_regions
from mcblueprint.terrain import TerrainPlacement, TerrainSnapshot
from mcblueprint.volume import BlockVolume

AIR = BlockState.parse("air")
INPUT_HASH = sha256(b"input").hexdigest()
DATA = {
    "formatVersion": 1, "minecraftVersion": "1.21.11", "name": "split",
    "origin": [-8, -3, -7],
    "operations": [
        {"type": "fill", "from": [-3, -1, -2], "to": [3, 0, 2], "block": "dirt"},
        {"type": "roof", "from": [-3, 1, -2], "to": [3, 1, 2],
         "block": "stone_brick_stairs", "style": "gable", "ridge": "x", "overhang": 0},
    ],
}


def assert_bundle(path, volume, blueprint, fmt):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = Path(__file__).parents[1]
    schema = root / "src/mcblueprint/schema/region-manifest.schema.json"
    assert schema.read_bytes() == (root / "schema/region-manifest.schema.json").read_bytes()
    jsonschema.validate(manifest, json.loads(schema.read_text(encoding="utf-8")))
    assert manifest["origin"] == blueprint.origin.to_list()
    assert manifest["inputSha256"] == INPUT_HASH
    cells = {}
    blocks = blockdata.load_block_data(blueprint.minecraft_version)
    for entry in manifest["regions"]:
        file = path.parent / entry["file"]
        assert file.suffix == f".{fmt}"
        assert entry["sha256"] == sha256(file.read_bytes()).hexdigest()
        region = AABB(Vec3(*entry["bounds"]["min"]), Vec3(*entry["bounds"]["max"]))
        snapshot = read_terrain(file)
        assert snapshot.bounds.size == region.size
        assert snapshot.offset == Vec3(*entry["offset"]) == region.min - blueprint.origin
        for pos in iter_box(region):
            assert pos not in cells
            cells[pos] = snapshot.get(pos - region.min)
    bounds = volume.bounds()
    assert set(cells) == set(iter_box(bounds))
    for pos, state in cells.items():
        expected = volume.get(pos) or AIR
        if blueprint.terrain is None:
            expected = blocks.complete(expected)
        assert state == expected
    return manifest


@pytest.mark.parametrize("fmt", ["schem", "litematic"])
@pytest.mark.parametrize("terrain", [False, True])
def test_rejoin_roof_terrain_air_and_partial_edges(tmp_path, fmt, terrain):
    blueprint = load_blueprint_dict(DATA)
    if terrain:
        bounds = AABB(Vec3(-4, -2, -3), Vec3(5, 6, 4))
        snapshot = TerrainSnapshot(
            AABB(Vec3(0, 0, 0), bounds.size - Vec3(1, 1, 1)), bounds.min,
            4671, "1.21.11", INPUT_HASH,
            {Vec3(0, 0, 0): BlockState.parse("oak_log")},
        )
        blueprint.terrain = TerrainPlacement(snapshot, bounds)
    volume = generate(blueprint)
    manifest = assert_bundle(export_regions(
        volume, blueprint, tmp_path / "bundle", region_size=Vec3(3, 2, 3),
        input_sha256=INPUT_HASH, format=fmt,
    ), volume, blueprint, fmt)
    assert manifest["terrainSha256"] == (INPUT_HASH if terrain else None)
    assert any(entry["bounds"]["max"][0] - entry["bounds"]["min"][0] < 2
               for entry in manifest["regions"])


@pytest.mark.parametrize("fmt", ["schem", "litematic"])
def test_sparse_gap_and_all_air(tmp_path, fmt):
    blueprint = load_blueprint_dict(DATA)
    volume = BlockVolume()
    volume.set(Vec3(-3, 0, 0), AIR)
    volume.set(Vec3(3, 0, 0), AIR)
    manifest = assert_bundle(export_regions(
        volume, blueprint, tmp_path / "bundle", region_size=Vec3(2, 2, 2),
        input_sha256=INPUT_HASH, format=fmt,
    ), volume, blueprint, fmt)
    assert len(manifest["regions"]) == 4


def test_terrain_missing_cells_outside_and_protected(tmp_path):
    blueprint = load_blueprint_dict(DATA)
    bounds = AABB(Vec3(0, 0, 0), Vec3(2, 0, 0))
    snapshot = TerrainSnapshot(bounds, Vec3(0, 0, 0), 4671, "1.21.11", INPUT_HASH, {})
    blueprint.terrain = TerrainPlacement(snapshot, bounds)
    volume = BlockVolume()
    volume.set(bounds.min, AIR)
    volume.set(bounds.max, AIR)
    with pytest.raises(BlueprintError, match="未取得"):
        export_regions(volume, blueprint, tmp_path / "unknown", region_size=Vec3(1, 1, 1),
                       input_sha256=INPUT_HASH)
    volume.set(Vec3(1, 0, 0), AIR)
    blueprint.terrain = replace(blueprint.terrain, region=AABB(bounds.min, Vec3(1, 0, 0)))
    with pytest.raises(BlueprintError, match="一致"):
        export_regions(volume, blueprint, tmp_path / "outside", region_size=Vec3(1, 1, 1),
                       input_sha256=INPUT_HASH)
    with pytest.raises(ValueError, match="保護"):
        TerrainPlacement(snapshot, bounds, (bounds,))
    assert not list(tmp_path.iterdir())


def test_failure_and_existing_output_preserved(tmp_path, monkeypatch):
    blueprint = load_blueprint_dict(DATA)
    volume = generate(blueprint)
    exporter = EXPORTERS["schem"]
    original = exporter.export
    calls = 0

    def fail(self, *args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("write failed")
        original(self, *args)

    monkeypatch.setattr(exporter, "export", fail)
    destination = tmp_path / "bundle"
    with pytest.raises(BlueprintError, match="write failed"):
        export_regions(volume, blueprint, destination, region_size=Vec3(3, 2, 3),
                       input_sha256=INPUT_HASH)
    assert not list(tmp_path.iterdir())
    destination.mkdir()
    (destination / "keep").write_bytes(b"keep")
    with pytest.raises(BlueprintError, match="既に存在"):
        export_regions(volume, blueprint, destination, region_size=Vec3(3, 2, 3),
                       input_sha256=INPUT_HASH)
    assert (destination / "keep").read_bytes() == b"keep"


@pytest.mark.parametrize("fmt", ["schem", "litematic"])
def test_cli_manifest_hash_overrides_and_extension_is_directory(tmp_path, fmt):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(DATA), encoding="utf-8")
    out = tmp_path / "bundle.schem"
    assert main(["build", str(source), "--region-size", "3", "2", "3", "--format", fmt,
                 "--seed", "12", "-o", str(out)]) == 0
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["inputSha256"] == sha256(source.read_bytes()).hexdigest()
    assert manifest["seed"] == 12
    assert all(entry["file"].endswith(f".{fmt}") for entry in manifest["regions"])
    assert main(["build", str(source), "--region-size", "0", "2", "3",
                 "-o", str(tmp_path / "bad")]) == 2
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("size", [Vec3(0, 1, 1), Vec3(-1, 1, 1), Vec3(True, 1, 1)])
def test_invalid_dimensions_and_empty_volume(tmp_path, size):
    blueprint = load_blueprint_dict(DATA)
    with pytest.raises(BlueprintError, match="正整数"):
        export_regions(generate(blueprint), blueprint, tmp_path / "bad", region_size=size,
                       input_sha256=INPUT_HASH)
    with pytest.raises(BlueprintError, match="ありません"):
        export_regions(BlockVolume(), blueprint, tmp_path / "empty", region_size=Vec3(1, 1, 1),
                       input_sha256=INPUT_HASH)
    assert not list(tmp_path.iterdir())


def test_input_json_and_terrain_are_snapshots(tmp_path, monkeypatch):
    from mcblueprint import cli

    source = tmp_path / "source.schem"
    blueprint = load_blueprint_dict(DATA)
    EXPORTERS["schem"]().export(generate(blueprint), blueprint, source)
    data = {**DATA, "terrain": {
        "source": source.name,
        "region": {"from": [-3, -1, -2], "to": [3, 3, 2]},
    }, "origin": [0, 0, 0], "operations": [
        {"type": "set", "position": [0, 0, 0], "block": "air"},
    ]}
    # 元ファイルの貼付基準へ施工座標を合わせる。
    imported = read_terrain(source)
    data["terrain"]["region"] = {
        "from": imported.source_bounds.min.to_list(),
        "to": imported.source_bounds.max.to_list(),
    }
    data["operations"][0]["position"] = imported.source_bounds.min.to_list()
    path = tmp_path / "input.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    original_json_hash = sha256(path.read_bytes()).hexdigest()
    original_terrain_hash = sha256(source.read_bytes()).hexdigest()
    validate = cli.validate_and_load
    export = cli.export_regions

    def validate_after_json_changes(raw, **kwargs):
        path.write_text("{}", encoding="utf-8")
        return validate(raw, **kwargs)

    def export_after_terrain_removed(volume, blueprint, out_dir, **kwargs):
        source.unlink()
        return export(volume, blueprint, out_dir, **kwargs)

    monkeypatch.setattr(cli, "validate_and_load", validate_after_json_changes)
    monkeypatch.setattr(cli, "export_regions", export_after_terrain_removed)
    destination = tmp_path / "bundle"
    assert main(["build", str(path), "--region-size", "3", "2", "3",
                 "-o", str(destination)]) == 0
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["inputSha256"] == original_json_hash
    assert manifest["terrainSha256"] == original_terrain_hash
    assert manifest["bounds"]["min"] == imported.source_bounds.min.to_list()
