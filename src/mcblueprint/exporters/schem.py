"""Sponge Schematic v2 (``.schem``) exporter — see docs/ARCHITECTURE.md section 9."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from nbtlib import ByteArray, Compound, File, Int, IntArray, Short

from mcblueprint import blockdata
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters.base import Exporter
from mcblueprint.model.block import BlockState
from mcblueprint.model.blueprint import Blueprint
from mcblueprint.model.vec import Vec3
from mcblueprint.volume import BlockVolume

AIR = BlockState.parse("minecraft:air")
MAX_SHORT = 32767


def encode_varint(value: int) -> Iterable[int]:
    """7 bits per byte, low bits first, high bit set while more bytes follow."""
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            yield byte | 0x80
        else:
            yield byte
            return


def to_signed_byte(byte: int) -> int:
    return byte - 256 if byte > 127 else byte


class SchemExporter(Exporter):
    format = "schem"
    extension = ".schem"

    def export(self, volume: BlockVolume, blueprint: Blueprint, out_path: Path) -> None:
        bounds = volume.bounds()
        if bounds is None:
            raise BlueprintError("Nothing to export: no blocks were generated")
        size = bounds.size
        if max(size.x, size.y, size.z) > MAX_SHORT:
            raise BlueprintError(f"Structure too large for .schem: {size.x} x {size.y} x {size.z}")

        blocks = blockdata.load_block_data(blueprint.minecraft_version)
        palette_index: dict[str, int] = {}
        palette_of: dict[BlockState, int] = {}

        def index_for(state: BlockState) -> int:
            index = palette_of.get(state)
            if index is None:
                key = blocks.complete(state).to_string()
                index = palette_index.setdefault(key, len(palette_index))
                palette_of[state] = index
            return index

        data = bytearray()
        for y in range(bounds.min.y, bounds.max.y + 1):
            for z in range(bounds.min.z, bounds.max.z + 1):
                for x in range(bounds.min.x, bounds.max.x + 1):
                    state = volume.get(Vec3(x, y, z))
                    data.extend(encode_varint(index_for(AIR if state is None else state)))

        offset = bounds.min - blueprint.origin
        root = Compound(
            {
                "Version": Int(2),
                "DataVersion": Int(blockdata.data_version(blueprint.minecraft_version)),
                "Width": Short(size.x),
                "Height": Short(size.y),
                "Length": Short(size.z),
                "Offset": IntArray([offset.x, offset.y, offset.z]),
                "Palette": Compound({key: Int(i) for key, i in palette_index.items()}),
                "PaletteMax": Int(len(palette_index)),
                "BlockData": ByteArray([to_signed_byte(b) for b in data]),
                "Metadata": Compound(
                    {
                        "WEOffsetX": Int(offset.x),
                        "WEOffsetY": Int(offset.y),
                        "WEOffsetZ": Int(offset.z),
                    }
                ),
            }
        )
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        File(root, gzipped=True, root_name="Schematic").save(str(out_path))
