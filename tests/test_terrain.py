from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path

import pytest
from nbtlib import ByteArray, Compound, File, Float, Int, IntArray, List, LongArray, Short, String

from mcblueprint.errors import BlueprintError
from mcblueprint.exporters.litematic import bits_for, pack_bit_array
from mcblueprint.importers import read_schematic, read_terrain
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.terrain import TerrainSnapshot

B = BlockState.parse
AIR = B("air")


def schem(
    size: tuple[int, int, int] = (3, 1, 1),
    indices: tuple[int, ...] = (0, 1, 0),
    *,
    version: int = 2,
) -> Compound:
    blocks = Compound({
        "Palette": Compound({"minecraft:air": Int(0), "minecraft:stone": Int(1)}),
        "Data": ByteArray(indices),
    })
    root = Compound({
        "Version": Int(version), "DataVersion": Int(4671),
        "Width": Short(size[0]), "Height": Short(size[1]), "Length": Short(size[2]),
        "Offset": IntArray([-4, 7, -2]),
    })
    if version == 3:
        root["Blocks"] = blocks
        return Compound({"Schematic": root})
    root["Palette"] = blocks["Palette"]
    root["BlockData"] = blocks["Data"]
    return root


def vec(values: tuple[int, int, int]) -> Compound:
    return Compound({axis: Int(value) for axis, value in zip("xyz", values, strict=True)})


def litematic(
    size: tuple[int, int, int] = (3, 1, 1),
    indices: tuple[int, ...] = (0, 1, 0),
) -> Compound:
    region = Compound({
        "Size": vec(size), "Position": vec((-4, 7, -2)),
        "BlockStatePalette": List[Compound]([
            Compound({"Name": String("minecraft:air")}),
            Compound({"Name": String("minecraft:stone")}),
        ]),
        "BlockStates": LongArray(pack_bit_array(list(indices), bits_for(2))),
    })
    return Compound({"MinecraftDataVersion": Int(4671), "Regions": Compound({"Main": region})})


def save(tmp_path: Path, root: Compound, fmt: str, *, gzipped: bool = True) -> Path:
    path = tmp_path / f"terrain.{fmt}"
    File(root, gzipped=gzipped, root_name="").save(str(path))
    return path


@pytest.mark.parametrize("version", [1, 2, 3])
@pytest.mark.parametrize("gzipped", [True, False])
def test_schem_declared_air_margin_and_metadata(
    tmp_path: Path, version: int, gzipped: bool
) -> None:
    path = save(tmp_path, schem(version=version), "schem", gzipped=gzipped)
    original = path.read_bytes()
    snapshot = read_terrain(path)
    assert snapshot.bounds == AABB(Vec3(0, 0, 0), Vec3(2, 0, 0))
    assert snapshot.source_bounds == AABB(Vec3(-4, 7, -2), Vec3(-2, 7, -2))
    assert snapshot.offset == Vec3(-4, 7, -2)
    assert snapshot.data_version == 4671
    assert snapshot.minecraft_version == "1.21.11"
    assert snapshot.input_sha256 == sha256(original).hexdigest()
    assert snapshot.get(Vec3(0, 0, 0)) == AIR
    assert snapshot.get(Vec3(1, 0, 0)) == B("stone")
    assert snapshot.get(Vec3(2, 0, 0)) == AIR
    assert snapshot.get(Vec3(3, 0, 0)) is None
    assert snapshot.get(Vec3(-1, 0, 0)) is None
    assert len(snapshot.blocks) == 1
    assert path.read_bytes() == original
    assert read_schematic(path).volume.bounds() == AABB(Vec3(1, 0, 0), Vec3(1, 0, 0))


@pytest.mark.parametrize("fmt", ["schem", "litematic"])
@pytest.mark.parametrize("size", [(1, 1, 1), (3, 2, 4)])
def test_all_air_and_single_cell(tmp_path: Path, fmt: str, size: tuple[int, int, int]) -> None:
    indices = (0,) * (size[0] * size[1] * size[2])
    root = schem(size, indices) if fmt == "schem" else litematic(size, indices)
    snapshot = read_terrain(save(tmp_path, root, fmt))
    assert snapshot.bounds.size == Vec3(*size)
    assert not snapshot.blocks
    assert snapshot.get(snapshot.bounds.max) == AIR
    assert snapshot.get(snapshot.bounds.max + Vec3(0, 1, 0)) is None


@pytest.mark.parametrize("size", [(2, 3, 2), (-2, 3, 2), (2, -3, 2), (-2, -3, -2)])
def test_litematic_negative_size_and_all_axes(tmp_path: Path, size: tuple[int, int, int]) -> None:
    indices = (0, 1) * 6
    snapshot = read_terrain(save(tmp_path, litematic(size, indices), "litematic"))
    expected_offset = Vec3(*(
        position + (axis + 1 if axis < 0 else 0)
        for position, axis in zip((-4, 7, -2), size, strict=True)
    ))
    assert snapshot.offset == expected_offset
    for y in range(3):
        for z in range(2):
            for x in range(2):
                pos = Vec3(x, y, z)
                assert snapshot.get(pos) == (AIR if x == 0 else B("stone"))
                assert snapshot.to_local(snapshot.to_source(pos)) == pos
    outside = Vec3(-8, 90, -1)
    assert snapshot.to_source(snapshot.to_local(outside)) == outside


@pytest.mark.parametrize("fmt", ["schem", "litematic"])
def test_original_states_and_immutability(tmp_path: Path, fmt: str) -> None:
    root = schem() if fmt == "schem" else litematic()
    states = ["minecraft:cave_air", "minecraft:void_air", "minecraft:oak_stairs[facing=east]"]
    if fmt == "schem":
        root["Palette"] = Compound({state: Int(i) for i, state in enumerate(states)})
        root["BlockData"] = ByteArray([0, 1, 2])
    else:
        region = root["Regions"]["Main"]
        region["BlockStatePalette"] = List[Compound]([
            Compound({"Name": String("minecraft:cave_air")}),
            Compound({"Name": String("minecraft:void_air")}),
            Compound({"Name": String("minecraft:oak_stairs"),
                      "Properties": Compound({"facing": String("east")})}),
        ])
        region["BlockStates"] = LongArray(pack_bit_array([0, 1, 2], 2))
    path = save(tmp_path, root, fmt)
    snapshot = read_terrain(path)
    assert [snapshot.get(Vec3(x, 0, 0)) for x in range(3)] == [B(state) for state in states]
    with pytest.raises(FrozenInstanceError):
        snapshot.offset = Vec3(0, 0, 0)
    with pytest.raises(TypeError):
        snapshot.blocks[Vec3(0, 0, 0)] = B("stone")
    path.write_bytes(b"changed after reading")
    assert snapshot.get(Vec3(2, 0, 0)) == B(states[2])


def test_constructor_copies_source_mapping() -> None:
    cells = {Vec3(0, 0, 0): B("stone")}
    snapshot = TerrainSnapshot(AABB(Vec3(0, 0, 0), Vec3(0, 0, 0)), Vec3(0, 0, 0),
                               None, None, "digest", cells)
    cells.clear()
    assert snapshot.get(Vec3(0, 0, 0)) == B("stone")


@pytest.mark.parametrize("fmt", ["schem", "litematic"])
@pytest.mark.parametrize("data_version", [None, 999999])
def test_unknown_version_is_not_guessed(tmp_path: Path, fmt: str, data_version: int | None) -> None:
    root = schem() if fmt == "schem" else litematic()
    key = "DataVersion" if fmt == "schem" else "MinecraftDataVersion"
    if data_version is None:
        del root[key]
    else:
        root[key] = Int(data_version)
    snapshot = read_terrain(save(tmp_path, root, fmt))
    assert snapshot.data_version == data_version
    assert snapshot.minecraft_version is None


@pytest.mark.parametrize("key", ["BlockEntities", "TileEntities", "Entities",
                                "PendingBlockTicks", "PendingFluidTicks",
                                "BlockTicks", "FluidTicks"])
@pytest.mark.parametrize("target", ["schem-root", "schem-v3-root", "schem-v3-blocks",
                                   "litematic-root", "litematic-region"])
def test_reject_nonempty_attached_data(tmp_path: Path, key: str, target: str) -> None:
    fmt = "litematic" if target.startswith("litematic") else "schem"
    root = litematic() if fmt == "litematic" else schem(version=3 if "v3" in target else 2)
    if target == "schem-v3-root":
        container = root["Schematic"]
    elif target == "schem-v3-blocks":
        container = root["Schematic"]["Blocks"]
    elif target == "litematic-region":
        container = root["Regions"]["Main"]
    else:
        container = root
    container[key] = List[Compound]([Compound({"id": String("example")})])
    path = save(tmp_path, root, fmt)
    original = path.read_bytes()
    with pytest.raises(BlueprintError, match=key):
        read_terrain(path)
    assert path.read_bytes() == original
    assert len(read_schematic(path).volume) == 1
    container[key] = List[Compound]([])
    assert read_terrain(save(tmp_path, root, fmt)).get(Vec3(1, 0, 0)) == B("stone")


@pytest.mark.parametrize("size", [(0, 1, 1), (-1, 1, 1), (1, 0, 1)])
def test_reject_schem_invalid_dimensions(tmp_path: Path, size: tuple[int, int, int]) -> None:
    with pytest.raises(BlueprintError):
        read_terrain(save(tmp_path, schem(size), "schem"))


@pytest.mark.parametrize("data", [[0, 1], [0, 1, 0, 1], [0, 4, 0], [0, 1, -128],
                                  [-1, -1, -1, -1, 127]])
def test_reject_schem_bad_data(tmp_path: Path, data: list[int]) -> None:
    root = schem()
    root["BlockData"] = ByteArray(data)
    with pytest.raises(BlueprintError):
        read_terrain(save(tmp_path, root, "schem"))


@pytest.mark.parametrize("palette", [{}, {"minecraft:air": 0, "minecraft:stone": 0},
                                    {"minecraft:stone": -1}, {"bad state": 0}])
def test_reject_schem_bad_palette(tmp_path: Path, palette: dict[str, int]) -> None:
    root = schem()
    root["Palette"] = Compound({key: Int(value) for key, value in palette.items()})
    with pytest.raises(BlueprintError):
        read_terrain(save(tmp_path, root, "schem"))


@pytest.mark.parametrize("failure", ["no-regions", "multi-regions", "zero-size", "empty-palette",
                                    "bad-state", "bad-index", "short-data", "long-data"])
def test_reject_litematic_bad_data(tmp_path: Path, failure: str) -> None:
    root = litematic()
    region = root["Regions"]["Main"]
    if failure == "no-regions":
        root["Regions"] = Compound({})
    elif failure == "multi-regions":
        root["Regions"]["Other"] = region
    elif failure == "zero-size":
        region["Size"]["x"] = Int(0)
    elif failure == "empty-palette":
        region["BlockStatePalette"] = List[Compound]([])
    elif failure == "bad-state":
        region["BlockStatePalette"][0]["Name"] = String("bad state")
    elif failure == "bad-index":
        region["BlockStates"] = LongArray(pack_bit_array([0, 3, 0], 2))
    elif failure == "short-data":
        region["BlockStates"] = LongArray([])
    else:
        region["BlockStates"] = LongArray([0, 0])
    with pytest.raises(BlueprintError):
        read_terrain(save(tmp_path, root, "litematic"))


@pytest.mark.parametrize("payload", [b"", b"not nbt", b"\x1f\x8bcorrupt gzip"])
def test_corrupted_input(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "bad.schem"
    path.write_bytes(payload)
    with pytest.raises(BlueprintError):
        read_terrain(path)
    assert path.read_bytes() == payload


def test_missing_fields_file_and_unsupported_format(tmp_path: Path) -> None:
    for path in (tmp_path / "missing.schem", tmp_path / "unsupported.schematic"):
        with pytest.raises(BlueprintError):
            read_terrain(path)
    with pytest.raises(BlueprintError):
        read_terrain(save(tmp_path, Compound({}), "schem"))
    root = schem()
    root["Version"] = Int(99)
    with pytest.raises(BlueprintError):
        read_terrain(save(tmp_path, root, "schem"))


@pytest.mark.parametrize("key", ["Width", "Height", "Length", "Offset", "DataVersion",
                                "Version", "Palette"])
@pytest.mark.parametrize("tag", [Float, String])
def test_schem_rejects_noninteger_fields(tmp_path: Path, key: str, tag: type) -> None:
    root = schem()
    if key == "Offset":
        root[key] = List[tag]([tag(-4.9 if tag is Float else "-4"), tag(7), tag(-2)])
    elif key == "Palette":
        root[key]["minecraft:stone"] = tag(1.9 if tag is Float else "1")
    else:
        value = {"Width": 3, "Height": 1, "Length": 1, "DataVersion": 4671, "Version": 2}[key]
        root[key] = tag(value + 0.9 if tag is Float else str(value))
    path = save(tmp_path, root, "schem")
    with pytest.raises(BlueprintError, match=key):
        read_terrain(path)
    # 建築用 import が従来どおり変換する経路は維持する。
    assert len(read_schematic(path).volume) == 1


@pytest.mark.parametrize("field,axis", [
    ("Size", "x"), ("Size", "y"), ("Size", "z"),
    ("Position", "x"), ("Position", "y"), ("Position", "z"),
    ("MinecraftDataVersion", None),
])
@pytest.mark.parametrize("tag", [Float, String])
def test_litematic_rejects_noninteger_fields(
    tmp_path: Path, field: str, axis: str | None, tag: type
) -> None:
    root = litematic()
    if field == "MinecraftDataVersion":
        root[field] = tag(4671.9 if tag is Float else "4671")
    else:
        container = root["Regions"]["Main"][field]
        value = int(container[axis])
        container[axis] = (
            tag(value - 0.9 if value < 0 else value + 0.9) if tag is Float else tag(value)
        )
    path = save(tmp_path, root, "litematic")
    with pytest.raises(BlueprintError, match=field):
        read_terrain(path)
    assert len(read_schematic(path).volume) == 1


@pytest.mark.parametrize("version", [1, 2, 3])
def test_schem_rejects_nonbyte_block_data(tmp_path: Path, version: int) -> None:
    root = schem((1, 1, 1), (0,), version=version)
    if version == 3:
        root["Schematic"]["Blocks"]["Data"] = IntArray([256])
    else:
        root["BlockData"] = IntArray([256])
    path = save(tmp_path, root, "schem")
    with pytest.raises(BlueprintError, match="ByteArray"):
        read_terrain(path)
    assert len(read_schematic(path).volume) == 0
