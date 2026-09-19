import json
from pathlib import Path
from typing import Any

import nbtlib
import pytest

from mcblueprint.cli import (
    EXIT_OK,
    EXIT_USAGE_ERROR,
    EXIT_VALIDATION_ERROR,
    main,
    resolve_output_path,
)

VALID: dict[str, Any] = {
    "formatVersion": 1,
    "minecraftVersion": "1.21.11",
    "name": "house",
    "palettes": {"p": [{"block": "stone_bricks"}, {"block": "mossy_stone_bricks"}]},
    "operations": [
        {"type": "fill", "from": [-5, 0, -5], "to": [5, 7, 5], "palette": "p"},
        {"type": "fill", "from": [-4, 1, -4], "to": [4, 6, 4], "block": "air"},
    ],
}


def write(tmp_path: Path, data: Any, name: str = "house.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestValidate:
    def test_valid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["validate", str(write(tmp_path, VALID))]) == EXIT_OK
        assert capsys.readouterr().out.strip() == "Blueprint is valid."

    def test_invalid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        bad = {**VALID, "operations": [{"type": "set", "position": [0, 0, 0], "block": "nope"}]}
        assert main(["validate", str(write(tmp_path, bad))]) == EXIT_VALIDATION_ERROR
        out = capsys.readouterr().out
        assert "ERROR operations[0].block (set)" in out
        assert "Unknown block id." in out
        assert out.strip().endswith("1 error found.")

    def test_max_dimension(self, tmp_path: Path) -> None:
        big = {
            **VALID,
            "operations": [{"type": "line", "from": [0, 0, 0], "to": [50, 0, 0], "block": "stone"}],
        }
        path = write(tmp_path, big)
        assert main(["validate", str(path)]) == EXIT_OK
        assert main(["validate", str(path), "--max-dimension", "20"]) == EXIT_VALIDATION_ERROR

    def test_missing_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["validate", str(tmp_path / "missing.json")]) == EXIT_USAGE_ERROR
        assert "not found" in capsys.readouterr().err

    def test_invalid_json(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{", encoding="utf-8")
        assert main(["validate", str(path)]) == EXIT_USAGE_ERROR
        assert "Invalid JSON" in capsys.readouterr().err


class TestBuild:
    def test_default_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["build", str(write(tmp_path, VALID))]) == EXIT_OK
        out = capsys.readouterr().out.splitlines()
        assert out[0] == "Wrote output/house.schem"
        assert out[1] == "Bounds: X -5..5  Y 0..7  Z -5..5  (11 x 8 x 11)"
        assert out[2] == "Blocks: 968"
        nbt = nbtlib.load(tmp_path / "output" / "house.schem")
        assert (nbt["Width"], nbt["Height"], nbt["Length"]) == (11, 8, 11)

    def test_output_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "dist"
        target.mkdir()
        assert main(["build", str(write(tmp_path, VALID)), "-o", str(target)]) == EXIT_OK
        assert (target / "house.schem").exists()

    def test_output_file(self, tmp_path: Path) -> None:
        target = tmp_path / "custom" / "name.schem"
        assert main(["build", str(write(tmp_path, VALID)), "-o", str(target)]) == EXIT_OK
        assert target.exists()

    def test_seed_override_changes_palette_result(self, tmp_path: Path) -> None:
        path = write(tmp_path, VALID)
        main(["build", str(path), "-o", str(tmp_path / "a.schem")])
        main(["build", str(path), "-o", str(tmp_path / "b.schem")])
        main(["build", str(path), "-o", str(tmp_path / "c.schem"), "--seed", "99"])
        a = list(nbtlib.load(tmp_path / "a.schem")["BlockData"])
        b = list(nbtlib.load(tmp_path / "b.schem")["BlockData"])
        c = list(nbtlib.load(tmp_path / "c.schem")["BlockData"])
        assert a == b
        assert a != c

    def test_validation_error_writes_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad = {**VALID, "operations": [{"type": "set", "position": [0, 0, 0]}]}
        assert main(["build", str(write(tmp_path, bad))]) == EXIT_VALIDATION_ERROR
        assert "Exactly one of 'block' or 'palette'" in capsys.readouterr().out
        assert not (tmp_path / "output").exists()

    def test_unknown_format(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["build", str(write(tmp_path, VALID)), "--format", "nbt"])
        assert exc_info.value.code == 2

    def test_litematic_format(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["build", str(write(tmp_path, VALID)), "--format", "litematic"]) == EXIT_OK
        assert capsys.readouterr().out.splitlines()[0] == "Wrote output/house.litematic"
        nbt = nbtlib.load(tmp_path / "output" / "house.litematic")
        assert dict(nbt["Regions"]["Main"]["Size"]) == {"x": 11, "y": 8, "z": 11}


class TestResolveOutputPath:
    def test_default(self) -> None:
        assert resolve_output_path(None, Path("blueprints/castle.json"), ".schem") == Path(
            "output/castle.schem"
        )

    def test_directory(self, tmp_path: Path) -> None:
        assert resolve_output_path(str(tmp_path), Path("x.json"), ".schem") == tmp_path / "x.schem"
        assert resolve_output_path("dir/", Path("x.json"), ".schem") == Path("dir/x.schem")
        assert resolve_output_path("dist", Path("x.json"), ".schem") == Path("dist/x.schem")

    def test_file(self) -> None:
        assert resolve_output_path("a/b.schem", Path("x.json"), ".schem") == Path("a/b.schem")


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == EXIT_USAGE_ERROR
    assert "usage:" in capsys.readouterr().out


class TestInspect:
    def test_text(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        data = {
            **VALID,
            "description": "desc",
            "size": [11, 10, 11],
            "operations": VALID["operations"]
            + [
                {
                    "type": "repeat",
                    "count": 2,
                    "offset": [0, 1, 0],
                    "operations": [{"type": "set", "position": [0, 8, 0], "block": "stone"}],
                }
            ],
        }
        assert main(["inspect", str(write(tmp_path, data))]) == EXIT_OK
        out = capsys.readouterr().out
        assert "Name: house" in out
        assert "Minecraft: 1.21.11" in out
        assert "X: -5 .. 5" in out and "Y: 0 .. 9" in out and "Z: -5 .. 5" in out
        assert "Size: 11 x 10 x 11" in out
        assert "Operations: 4 (top level: 3)" in out
        assert "Palettes: 1" in out
        assert "Declared size: [11, 10, 11]" in out
        assert "Description: desc" in out

    def test_json(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["inspect", str(write(tmp_path, VALID)), "--json"]) == EXIT_OK
        info = json.loads(capsys.readouterr().out)
        assert info["bounds"] == {"min": [-5, 0, -5], "max": [5, 7, 5]}
        assert info["size"] == [11, 8, 11]
        assert info["operations"] == 2
        assert info["declaredSize"] is None

    def test_does_not_generate_and_reports_errors(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad = {**VALID, "operations": [{"type": "set", "position": [0, 0, 0], "block": "nope"}]}
        assert main(["inspect", str(write(tmp_path, bad))]) == EXIT_VALIDATION_ERROR
        assert "Unknown block id." in capsys.readouterr().out


class TestStats:
    def test_text(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["stats", str(write(tmp_path, VALID))]) == EXIT_OK
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "Total blocks: 482 (air: 486)"
        assert lines[1] == "Bounds: X -5..5  Y 0..7  Z -5..5  (11 x 8 x 11)"
        assert lines[2] == ""
        counts = {line.split()[1]: int(line.split()[0]) for line in lines[3:]}
        assert set(counts) == {"minecraft:stone_bricks", "minecraft:mossy_stone_bricks"}
        assert sum(counts.values()) == 482
        assert [int(line.split()[0]) for line in lines[3:]] == sorted(
            (int(line.split()[0]) for line in lines[3:]), reverse=True
        )

    def test_json_and_seed(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = write(tmp_path, VALID)
        assert main(["stats", str(path), "--json"]) == EXIT_OK
        a = json.loads(capsys.readouterr().out)
        assert main(["stats", str(path), "--json", "--seed", "99"]) == EXIT_OK
        b = json.loads(capsys.readouterr().out)
        assert a["totalBlocks"] == b["totalBlocks"] == 482
        assert a["airBlocks"] == 486
        assert a["size"] == [11, 8, 11]
        assert a["blocks"] != b["blocks"]

    def test_validation_error(self, tmp_path: Path) -> None:
        bad = {**VALID, "operations": [{"type": "set", "position": [0, 0, 0]}]}
        assert main(["stats", str(write(tmp_path, bad))]) == EXIT_VALIDATION_ERROR


class TestSupportWarnings:
    LANTERN_ON_SLAB = [
        {"type": "fill", "from": [0, 0, 0], "to": [2, 0, 2], "block": "stone"},
        {"type": "set", "position": [1, 3, 1], "block": "oak_slab[type=top]"},
        {"type": "set", "position": [1, 2, 1], "block": "lantern[hanging=true]"},
    ]

    def test_validate_prints_warnings_but_succeeds(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = write(tmp_path, {**VALID, "operations": self.LANTERN_ON_SLAB})
        assert main(["validate", str(path)]) == EXIT_OK
        out = capsys.readouterr().out
        assert out.startswith(
            "Blueprint is valid.\n\nWARNING [1, 2, 1] minecraft:lantern[hanging=true]"
        )
        assert out.strip().endswith("1 warning found.")

    def test_validate_strict(self, tmp_path: Path) -> None:
        path = write(tmp_path, {**VALID, "operations": self.LANTERN_ON_SLAB})
        assert main(["validate", str(path), "--strict"]) == EXIT_VALIDATION_ERROR
        assert main(["validate", str(write(tmp_path, VALID)), "--strict"]) == EXIT_OK

    def test_build_writes_with_warnings_unless_strict(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = write(tmp_path, {**VALID, "operations": self.LANTERN_ON_SLAB})
        assert main(["build", str(path)]) == EXIT_OK
        out = capsys.readouterr().out
        assert "WARNING" in out and "Wrote output/house.schem" in out
        assert (tmp_path / "output" / "house.schem").exists()

        assert main(["build", str(path), "-o", str(tmp_path / "strict.schem"), "--strict"]) == (
            EXIT_VALIDATION_ERROR
        )
        assert "Not written because of warnings" in capsys.readouterr().out
        assert not (tmp_path / "strict.schem").exists()
