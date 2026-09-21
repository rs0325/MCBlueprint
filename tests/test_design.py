import json
from pathlib import Path

import pytest

from mcblueprint import blockdata, components
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
            ("spruce_trapdoor", "decoration"),
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


class TestOpeningParts:
    FRAME_WINDOW = [
        # a 1x2 pane with a stripped-log frame and a slab sill, on each of the four walls
        {"type": "floor", "from": [0, 0, 0], "to": [10, 0, 10], "block": "stone_bricks"},
        {
            "type": "wall",
            "from": [0, 1, 0],
            "to": [10, 1, 10],
            "height": 5,
            "block": "white_terracotta",
        },
        {"type": "window", "position": [5, 2, 0], "axis": "x", "height": 2},
        {"type": "fill", "from": [4, 2, 0], "to": [4, 3, 0], "block": "stripped_oak_log"},
        {"type": "fill", "from": [6, 2, 0], "to": [6, 3, 0], "block": "stripped_oak_log"},
        {"type": "set", "position": [5, 4, 0], "block": "oak_slab[type=bottom]"},
        {"type": "set", "position": [5, 1, -1], "block": "oak_slab[type=top]"},
        {"type": "window", "position": [5, 2, 10], "axis": "x", "height": 2},
        {"type": "fill", "from": [4, 2, 10], "to": [4, 3, 10], "block": "stripped_oak_log"},
        {"type": "fill", "from": [6, 2, 10], "to": [6, 3, 10], "block": "stripped_oak_log"},
        {"type": "set", "position": [5, 4, 10], "block": "oak_slab[type=bottom]"},
        {"type": "set", "position": [5, 1, 11], "block": "oak_slab[type=top]"},
        {"type": "window", "position": [10, 2, 5], "axis": "z", "height": 2},
        {"type": "fill", "from": [10, 2, 4], "to": [10, 3, 4], "block": "stripped_oak_log"},
        {"type": "fill", "from": [10, 2, 6], "to": [10, 3, 6], "block": "stripped_oak_log"},
        {"type": "set", "position": [10, 4, 5], "block": "oak_slab[type=bottom]"},
        {"type": "set", "position": [11, 1, 5], "block": "oak_slab[type=top]"},
        {"type": "window", "position": [0, 2, 5], "axis": "z", "height": 2},
        {"type": "fill", "from": [0, 2, 4], "to": [0, 3, 4], "block": "stripped_oak_log"},
        {"type": "fill", "from": [0, 2, 6], "to": [0, 3, 6], "block": "stripped_oak_log"},
        {"type": "set", "position": [0, 4, 5], "block": "oak_slab[type=bottom]"},
        {"type": "set", "position": [-1, 1, 5], "block": "oak_slab[type=top]"},
        {
            "type": "doorway",
            "position": [8, 1, 0],
            "facing": "south",
            "width": 2,
            "door": "oak_door",
            "arch": {"style": "flat", "block": "stone_bricks", "trim": "stone_brick_stairs"},
        },
    ]

    def blueprint(self, *operations):
        return {
            "formatVersion": 1,
            "minecraftVersion": "1.21.11",
            "name": "parts",
            "operations": list(operations),
        }

    def test_framed_windows_become_one_part(self) -> None:
        analysis = analyze(generate(load_blueprint_dict(self.blueprint(*self.FRAME_WINDOW))))
        windows = [p for p in analysis.parts if p.kind == "window"]
        assert len(windows) == 1 and windows[0].count == 4
        part = windows[0]
        assert part.size == Vec3(3, 4, 2)  # frame 3 wide, sill + 2 panes + lintel, sill sticks out
        blocks = {st.id for st in part.cells.values()}
        assert blocks == {
            "minecraft:glass_pane",
            "minecraft:stripped_oak_log",
            "minecraft:oak_slab",
        }
        # normalised: the sill (outside) is on the -z side, panes at z=1
        assert part.opening.min.z == 1 and part.opening.min.x == 1
        assert all(p.z == 0 for p, st in part.cells.items() if st.get("type") == "top")
        doors = [p for p in analysis.parts if p.kind == "door"]
        assert len(doors) == 1 and doors[0].count == 1
        assert any(st.id.endswith("stairs") for st in doors[0].cells.values())

    def test_plain_windows_give_no_parts(self) -> None:
        analysis = analyze(example_volume("house"))
        assert analysis.parts == []

    def test_parts_rebuild_the_original(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        data = self.blueprint(*self.FRAME_WINDOW)
        source = tmp_path / "parts.json"
        source.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["design", str(source), "--name", "villa", "--no-views"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "Wrote components/villa_window.json" in out
        assert "Wrote components/villa_door.json" in out
        text = (tmp_path / "designs" / "local" / "villa.md").read_text(encoding="utf-8")
        assert "`villa_window`（4 箇所）" in text and "rotation: 90" in text
        # place the window part on the four walls with the documented rotations
        original = generate(load_blueprint_dict(data))
        rebuilt = self.blueprint(
            *self.FRAME_WINDOW[:2],
            {"type": "component", "name": "villa_window", "position": [4, 1, -1]},
            {"type": "component", "name": "villa_window", "position": [11, 1, 4], "rotation": 90},
            {"type": "component", "name": "villa_window", "position": [6, 1, 11], "rotation": 180},
            {"type": "component", "name": "villa_window", "position": [-1, 1, 6], "rotation": 270},
        )

        blocks = blockdata.load_block_data("1.21.11")
        with components.component_search_paths([tmp_path / "components"]):
            volume = generate(load_blueprint_dict(rebuilt))
        for pos, state in original:
            if state.id in (
                "minecraft:glass_pane",
                "minecraft:stripped_oak_log",
                "minecraft:oak_slab",
            ):
                placed = volume.get(pos)
                assert placed is not None and blocks.complete(placed) == blocks.complete(state), pos
        assert main(["check", "--strict"]) == EXIT_OK

    def test_no_parts_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source = tmp_path / "parts.json"
        source.write_text(json.dumps(self.blueprint(*self.FRAME_WINDOW)), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["design", str(source), "--name", "v", "--no-views", "--no-parts"]) == EXIT_OK
        assert "components/" not in capsys.readouterr().out


class TestWallDecor:
    TIMBER = [
        {"type": "floor", "from": [0, 0, 0], "to": [12, 0, 8], "block": "stone_bricks"},
        {
            "type": "wall",
            "from": [0, 1, 0],
            "to": [12, 1, 8],
            "height": 8,
            "block": "white_terracotta",
        },
        {"type": "fill", "from": [0, 4, 0], "to": [12, 4, 0], "block": "dark_oak_planks"},
        {"type": "fill", "from": [0, 4, 8], "to": [12, 4, 8], "block": "dark_oak_planks"},
        {"type": "fill", "from": [0, 4, 0], "to": [0, 4, 8], "block": "dark_oak_planks"},
        {"type": "fill", "from": [12, 4, 0], "to": [12, 4, 8], "block": "dark_oak_planks"},
        {
            "type": "repeat",
            "count": 4,
            "offset": [4, 0, 0],
            "operations": [
                {
                    "type": "wall",
                    "from": [0, 1, 0],
                    "to": [0, 1, 0],
                    "height": 8,
                    "block": "dark_oak_log",
                },
                {
                    "type": "wall",
                    "from": [0, 1, 8],
                    "to": [0, 1, 8],
                    "height": 8,
                    "block": "dark_oak_log",
                },
            ],
        },
        {
            "type": "fill",
            "from": [0, 5, -1],
            "to": [12, 5, -1],
            "block": "dark_oak_trapdoor[facing=north,half=top,open=true]",
        },
        {
            "type": "fill",
            "from": [0, 5, 9],
            "to": [12, 5, 9],
            "block": "dark_oak_trapdoor[facing=south,half=top,open=true]",
        },
        {"type": "set", "position": [6, 3, -1], "block": "oak_fence"},
        {"type": "set", "position": [6, 4, -1], "block": "lantern"},
        {"type": "line", "from": [1, 6, -1], "to": [11, 6, -1], "block": "dark_oak_log[axis=x]"},
    ]

    def test_bands_trims_posts_and_beams(self) -> None:
        data = {
            "formatVersion": 1,
            "minecraftVersion": "1.21.11",
            "name": "timber",
            "operations": self.TIMBER,
        }
        analysis = analyze(generate(load_blueprint_dict(data)))
        walls = analysis.walls
        assert walls is not None
        assert [(b.height, b.block) for b in walls.bands] == [(4, "minecraft:dark_oak_planks")]
        assert [(t.height, t.block) for t in walls.trims] == [(5, "minecraft:dark_oak_trapdoor")]
        assert walls.trims[0].coverage > 0.5
        assert walls.items == {"minecraft:oak_fence": 1}  # the lantern is a light, the beam a beam
        assert walls.post_spacing == 4
        assert walls.beam_heights == [6]
        assert analysis.top("post") == "minecraft:dark_oak_log"
        text = render_preset("timber", analysis, source="t.json", views=False)
        assert "床から 4 段目は `dark_oak_planks` の帯" in text
        assert "床から 5 段目の外側に `dark_oak_trapdoor` を 1 周" in text
        assert "柱は 4 ブロックおき" in text and "床から 6 段目に水平の梁" in text
        assert "`oak_fence` × 1（壁の外側に張り出す飾り）" in text

    def test_plain_walls_have_no_decor_line(self) -> None:
        text = render_preset("h", analyze(example_volume("house")), source="h", views=False)
        assert "壁の装飾" not in text
