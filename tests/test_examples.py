from pathlib import Path

import nbtlib
import pytest

from mcblueprint.cli import EXIT_OK, main
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint, read_blueprint_json
from mcblueprint.validator import validate

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
EXAMPLES = sorted(EXAMPLES_DIR.glob("*.json"))


def test_examples_exist() -> None:
    assert {p.name for p in EXAMPLES} >= {"house.json", "tower.json"}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_is_valid(path: Path) -> None:
    assert validate(read_blueprint_json(path)) == []


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_generates_within_declared_size(path: Path) -> None:
    blueprint = load_blueprint(path)
    volume = generate(blueprint)
    bounds = volume.bounds()
    assert bounds is not None and len(volume) > 0
    assert blueprint.size is not None
    size = bounds.size
    assert (size.x, size.y, size.z) <= (blueprint.size.x, blueprint.size.y, blueprint.size.z)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_builds(path: Path, tmp_path: Path) -> None:
    out = tmp_path / (path.stem + ".schem")
    assert main(["build", str(path), "-o", str(out)]) == EXIT_OK
    nbt = nbtlib.load(out)
    assert nbt["Version"] == 2
    assert nbt["PaletteMax"] == len(nbt["Palette"])
