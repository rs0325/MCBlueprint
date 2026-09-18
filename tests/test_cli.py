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
            main(["build", str(write(tmp_path, VALID)), "--format", "litematic"])
        assert exc_info.value.code == 2


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
