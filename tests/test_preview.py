import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from mcblueprint.cli import EXIT_OK, EXIT_USAGE_ERROR, main
from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Vec3
from mcblueprint.preview import (
    BACKGROUND,
    ORIGIN,
    VIEWS,
    Options,
    block_color,
    color_keyword,
    layer_name,
    render,
    render_layer,
    shade,
    uncoloured_blocks,
    write_previews,
)
from mcblueprint.volume import BlockVolume

B = BlockState.parse


def volume_with(*cells: tuple[tuple[int, int, int], str]) -> BlockVolume:
    volume = BlockVolume()
    for (x, y, z), block in cells:
        volume.set(Vec3(x, y, z), B(block))
    return volume


class TestColors:
    @pytest.mark.parametrize(
        ("block", "expected"),
        [
            ("air", None),
            ("stone", (125, 125, 125)),
            ("mossy_stone_bricks", (100, 120, 90)),
            ("oak_planks", (180, 145, 85)),
            ("dark_oak_stairs[facing=north]", (70, 45, 25)),
            ("white_concrete", (235, 235, 235)),
            ("light_gray_concrete", (150, 150, 145)),
            ("some_unknown_block", (150, 150, 150)),
        ],
    )
    def test_block_color(self, block: str, expected: Any) -> None:
        assert block_color(B(block)) == expected

    def test_dyed_terracotta_and_glass_are_tinted(self) -> None:
        white = block_color(B("white_terracotta"))
        assert white is not None and white != (235, 235, 235)
        assert white[0] > white[2]  # warm tint
        glass = block_color(B("red_stained_glass"))
        assert glass is not None and glass[0] > glass[1]

    def test_shade(self) -> None:
        assert shade((100, 200, 250), 0.5) == (50, 100, 125)
        assert shade((100, 200, 250), 2.0) == (200, 255, 255)


class TestRender:
    def test_top_view_size_and_highest_block(self) -> None:
        volume = volume_with(((0, 0, 0), "stone"), ((2, 3, 1), "gold_block"))
        image = render(volume, "top", scale=4)
        assert image.size == (3 * 4, 2 * 4)
        assert image.getpixel((2 * 4 + 1, 1 * 4 + 1)) != BACKGROUND
        assert image.getpixel((1 * 4 + 1, 0 * 4 + 1)) == BACKGROUND  # empty column

    def test_elevations_show_nearest_block(self) -> None:
        volume = volume_with(((0, 0, 0), "gold_block"), ((0, 0, 5), "stone"))
        north = render(volume, "north", scale=4)
        south = render(volume, "south", scale=4)
        assert north.size == (4, 4) and south.size == (4, 4)
        assert north.getpixel((1, 2)) == shade((250, 220, 70), 0.9)  # row 1 is the top highlight
        assert south.getpixel((1, 2)) == shade((125, 125, 125), 0.9)
        east = render(volume, "east", scale=4)
        assert east.size == (6 * 4, 4)

    def test_isometric_size_and_hidden_cubes(self) -> None:
        volume = volume_with(
            *(((x, y, z), "stone") for x in range(3) for y in range(3) for z in range(3))
        )
        image = render(volume, "isometric", scale=8)
        assert image.size == ((3 + 3) * 8, (3 + 3) * 4 + 3 * 8 + 8)
        # something was drawn
        assert any(
            image.getpixel((x, y)) != BACKGROUND
            for x in range(0, image.width, 4)
            for y in range(0, image.height, 4)
        )

    def test_unknown_view_and_empty_volume(self) -> None:
        with pytest.raises(BlueprintError, match="Unknown view"):
            render(volume_with(((0, 0, 0), "stone")), "bottom")
        with pytest.raises(BlueprintError, match="no blocks"):
            render(BlockVolume(), "top")

    def test_write_previews(self, tmp_path: Path) -> None:
        volume = volume_with(((0, 0, 0), "stone"))
        paths = write_previews(volume, tmp_path / "out", "x", VIEWS, scale=4)
        assert [p.name for p in paths] == [f"x-{v}.png" for v in VIEWS]
        assert all(Image.open(p).size[0] > 0 for p in paths)


class TestCli:
    DATA = {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "p",
        "operations": [{"type": "fill", "from": [0, 0, 0], "to": [3, 2, 3], "block": "stone"}],
    }

    def test_default_views(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = tmp_path / "p.json"
        path.write_text(json.dumps(self.DATA), encoding="utf-8")
        assert main(["preview", str(path), "-o", str(tmp_path / "pv")]) == EXIT_OK
        out = capsys.readouterr().out.splitlines()
        assert [Path(line.split(" ", 1)[1]).name for line in out] == [
            "p-top.png",
            "p-north.png",
            "p-east.png",
            "p-isometric.png",
        ]
        assert Image.open(tmp_path / "pv" / "p-top.png").size == (32, 32)

    def test_views_and_scale(self, tmp_path: Path) -> None:
        path = tmp_path / "p.json"
        path.write_text(json.dumps(self.DATA), encoding="utf-8")
        assert (
            main(["preview", str(path), "-o", str(tmp_path), "--views", "south", "--scale", "2"])
            == EXIT_OK
        )
        assert Image.open(tmp_path / "p-south.png").size == (8, 6)
        assert (
            main(["preview", str(path), "-o", str(tmp_path), "--views", "bottom"])
            == EXIT_USAGE_ERROR
        )
        assert main(["preview", str(path), "-o", str(tmp_path), "--scale", "0"]) == EXIT_USAGE_ERROR

    def test_missing_pillow_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "PIL":
                raise ImportError("no PIL")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(BlueprintError, match="Pillow"):
            render(volume_with(((0, 0, 0), "stone")), "top")


class TestLayersAndShading:
    def test_layer_shows_level_and_ghosts_the_one_below(self) -> None:
        volume = volume_with(((0, 0, 0), "gold_block"), ((2, 0, 1), "stone"), ((2, 1, 1), "stone"))
        image = render_layer(volume, 1, scale=4)
        assert image.size == (3 * 4, 2 * 4)
        assert image.getpixel((2 * 4 + 1, 1 * 4 + 1)) == (125, 125, 125)  # stone at y=1
        ghost = image.getpixel((1, 1))  # gold block one level below, faded
        assert ghost != BACKGROUND and ghost != (250, 220, 70)
        assert ghost[0] > ghost[2]  # still yellowish
        assert image.getpixel((1 * 4 + 1, 1)) == BACKGROUND

    def test_layer_outside_the_structure(self) -> None:
        volume = volume_with(((0, 0, 0), "stone"))
        with pytest.raises(BlueprintError, match="outside"):
            render_layer(volume, 5)
        with pytest.raises(BlueprintError, match="no blocks"):
            render_layer(BlockVolume(), 0)

    def test_layer_name_is_zero_padded(self) -> None:
        from mcblueprint.model import AABB

        bounds = AABB.of(Vec3(0, 0, 0), Vec3(0, 12, 0))
        assert layer_name(3, bounds) == "y03" and layer_name(12, bounds) == "y12"
        assert layer_name(-2, AABB.of(Vec3(0, -5, 0), Vec3(0, 3, 0))) == "y-2"

    def test_elevation_highlights_exposed_top_and_side(self) -> None:
        volume = volume_with(((0, 0, 0), "stone"), ((0, 1, 0), "stone"), ((1, 0, 0), "stone"))
        image = render(volume, "south", scale=8)
        # column 0 (x=0): top block's top edge is lighter than its body
        body = image.getpixel((3, 4))
        assert image.getpixel((3, 1)) == shade((125, 125, 125), 1.25)
        assert body == shade((125, 125, 125), 0.9)
        # the right edge of x=1 (nothing beyond) is darker, the right edge of x=0 at y=0 is not
        assert image.getpixel((15, 12)) == shade((125, 125, 125), 0.55)
        assert image.getpixel((7, 12)) == body

    def test_top_view_marks_steps(self) -> None:
        volume = volume_with(((0, 1, 0), "stone"), ((1, 0, 0), "stone"))
        image = render(volume, "top", scale=8)
        # x=0 is higher than x=1: its right edge is dark; x=1's right edge is dark (nothing)
        assert image.getpixel((7, 3)) == shade((125, 125, 125), 0.55)
        assert image.getpixel((15, 3)) == shade((125, 125, 125), 0.55)

    def test_grid_adds_margin_labels_and_origin(self) -> None:
        volume = volume_with(*(((x, 0, z), "stone") for x in range(6) for z in range(6)))
        plain = render(volume, "top", scale=8)
        gridded = render(volume, "top", options=Options(scale=8, grid=5, origin=Vec3(2, 0, 3)))
        assert gridded.size == (plain.size[0] + 14, plain.size[1] + 14)
        # a major grid line at x=5 runs through the margin
        assert gridded.getpixel((14 + 5 * 8, 2)) == (160, 160, 160)
        # origin cell outlined in red
        assert gridded.getpixel((14 + 2 * 8, 14 + 3 * 8)) == ORIGIN
        # label text (antialiased dark pixels) was drawn somewhere in the margin
        assert any(
            gridded.getpixel((x, y))[0] < 140 and gridded.getpixel((x, y)) != (160, 160, 160)
            for x in range(14, 60)
            for y in range(0, 12)
        )
        iso = render(volume, "isometric", options=Options(scale=8, grid=5, origin=Vec3(2, 0, 3)))
        assert any(
            iso.getpixel((x, y)) == ORIGIN for x in range(iso.width) for y in range(iso.height)
        )

    def test_origin_outside_the_image_is_ignored(self) -> None:
        volume = volume_with(((0, 0, 0), "stone"))
        image = render(volume, "top", options=Options(scale=8, origin=Vec3(9, 0, 9)))
        assert image.size == (8, 8)

    def test_isometric_outlines(self) -> None:
        volume = volume_with(((0, 0, 0), "stone"))
        image = render(volume, "isometric", scale=8)
        assert any(
            image.getpixel((x, y)) == shade((125, 125, 125), 0.45)
            for x in range(image.width)
            for y in range(image.height)
        )

    def test_uncoloured_blocks(self) -> None:
        volume = volume_with(
            ((0, 0, 0), "stone"), ((1, 0, 0), "minecraft:sniffer_egg"), ((2, 0, 0), "air")
        )
        assert uncoloured_blocks(volume) == ["minecraft:sniffer_egg"]
        assert color_keyword(B("white_wool")) == "white"
        assert color_keyword(B("mossy_stone_bricks")) == "mossy_stone_brick"
        assert color_keyword(B("sniffer_egg")) is None

    def test_write_layers(self, tmp_path: Path) -> None:
        volume = volume_with(((0, 0, 0), "stone"), ((0, 3, 0), "stone"))
        paths = write_previews(volume, tmp_path, "x", views=[], layers=[0, 3])
        assert [p.name for p in paths] == ["x-y0.png", "x-y3.png"]


class TestCliLayers:
    DATA = {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "p",
        "origin": [1, 0, 1],
        "operations": [
            {"type": "fill", "from": [0, 0, 0], "to": [3, 2, 3], "block": "stone"},
            {"type": "set", "position": [1, 3, 1], "block": "sniffer_egg"},
        ],
    }

    def write(self, tmp_path: Path) -> Path:
        path = tmp_path / "p.json"
        path.write_text(json.dumps(self.DATA), encoding="utf-8")
        return path

    def test_layers_only(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = self.write(tmp_path)
        assert main(["preview", str(path), "-o", str(tmp_path), "--layers", "all"]) == EXIT_OK
        out = capsys.readouterr().out
        names = [
            Path(line.split(" ", 1)[1]).name
            for line in out.splitlines()
            if line.startswith("Wrote")
        ]
        assert names == ["p-y0.png", "p-y1.png", "p-y2.png", "p-y3.png"]
        assert "WARNING: no preview colour for minecraft:sniffer_egg" in out

    def test_layer_range_and_single_with_views(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = self.write(tmp_path)
        assert (
            main(
                [
                    "preview",
                    str(path),
                    "-o",
                    str(tmp_path),
                    "--layers",
                    "1..2",
                    "--layer",
                    "0",
                    "--views",
                    "top",
                    "--grid",
                    "2",
                ]
            )
            == EXIT_OK
        )
        names = [
            Path(line.split(" ", 1)[1]).name
            for line in capsys.readouterr().out.splitlines()
            if line.startswith("Wrote")
        ]
        assert names == ["p-top.png", "p-y0.png", "p-y1.png", "p-y2.png"]
        assert Image.open(tmp_path / "p-top.png").size == (4 * 8 + 14, 4 * 8 + 14)
        assert main(["preview", str(path), "-o", str(tmp_path), "--layers", "..1"]) == EXIT_OK
        assert (
            main(["preview", str(path), "-o", str(tmp_path), "--layers", "9"]) == EXIT_USAGE_ERROR
        )
        assert (
            main(["preview", str(path), "-o", str(tmp_path), "--layers", "x"]) == EXIT_USAGE_ERROR
        )
        assert main(["preview", str(path), "-o", str(tmp_path), "--grid", "0"]) == EXIT_USAGE_ERROR
