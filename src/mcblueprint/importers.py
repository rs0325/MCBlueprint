"""Read ``.schem`` (Sponge v2 / v3) and ``.litematic`` files into a BlockVolume, and
turn a BlockVolume back into Blueprint JSON (docs/ARCHITECTURE.md section 14)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import nbtlib

from mcblueprint import blockdata
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters.litematic import bits_for, unpack_bit_array
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import Vec3
from mcblueprint.volume import BlockVolume

AIR_IDS = frozenset({"minecraft:air", "minecraft:cave_air", "minecraft:void_air"})


@dataclass
class ImportedSchematic:
    volume: BlockVolume
    offset: Vec3  # position of the volume's origin relative to the paste point
    data_version: int | None
    name: str | None = None


# --- readers ----------------------------------------------------------------


def read_schematic(path: str | Path) -> ImportedSchematic:
    path = Path(path)
    try:
        nbt = nbtlib.load(str(path))
    except FileNotFoundError:
        raise BlueprintError(f"Schematic file not found: {path}") from None
    except Exception as exc:  # nbtlib raises assorted errors on bad input
        raise BlueprintError(f"Cannot read {path}: {exc}") from exc
    suffix = path.suffix.lower()
    if suffix == ".litematic":
        return _read_litematic(nbt)
    if suffix in (".schem", ".schematic"):
        return _read_schem(nbt)
    raise BlueprintError(f"Unsupported schematic extension {suffix!r} (use .schem or .litematic)")


def decode_varints(data: list[int]) -> list[int]:
    values, value, shift = [], 0, 0
    for byte in data:
        byte &= 0xFF
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
        else:
            values.append(value)
            value, shift = 0, 0
    return values


def _read_schem(nbt: Any) -> ImportedSchematic:
    root = nbt["Schematic"] if "Schematic" in nbt and "Version" not in nbt else nbt
    version = int(root.get("Version", 2))
    if version == 3:
        blocks = root["Blocks"]
        palette_tag, data_tag = blocks["Palette"], blocks["Data"]
    elif version in (1, 2):
        palette_tag, data_tag = root["Palette"], root["BlockData"]
    else:
        raise BlueprintError(f"Unsupported Sponge schematic version {version}")
    width, height, length = int(root["Width"]), int(root["Height"]), int(root["Length"])
    offset = Vec3.from_seq([int(v) for v in root["Offset"]]) if "Offset" in root else Vec3(0, 0, 0)
    palette = {int(index): BlockState.parse(str(key)) for key, index in palette_tag.items()}
    indices = decode_varints(list(data_tag))
    expected = width * height * length
    if len(indices) < expected:
        raise BlueprintError(f"Schematic block data is truncated ({len(indices)} < {expected})")
    volume = _fill_volume(indices, palette, width, height, length)
    data_version = int(root["DataVersion"]) if "DataVersion" in root else None
    return ImportedSchematic(volume, offset, data_version)


def _read_litematic(nbt: Any) -> ImportedSchematic:
    regions = nbt["Regions"]
    if len(regions) != 1:
        raise BlueprintError(
            f"Only single-region .litematic files are supported (found {len(regions)})"
        )
    name, region = next(iter(regions.items()))
    size = Vec3(int(region["Size"]["x"]), int(region["Size"]["y"]), int(region["Size"]["z"]))
    position = Vec3(
        int(region["Position"]["x"]), int(region["Position"]["y"]), int(region["Position"]["z"])
    )
    # negative sizes mean the region extends towards negative coordinates
    origin = Vec3(
        position.x + (size.x + 1 if size.x < 0 else 0),
        position.y + (size.y + 1 if size.y < 0 else 0),
        position.z + (size.z + 1 if size.z < 0 else 0),
    )
    width, height, length = abs(size.x), abs(size.y), abs(size.z)
    palette = {}
    for index, entry in enumerate(region["BlockStatePalette"]):
        props = entry.get("Properties") or {}
        palette[index] = BlockState(
            str(entry["Name"]), tuple(sorted((str(k), str(v)) for k, v in props.items()))
        )
    bits = bits_for(len(palette))
    indices = unpack_bit_array(list(region["BlockStates"]), bits, width * height * length)
    volume = _fill_volume(indices, palette, width, height, length)
    data_version = int(nbt["MinecraftDataVersion"]) if "MinecraftDataVersion" in nbt else None
    meta_name = (
        str(nbt["Metadata"]["Name"]) if "Metadata" in nbt and "Name" in nbt["Metadata"] else None
    )
    return ImportedSchematic(volume, origin, data_version, meta_name or str(name))


def _fill_volume(
    indices: list[int], palette: dict[int, BlockState], width: int, height: int, length: int
) -> BlockVolume:
    volume = BlockVolume()
    i = 0
    for y in range(height):
        for z in range(length):
            for x in range(width):
                state = palette.get(indices[i])
                i += 1
                if state is None:
                    raise BlueprintError(f"Block index {indices[i - 1]} is not in the palette")
                if state.id in AIR_IDS:
                    continue
                volume.set(Vec3(x, y, z), state)
    return volume


# --- volume -> blueprint ------------------------------------------------------


def greedy_boxes(volume: BlockVolume) -> list[tuple[Vec3, Vec3, BlockState]]:
    """Cover every set cell with axis-aligned boxes of one block state (greedy merge)."""
    cells = {pos: state for pos, state in volume}
    done: set[Vec3] = set()
    boxes = []
    for start in sorted(cells, key=lambda p: (p.y, p.z, p.x)):
        if start in done:
            continue
        state = cells[start]
        end = start
        while _same(cells, done, state, end + Vec3(1, 0, 0)):
            end = end + Vec3(1, 0, 0)
        while all(
            _same(cells, done, state, Vec3(x, start.y, end.z + 1))
            for x in range(start.x, end.x + 1)
        ):
            end = end + Vec3(0, 0, 1)
        while all(
            _same(cells, done, state, Vec3(x, end.y + 1, z))
            for x in range(start.x, end.x + 1)
            for z in range(start.z, end.z + 1)
        ):
            end = end + Vec3(0, 1, 0)
        for x in range(start.x, end.x + 1):
            for y in range(start.y, end.y + 1):
                for z in range(start.z, end.z + 1):
                    done.add(Vec3(x, y, z))
        boxes.append((start, end, state))
    return boxes


def _same(cells: dict[Vec3, BlockState], done: set[Vec3], state: BlockState, pos: Vec3) -> bool:
    return pos not in done and cells.get(pos) == state


def to_blueprint(
    imported: ImportedSchematic, *, name: str, minecraft_version: str, description: str | None
) -> dict[str, Any]:
    """Blueprint JSON that regenerates the imported volume at the same paste offset."""
    blocks = (
        blockdata.load_block_data(minecraft_version)
        if blockdata.is_supported(minecraft_version)
        else None
    )
    operations = []
    for start, end, state in greedy_boxes(imported.volume):
        text = _compact(state, blocks)
        a, b = start + imported.offset, end + imported.offset
        if a == b:
            operations.append({"type": "set", "position": a.to_list(), "block": text})
        else:
            operations.append(
                {"type": "fill", "from": a.to_list(), "to": b.to_list(), "block": text}
            )
    if not operations:
        raise BlueprintError("The schematic contains no blocks (only air)")
    data: dict[str, Any] = {
        "formatVersion": 1,
        "minecraftVersion": minecraft_version,
        "name": name,
    }
    if description:
        data["description"] = description
    data["origin"] = [0, 0, 0]
    data["operations"] = operations
    return data


def _compact(state: BlockState, blocks: blockdata.BlockData | None) -> str:
    """Drop properties equal to the block's default so the JSON stays short."""
    if blocks is None:
        return state.to_string()
    info = blocks.get(state.id)
    if info is None:
        return state.to_string()
    props = tuple((k, v) for k, v in state.properties if info.default.get(k) != v)
    return BlockState(state.id, props).to_string()


def version_for_data_version(data_version: int | None) -> str | None:
    if data_version is None:
        return None
    for version in blockdata.supported_versions():
        if blockdata.data_version(version) == data_version:
            return version
    return None
