import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from mcblueprint.cli import EXIT_OK, EXIT_USAGE_ERROR, main
from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState, Vec3
from mcblueprint.preview import BACKGROUND, VIEWS, block_color, render, shade, write_previews
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
        assert north.getpixel((1, 1)) == shade((250, 220, 70), 0.9)
        assert south.getpixel((1, 1)) == shade((125, 125, 125), 0.9)
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
