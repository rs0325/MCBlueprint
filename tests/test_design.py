import json
from pathlib import Path

import pytest

from mcblueprint import components
from mcblueprint.analysis import analyze, kind_of, palette_id
from mcblueprint.checking import check_preset
from mcblueprint.cli import EXIT_OK, EXIT_USAGE_ERROR, main
from mcblueprint.design_preset import PartInfo, palettes_json, render_preset
from mcblueprint.exporters import SchemExporter
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint, load_blueprint_dict, read_blueprint_json
from mcblueprint.model import BlockState, Vec3

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"
B = BlockState.parse


def example_volume(name: str):
    with components.component_search_paths([REPO_ROOT / "components"]):
        return generate(load_blueprint(EXAMPLES / f"{name}.json"))


class TestClassification:
    @pytest.mark.parametrize(
        ("name", "kind"),
        [
            ("glass_pane", "window"),
            ("glass", "window"),
            ("iron_bars", "window"),
            ("oak_door", "door"),
            ("spruce_trapdoor", "door"),
            ("lantern", "light"),
            ("wall_torch", "light"),
            ("oak_fence", "decoration"),
            ("poppy", "decoration"),
            ("stone_bricks", None),
            ("dark_oak_stairs", None),
            ("oak_log", None),
        ],
    )
    def test_kind_of(self, name: str, kind: str | None) -> None:
        assert kind_of(name) == kind

    def test_palette_id_keeps_only_log_axis(self) -> None:
        assert palette_id(B("oak_log[axis=x]")) == "minecraft:oak_log[axis=x]"
        assert (
            palette_id(B("dark_oak_stairs[facing=north,half=top]")) == "minecraft:dark_oak_stairs"
        )
        assert palette_id(B("stone_brick_slab[type=top]")) == "minecraft:stone_brick_slab"


class TestHouseAnalysis:
    @pytest.fixture
    def house(self):
        return analyze(example_volume("house"))

    def test_roles(self, house) -> None:
        assert house.top("wall") == "minecraft:white_terracotta"
        assert house.top("post") == "minecraft:oak_log"
        assert house.top("floor") == "minecraft:oak_planks"
        assert house.top("foundation") == "minecraft:stone_bricks"
        assert house.top("roof") == "minecraft:dark_oak_stairs"
        assert house.top("gable") == "minecraft:spruce_planks"
        assert house.top("ridge") == "minecraft:dark_oak_planks"
        assert house.top("window") == "minecraft:glass_pane"
        assert house.top("door") == "minecraft:oak_door"
        assert house.top("light") == "minecraft:campfire"
        # the roof's eaves and the gable's bottom row are not counted as wall
        assert all("stairs" not in block for block, _ in house.palette("wall"))
        assert all("spruce" not in block for block, _ in house.palette("wall"))

    def test_palette_weights(self, house) -> None:
        wall = dict(house.palette("wall"))
        assert set(wall) == {"minecraft:white_terracotta", "minecraft:light_gray_terracotta"}
        assert wall["minecraft:white_terracotta"] > wall["minecraft:light_gray_terracotta"]
        assert 95 <= sum(wall.values()) <= 100

    def test_dimensions(self, house) -> None:
        assert house.size == Vec3(13, 12, 11)
        assert house.footprint.min == Vec3(0, 1, 0) and house.footprint.max == Vec3(10, 5, 8)
        assert house.floor_levels == [0]
        assert house.wall_height == 5
        assert house.wall_thickness == 1

    def test_roof(self, house) -> None:
        roof = house.roof
        assert roof is not None
        assert roof.style == "gable" and roof.ridge == "x"
        assert roof.block == "minecraft:dark_oak_stairs"
        assert roof.gable_block == "minecraft:spruce_planks"
        assert roof.ridge_block == "minecraft:dark_oak_slab"
        assert roof.overhang == 1 and roof.rise == 5

    def test_windows_and_door(self, house) -> None:
        w = house.windows
        assert w is not None
        assert (w.block, w.width, w.height, w.sill) == ("minecraft:glass_pane", 1, 2, 2)
        assert w.count == 7 and w.spacing == 2
        assert house.doors == {"minecraft:oak_door": 1} and house.door_count == 1


class TestOtherExamples:
    def test_tower_storeys_and_beams(self) -> None:
        tower = analyze(example_volume("tower"))
        assert tower.floor_levels[:4] == [0, 5, 10, 15]
        assert tower.storey_heights[:3] == [5, 5, 5]
        assert tower.top("wall") == "minecraft:stone_bricks"
        assert tower.top("beam") == "minecraft:dark_oak_log[axis=z]"
        assert tower.top("foundation") == "minecraft:cobblestone"
        assert tower.roof is None  # the dome is a sphere, not stairs
        assert tower.windows is not None and tower.windows.count == 15
        assert tower.wall_thickness == 1

    def test_hip_roof(self) -> None:
        data = {
            "formatVersion": 1,
            "minecraftVersion": "1.21.11",
            "name": "hip",
            "operations": [
                {"type": "floor", "from": [0, 0, 0], "to": [8, 0, 8], "block": "stone"},
                {
                    "type": "wall",
                    "from": [0, 1, 0],
                    "to": [8, 1, 8],
                    "height": 4,
                    "block": "bricks",
                },
                {
                    "type": "roof",
                    "from": [0, 4, 0],
                    "to": [8, 4, 8],
                    "style": "hip",
                    "block": "brick_stairs",
                },
            ],
        }
        analysis = analyze(generate(load_blueprint_dict(data)))
        assert analysis.roof is not None and analysis.roof.style == "hip"
        assert analysis.roof.block == "minecraft:brick_stairs" and analysis.roof.overhang == 1
        assert analysis.top("wall") == "minecraft:bricks"


class TestPreset:
    def test_render_sections_and_palettes(self) -> None:
        house = analyze(example_volume("house"))
        text = render_preset("my_house", house, source="house.schem")
        for heading in (
            "# my_house",
            "## 概要",
            "## Palette",
            "## 構造ルール",
            "## 寸法の目安",
            "## 装飾",
            "## 禁止事項",
            "## 参考図",
        ):
            assert heading in text
        assert '`style: "gable"`' in text and "`overhang: 1`" in text
        assert "幅 1 × 高さ 2、床から 2" in text
        assert "`doorway` に `oak_door`" in text
        palettes = palettes_json(house)["palettes"]
        assert set(palettes) >= {"wall", "post", "floor", "roof", "gable", "foundation"}
        assert "window" not in palettes  # single blocks are rules, not palettes

    def test_parts_reference_and_no_views(self) -> None:
        house = analyze(example_volume("house"))
        part = PartInfo("gate", Vec3(5, 6, 1), "an arch", "components/gate.json")
        ref = PartInfo(
            "my_house_reference", Vec3(13, 12, 11), None, "components/my_house_reference.json"
        )
        text = render_preset("h", house, source="h.schem", parts=[part], reference=ref, views=False)
        assert "## 部品" in text and "| `gate` | 5 × 6 × 1 | an arch |" in text
        assert '"name": "gate"' in text and "my_house_reference" in text
        assert "## 参考図" not in text

    def test_generated_preset_passes_check(self, tmp_path: Path) -> None:
        house = analyze(example_volume("house"))
        path = tmp_path / "h.md"
        path.write_text(render_preset("h", house, source="h.json"), encoding="utf-8")
        result = check_preset(path, "1.21.11")
        assert result.ok, [e.format() for e in result.errors]


class TestCli:
    def test_design_from_blueprint_and_schematic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with components.component_search_paths([REPO_ROOT / "components"]):
            assert main(["design", str(EXAMPLES / "house.json"), "--name", "villa"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "Wrote designs/local/villa.md" in out and "Roles: wall" in out
        text = (tmp_path / "designs" / "local" / "villa.md").read_text(encoding="utf-8")
        assert text.startswith("# villa")
        # the same build as a schematic, with a part and a reference component
        blueprint = load_blueprint(EXAMPLES / "house.json")
        schem = tmp_path / "villa.schem"
        SchemExporter().export(generate(blueprint), blueprint, schem)
        part = tmp_path / "gate.schem"
        with components.component_search_paths([REPO_ROOT / "components"]):
            part_bp = load_blueprint_dict(read_blueprint_json(EXAMPLES / "gatehouse.json"))
            SchemExporter().export(generate(part_bp), part_bp, part)
        assert (
            main(
                [
                    "design",
                    str(schem),
                    "--reference",
                    "--part",
                    f"gate={part}",
                    "-o",
                    str(tmp_path / "out.md"),
                    "--no-views",
                ]
            )
            == EXIT_OK
        )
        out = capsys.readouterr().out
        assert "Wrote components/gate.json" in out
        assert "Wrote components/villa_reference.json" in out
        assert "out.md" in out
        text = (tmp_path / "out.md").read_text(encoding="utf-8")
        assert "| `gate` | 15 × 9 × 9 |" in text and "villa_reference" in text
        assert "## 参考図" not in text
        ref = json.loads(
            (tmp_path / "components" / "villa_reference.json").read_text(encoding="utf-8")
        )
        assert ref["name"] == "villa_reference" and "origin" not in ref
        assert main(["check", "--strict"]) == EXIT_OK

    def test_design_errors(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert (
            main(["design", str(EXAMPLES / "house.json"), "--name", "Bad Name"]) == EXIT_USAGE_ERROR
        )
        assert "--name" in capsys.readouterr().err
        assert (
            main(
                [
                    "design",
                    str(EXAMPLES / "house.json"),
                    "--name",
                    "x",
                    "--part",
                    "nope",
                    "-o",
                    str(tmp_path / "x.md"),
                ]
            )
            == EXIT_USAGE_ERROR
        )
        assert "NAME=FILE" in capsys.readouterr().err
        assert main(["design", str(tmp_path / "missing.schem")]) == EXIT_USAGE_ERROR
