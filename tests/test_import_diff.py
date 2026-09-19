import json
from pathlib import Path
from typing import Any

import nbtlib
import pytest
from nbtlib import ByteArray, Compound, File, Int, IntArray, Short

from mcblueprint.cli import EXIT_OK, EXIT_USAGE_ERROR, EXIT_VALIDATION_ERROR, main
from mcblueprint.diffing import diff_volumes, format_diff, normalize
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters import LitematicExporter, SchemExporter
from mcblueprint.generator import generate
from mcblueprint.importers import (
    greedy_boxes,
    read_schematic,
    to_blueprint,
    version_for_data_version,
)
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model import BlockState, Vec3
from mcblueprint.volume import BlockVolume

B = BlockState.parse
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def blueprint(*operations: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "t",
        "operations": list(operations),
        **extra,
    }


def volume_with(*cells: tuple[tuple[int, int, int], str]) -> BlockVolume:
    volume = BlockVolume()
    for (x, y, z), block in cells:
        volume.set(Vec3(x, y, z), B(block))
    return volume


class TestGreedyBoxes:
    def test_merges_into_boxes(self) -> None:
        volume = volume_with(
            *(((x, y, z), "stone") for x in range(3) for y in range(2) for z in range(2)),
            ((5, 0, 0), "oak_planks"),
        )
        boxes = greedy_boxes(volume)
        assert (Vec3(0, 0, 0), Vec3(2, 1, 1), B("stone")) in boxes
        assert (Vec3(5, 0, 0), Vec3(5, 0, 0), B("oak_planks")) in boxes
        assert len(boxes) == 2

    def test_covers_every_cell_exactly_once(self) -> None:
        volume = volume_with(
            *(((x, 0, z), "stone" if (x + z) % 3 else "dirt") for x in range(6) for z in range(5)),
            ((2, 1, 2), "stone"),
        )
        covered: list[Vec3] = []
        for a, b, state in greedy_boxes(volume):
            for x in range(a.x, b.x + 1):
                for y in range(a.y, b.y + 1):
                    for z in range(a.z, b.z + 1):
                        assert volume.get(Vec3(x, y, z)) == state
                        covered.append(Vec3(x, y, z))
        assert sorted(covered, key=lambda p: (p.y, p.z, p.x)) == sorted(
            volume.positions(), key=lambda p: (p.y, p.z, p.x)
        )


class TestReaders:
    @pytest.mark.parametrize("fmt", ["schem", "litematic"])
    def test_roundtrip_examples(self, tmp_path: Path, fmt: str) -> None:
        for name in ("house", "tower", "gatehouse"):
            data = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
            from mcblueprint import components

            with components.component_search_paths([EXAMPLES.parent / "components"]):
                bp = load_blueprint_dict(data)
            volume = generate(bp)
            exporter = SchemExporter() if fmt == "schem" else LitematicExporter()
            path = tmp_path / f"{name}.{fmt}"
            exporter.export(volume, bp, path)

            imported = read_schematic(path)
            assert imported.data_version == 4671
            regenerated = load_blueprint_dict(
                to_blueprint(imported, name=name, minecraft_version="1.21.11", description=None)
            )
            assert diff_volumes(
                normalize(volume, bp), normalize(generate(regenerated), regenerated)
            ).is_empty

    def test_schem_v3_layout(self, tmp_path: Path) -> None:
        root = Compound(
            {
                "Version": Int(3),
                "DataVersion": Int(4671),
                "Width": Short(2),
                "Height": Short(1),
                "Length": Short(1),
                "Offset": IntArray([0, 0, 0]),
                "Blocks": Compound(
                    {
                        "Palette": Compound({"minecraft:air": Int(0), "minecraft:stone": Int(1)}),
                        "Data": ByteArray([1, 0]),
                        "BlockEntities": nbtlib.List[Compound]([]),
                    }
                ),
            }
        )
        path = tmp_path / "v3.schem"
        File(Compound({"Schematic": root}), gzipped=True, root_name="").save(str(path))
        imported = read_schematic(path)
        assert imported.volume.get(Vec3(0, 0, 0)) == B("stone")
        assert imported.volume.get(Vec3(1, 0, 0)) is None
        assert len(imported.volume) == 1

    def test_errors(self, tmp_path: Path) -> None:
        with pytest.raises(BlueprintError, match="not found"):
            read_schematic(tmp_path / "missing.schem")
        bad = tmp_path / "x.txt"
        bad.write_text("nope", encoding="utf-8")
        with pytest.raises(BlueprintError):
            read_schematic(bad)

    def test_version_lookup(self) -> None:
        assert version_for_data_version(4671) == "1.21.11"
        assert version_for_data_version(1) is None
        assert version_for_data_version(None) is None

    def test_to_blueprint_compacts_defaults_and_keeps_offset(self) -> None:
        from mcblueprint.importers import ImportedSchematic

        volume = volume_with(
            ((0, 0, 0), "oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]"),
            ((1, 0, 0), "oak_stairs[facing=east,half=top,shape=straight,waterlogged=false]"),
        )
        data = to_blueprint(
            ImportedSchematic(volume, Vec3(10, 0, 0), 4671),
            name="n",
            minecraft_version="1.21.11",
            description="d",
        )
        ops = data["operations"]
        assert ops[0] == {
            "type": "set",
            "position": [10, 0, 0],
            "block": "minecraft:oak_stairs[facing=east]",
        }
        assert ops[1]["block"] == "minecraft:oak_stairs[facing=east,half=top]"
        assert data["origin"] == [0, 0, 0] and data["description"] == "d"


class TestDiff:
    def test_diff_categories(self) -> None:
        a = volume_with(((0, 0, 0), "stone"), ((1, 0, 0), "stone"), ((2, 0, 0), "oak_planks"))
        b = volume_with(((0, 0, 0), "stone"), ((2, 0, 0), "bricks"), ((3, 0, 0), "glass"))
        d = diff_volumes(a, b)
        assert d.added == {Vec3(3, 0, 0): "minecraft:glass"}
        assert d.removed == {Vec3(1, 0, 0): "minecraft:stone"}
        assert d.changed == {Vec3(2, 0, 0): ("minecraft:oak_planks", "minecraft:bricks")}
        assert d.state_deltas() == {
            "minecraft:bricks": 1,
            "minecraft:glass": 1,
            "minecraft:oak_planks": -1,
            "minecraft:stone": -1,
        }
        text = format_diff(d)
        assert text.startswith("Added: 1  Removed: 1  Changed: 1")
        assert "[2, 0, 0] minecraft:oak_planks -> minecraft:bricks" in text
        assert d.to_json()["samples"]["changed"][0]["before"] == "minecraft:oak_planks"

    def test_empty(self) -> None:
        d = diff_volumes(volume_with(((0, 0, 0), "stone")), volume_with(((0, 0, 0), "stone")))
        assert d.is_empty and format_diff(d) == "No differences."

    def test_normalize(self) -> None:
        bp = load_blueprint_dict(
            blueprint(
                {"type": "set", "position": [5, 5, 5], "block": "oak_stairs[facing=east]"},
                {"type": "set", "position": [6, 5, 5], "block": "air"},
                origin=[5, 5, 5],
            )
        )
        norm = normalize(generate(bp), bp)
        assert list(norm) == [
            (
                Vec3(0, 0, 0),
                B("oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]"),
            )
        ]


class TestCli:
    def test_import_and_diff(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        src = tmp_path / "src.json"
        src.write_text(
            json.dumps(
                blueprint(
                    {"type": "fill", "from": [0, 0, 0], "to": [3, 1, 3], "block": "stone"},
                    {"type": "set", "position": [1, 2, 1], "block": "oak_stairs[facing=east]"},
                    origin=[1, 0, 1],
                )
            ),
            encoding="utf-8",
        )
        assert main(["build", str(src), "-o", str(tmp_path / "src.schem")]) == EXIT_OK
        capsys.readouterr()
        out_json = tmp_path / "imported.json"
        assert main(["import", str(tmp_path / "src.schem"), "-o", str(out_json)]) == EXIT_OK
        out = capsys.readouterr().out
        assert "Blocks: 33  Operations: 2" in out
        assert "Minecraft: 1.21.11" in out
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["name"] == "src" and data["description"] == "Imported from src.schem"

        assert main(["diff", str(src), str(out_json)]) == EXIT_OK
        assert capsys.readouterr().out.strip() == "No differences."

        changed = tmp_path / "changed.json"
        data["operations"].append({"type": "set", "position": [0, 5, 0], "block": "gold_block"})
        changed.write_text(json.dumps(data), encoding="utf-8")
        assert main(["diff", str(src), str(changed), "--json"]) == EXIT_OK
        info = json.loads(capsys.readouterr().out)
        assert info["added"] == 1 and info["stateDeltas"] == {"minecraft:gold_block": 1}

    def test_import_default_output_and_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src.json"
        src.write_text(
            json.dumps(blueprint({"type": "set", "position": [0, 0, 0], "block": "stone"})),
            encoding="utf-8",
        )
        assert main(["build", str(src), "-o", str(tmp_path / "castle.schem")]) == EXIT_OK
        assert main(["import", str(tmp_path / "castle.schem"), "--name", "My Castle"]) == EXIT_OK
        data = json.loads((tmp_path / "blueprints" / "castle.json").read_text(encoding="utf-8"))
        assert data["name"] == "My Castle"

    def test_import_unknown_version_needs_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root = Compound(
            {
                "Version": Int(2),
                "DataVersion": Int(1),
                "Width": Short(1),
                "Height": Short(1),
                "Length": Short(1),
                "Palette": Compound({"minecraft:stone": Int(0)}),
                "BlockData": ByteArray([0]),
            }
        )
        path = tmp_path / "old.schem"
        File(root, gzipped=True, root_name="Schematic").save(str(path))
        assert main(["import", str(path), "-o", str(tmp_path / "o.json")]) == EXIT_USAGE_ERROR
        assert "--minecraft-version" in capsys.readouterr().err
        assert (
            main(
                [
                    "import",
                    str(path),
                    "-o",
                    str(tmp_path / "o.json"),
                    "--minecraft-version",
                    "1.21.11",
                ]
            )
            == EXIT_OK
        )

    def test_import_reports_unknown_blocks(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root = Compound(
            {
                "Version": Int(2),
                "DataVersion": Int(4671),
                "Width": Short(1),
                "Height": Short(1),
                "Length": Short(1),
                "Palette": Compound({"mymod:thing": Int(0)}),
                "BlockData": ByteArray([0]),
            }
        )
        path = tmp_path / "mod.schem"
        File(root, gzipped=True, root_name="Schematic").save(str(path))
        assert main(["import", str(path), "-o", str(tmp_path / "m.json")]) == EXIT_VALIDATION_ERROR
        out = capsys.readouterr().out
        assert "Wrote" in out and "Unknown block id." in out
        assert (tmp_path / "m.json").exists()

    def test_diff_reports_invalid_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        good = tmp_path / "g.json"
        good.write_text(
            json.dumps(blueprint({"type": "set", "position": [0, 0, 0], "block": "stone"})),
            encoding="utf-8",
        )
        bad = tmp_path / "b.json"
        bad.write_text(
            json.dumps(blueprint({"type": "set", "position": [0, 0, 0], "block": "nope"})),
            encoding="utf-8",
        )
        assert main(["diff", str(good), str(bad)]) == EXIT_VALIDATION_ERROR
        assert "Unknown block id." in capsys.readouterr().out
