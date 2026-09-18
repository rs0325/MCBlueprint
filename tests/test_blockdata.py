import json
from pathlib import Path

import pytest

from mcblueprint import blockdata
from mcblueprint.errors import BlueprintError
from mcblueprint.model import BlockState

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_supported_versions_includes_1_21_11() -> None:
    assert "1.21.11" in blockdata.supported_versions()
    assert blockdata.is_supported("1.21.11")
    assert not blockdata.is_supported("0.0.0")
    assert blockdata.data_version("1.21.11") == 4671


def test_unsupported_version_raises() -> None:
    with pytest.raises(BlueprintError, match="Unsupported Minecraft version"):
        blockdata.load_block_data("0.0.0")
    with pytest.raises(BlueprintError, match="Unsupported Minecraft version"):
        blockdata.data_version("0.0.0")


def test_bundled_data_contents() -> None:
    data = blockdata.load_block_data("1.21.11")
    assert len(data) > 1000
    assert "minecraft:stone_bricks" in data
    assert "minecraft:air" in data
    stairs = data.get("minecraft:oak_stairs")
    assert stairs is not None
    assert stairs.properties["facing"] == ("north", "south", "west", "east")
    assert stairs.default == {
        "facing": "north",
        "half": "bottom",
        "shape": "straight",
        "waterlogged": "false",
    }


def test_load_is_cached() -> None:
    assert blockdata.load_block_data("1.21.11") is blockdata.load_block_data("1.21.11")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("stone_bricks", None),
        ("oak_stairs[facing=south,half=top]", None),
        ("stone_brick", "Unknown block id."),
        ("oak_stairs[facing=up]", "Invalid value 'up' for property 'facing'"),
        ("oak_stairs[color=red]", "Unknown property 'color' for minecraft:oak_stairs"),
        ("stone[facing=north]", "Unknown property 'facing' for minecraft:stone (valid: none)"),
    ],
)
def test_check_state(text: str, expected: str | None) -> None:
    data = blockdata.load_block_data("1.21.11")
    message = data.check_state(BlockState.parse(text))
    if expected is None:
        assert message is None
    else:
        assert message is not None and message.startswith(expected)


def test_complete_fills_defaults() -> None:
    data = blockdata.load_block_data("1.21.11")
    state = data.complete(BlockState.parse("oak_stairs[facing=south]"))
    assert state.to_string() == (
        "minecraft:oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]"
    )
    assert data.complete(BlockState.parse("stone")).to_string() == "minecraft:stone"
    with pytest.raises(BlueprintError):
        data.complete(BlockState.parse("not_a_block"))


def test_every_default_is_an_allowed_value() -> None:
    raw = json.loads(
        (REPO_ROOT / "src" / "mcblueprint" / "data" / "blocks" / "1.21.11.json").read_text(
            encoding="utf-8"
        )
    )
    for block_id, entry in raw.items():
        assert set(entry["default"]) == set(entry["properties"]), block_id
        for name, value in entry["default"].items():
            assert value in entry["properties"][name], (block_id, name)
