import json
from pathlib import Path

import pytest
from nbtlib import ByteArray, Compound, File, Int, IntArray, List, Short

from mcblueprint import generator, loader, validator
from mcblueprint.cli import main
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters import EXPORTERS
from mcblueprint.generator import generate
from mcblueprint.importers import read_terrain
from mcblueprint.loader import load_blueprint, load_blueprint_dict
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.box_like import iter_box
from mcblueprint.validator import validate, validate_and_load
from mcblueprint.volume import BlockVolume

B = BlockState.parse
REGION = {"from": [-4, 7, -2], "to": [-1, 8, -1]}


def source(
    tmp_path: Path, *, version: int = 4671, state: str = "oak_stairs[facing=east,half=top]",
) -> Path:
    path = tmp_path / "source.schem"
    root = Compound({
        "Version": Int(2), "DataVersion": Int(version),
        "Width": Short(4), "Height": Short(2), "Length": Short(2),
        "Offset": IntArray([-4, 7, -2]),
        "Palette": Compound({"minecraft:air": Int(0), "minecraft:stone": Int(1),
                             f"minecraft:{state}": Int(2)}),
        "BlockData": ByteArray([1, 2, 0, 0] + [0] * 12),
    })
    File(root, gzipped=True, root_name="Schematic").save(str(path))
    return path


def data(operations: list[dict] | None = None) -> dict:
    return {
        "formatVersion": 1, "minecraftVersion": "1.21.11", "name": "terrain_build",
        "origin": [3, -2, 5],
        "terrain": {"source": "source.schem", "region": REGION},
        "operations": operations or [
            {"type": "set", "position": [-4, 7, -2], "block": "diamond_block"},
            {"type": "copy", "from": [-3, 7, -2], "to": [-3, 7, -2], "offset": [1, 0, 0]},
            {"type": "replace", "from": [-2, 7, -2], "to": [-2, 7, -2],
             "match": "oak_stairs[facing=east]", "block": "oak_log[axis=x]"},
            {"type": "set", "position": [-4, 7, -2], "block": "air"},
        ],
    }


def test_composition_copy_replace_and_snapshot(tmp_path: Path) -> None:
    path = source(tmp_path)
    original = path.read_bytes()
    blueprint, errors = validate_and_load(data(), base_dir=tmp_path)
    assert not errors and blueprint is not None and blueprint.terrain is not None
    snapshot = blueprint.terrain.snapshot
    before = dict(snapshot.blocks)
    volume = generate(blueprint)
    assert volume.bounds() == AABB.of(Vec3(-4, 7, -2), Vec3(-1, 8, -1))
    assert len(volume) == 16
    assert volume.get(Vec3(-4, 7, -2)) == B("air")
    assert volume.get(Vec3(-3, 7, -2)) == B("oak_stairs[facing=east,half=top]")
    assert volume.get(Vec3(-2, 7, -2)) == B("oak_log[axis=x]")
    volume.set(Vec3(-1, 8, -1), B("gold_block"))
    assert generate(blueprint).get(Vec3(-1, 8, -1)) == B("air")
    assert dict(snapshot.blocks) == before and path.read_bytes() == original
    source(tmp_path, state="oak_log[axis=y]")
    assert generate(blueprint).get(Vec3(-3, 7, -2)) == B("oak_stairs[facing=east,half=top]")
    reloaded = load_blueprint_dict(data(), base_dir=tmp_path)
    assert generate(reloaded).get(Vec3(-3, 7, -2)) == B("oak_log[axis=y]")


def test_regeneration_after_removing_operation(tmp_path: Path) -> None:
    source(tmp_path)
    edited = data([{"type": "set", "position": [-1, 8, -1], "block": "gold_block"}])
    old = generate(load_blueprint_dict(edited, base_dir=tmp_path))
    assert old.get(Vec3(-1, 8, -1)) == B("gold_block")
    rebuilt = generate(load_blueprint_dict(data(), base_dir=tmp_path))
    assert rebuilt.get(Vec3(-1, 8, -1)) == B("air")


def test_all_air_source_remains_acquired(tmp_path: Path) -> None:
    path = source(tmp_path)
    root = File.load(str(path), gzipped=True)
    root["BlockData"] = ByteArray([0] * 16)
    root.save(str(path))
    blueprint = load_blueprint_dict(data([{"type": "fill", **REGION, "block": "air"}]),
                                    base_dir=tmp_path)
    volume = generate(blueprint)
    assert volume.bounds().size == Vec3(4, 2, 2)
    assert len(volume) == 16 and all(state == B("air") for _, state in volume)


@pytest.mark.parametrize("fmt", ["schem", "litematic"])
@pytest.mark.parametrize("all_air", [False, True])
def test_roundtrip_all_cells_and_offset(tmp_path: Path, fmt: str, all_air: bool) -> None:
    source(tmp_path)
    ops = [{"type": "fill", **REGION, "block": "air"}] if all_air else None
    blueprint = load_blueprint_dict(data(ops), base_dir=tmp_path)
    volume = generate(blueprint)
    out = tmp_path / f"result.{fmt}"
    EXPORTERS[fmt]().export(volume, blueprint, out)
    restored = read_terrain(out)
    assert restored.bounds.size == Vec3(4, 2, 2)
    assert restored.offset == Vec3(-7, 9, -7)
    for pos in iter_box(blueprint.terrain.region):
        assert restored.get(pos - blueprint.terrain.region.min) == volume.get(pos)
    if all_air:
        assert not restored.blocks


@pytest.mark.parametrize("field,value,message", [
    ("region", {"from": [-5, 7, -2], "to": [-1, 8, -1]}, "取得範囲外"),
    ("protected", [{"from": [-1, 8, -1], "to": [3, 9, 3]}], "保護範囲"),
])
def test_reject_region(tmp_path: Path, field: str, value: object, message: str) -> None:
    source(tmp_path)
    blueprint = data()
    blueprint["terrain"][field] = value
    assert message in validate(blueprint, base_dir=tmp_path)[0].message


def test_protected_outside_and_reversed_corners(tmp_path: Path) -> None:
    source(tmp_path)
    blueprint = data()
    blueprint["terrain"]["region"] = {"from": REGION["to"], "to": REGION["from"]}
    blueprint["terrain"]["protected"] = [{"from": [0, 7, -2], "to": [0, 8, -1]}]
    assert validate(blueprint, base_dir=tmp_path) == []


@pytest.mark.parametrize("ops", [
    [{"type": "set", "position": [0, 7, -2], "block": "stone"}],
    [{"type": "copy", "from": [-5, 7, -2], "to": [-5, 7, -2], "offset": [1, 0, 0]}],
    [{"type": "translate", "offset": [5, 0, 0], "operations": [
        {"type": "set", "position": [-3, 7, -2], "block": "stone"}]}],
])
def test_operation_outside_is_rejected(tmp_path: Path, ops: list[dict]) -> None:
    source(tmp_path)
    assert "terrain.region 外" in validate(data(ops), base_dir=tmp_path)[0].message


@pytest.mark.parametrize("state", ["unknown_block", "stone[bad=true]", "oak_log[axis=wrong]"])
def test_unpreservable_states(tmp_path: Path, state: str) -> None:
    source(tmp_path, state=state)
    assert "terrain.source" in validate(data(), base_dir=tmp_path)[0].message


@pytest.mark.parametrize("version", [1, 999999, 4844])
def test_version_must_match(tmp_path: Path, version: int) -> None:
    source(tmp_path, version=version)
    assert "DataVersion" in validate(data(), base_dir=tmp_path)[0].message


def test_attached_data_rejected(tmp_path: Path) -> None:
    path = source(tmp_path)
    root = File.load(str(path), gzipped=True)
    root["BlockEntities"] = List[Compound]([Compound({"x": Int(0)})])
    root.save(str(path))
    assert "BlockEntities" in validate(data(), base_dir=tmp_path)[0].message


def test_air_cells_count_towards_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source(tmp_path)
    assert "maximum dimension" in validate(data(), base_dir=tmp_path, max_dimension=3)[0].message
    monkeypatch.setattr(validator, "MAX_VOLUME", 15)
    assert "bounding box" in validate(data(), base_dir=tmp_path)[0].message
    blueprint = load_blueprint_dict(data(), base_dir=tmp_path)
    monkeypatch.setattr(generator, "MAX_VOLUME", 15)
    with pytest.raises(BlueprintError, match="airを含む"):
        generate(blueprint)


def test_write_bounds() -> None:
    volume = BlockVolume(write_bounds=AABB(Vec3(0, 0, 0), Vec3(1, 1, 1)))
    with pytest.raises(BlueprintError, match="施工範囲外"):
        volume.set(Vec3(2, 0, 0), B("air"))


@pytest.mark.parametrize("command, flags", [
    ("validate", []), ("validate", ["--json"]),
    ("validate", ["--json", "--strict", "--kind", "semantic", "--limit", "1", "--offset", "1"]),
    ("build", []), ("inspect", []), ("stats", []),
])
def test_cli_relative_source_read_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    command: str, flags: list[str],
) -> None:
    directory = tmp_path / "blueprints"
    directory.mkdir()
    source(directory)
    path = directory / "build.json"
    path.write_text(json.dumps(data()), encoding="utf-8")
    original_reader = loader.read_terrain
    calls = []
    def read(path: Path):
        calls.append(path)
        return original_reader(path)
    monkeypatch.setattr(loader, "read_terrain", read)
    monkeypatch.chdir(tmp_path)
    assert main([command, str(path), *flags]) == 0
    if "--json" in flags:
        report = json.loads(capsys.readouterr().out)
        assert report["valid"] is True and report["exitCode"] == 0
    assert calls == [directory / "source.schem"]
    assert load_blueprint(path).terrain is not None


@pytest.mark.parametrize("terrain", [
    {}, {"source": "source.schem"},
    {"source": "source.schem", "region": {"from": [0, 0], "to": [1, 1, 1]}},
    {"source": "source.schem", "region": REGION, "mask": []},
])
def test_terrain_schema(terrain: dict) -> None:
    blueprint = data()
    blueprint["terrain"] = terrain
    assert validator.validate_schema(blueprint)
