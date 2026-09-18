import json
from pathlib import Path
from typing import Any

import pytest

from mcblueprint.errors import BlueprintError
from mcblueprint.loader import load_blueprint, load_blueprint_dict, read_blueprint_json
from mcblueprint.model import BlockState, Vec3


def minimal(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "test",
        "operations": [{"type": "set", "position": [0, 0, 0], "block": "stone"}],
    }
    data.update(overrides)
    return data


def test_defaults() -> None:
    bp = load_blueprint_dict(minimal())
    assert bp.format_version == 1
    assert bp.minecraft_version == "1.21.11"
    assert bp.name == "test"
    assert bp.description is None
    assert bp.author is None
    assert bp.seed == 0
    assert bp.origin == Vec3(0, 0, 0)
    assert bp.size is None
    assert bp.palettes == {}
    assert bp.metadata is None
    assert bp.operations == [{"type": "set", "position": [0, 0, 0], "block": "stone"}]


def test_full_top_level() -> None:
    bp = load_blueprint_dict(
        minimal(
            description="d",
            author="a",
            seed=42,
            origin=[1, 2, 3],
            size=[16, 24, 16],
            metadata={"k": "v"},
            palettes={
                "stone_wall": [
                    {"block": "stone_bricks", "weight": 70},
                    {"block": "minecraft:mossy_stone_bricks"},
                ]
            },
        )
    )
    assert bp.description == "d"
    assert bp.author == "a"
    assert bp.seed == 42
    assert bp.origin == Vec3(1, 2, 3)
    assert bp.size == Vec3(16, 24, 16)
    assert bp.metadata == {"k": "v"}
    palette = bp.palettes["stone_wall"]
    assert palette.name == "stone_wall"
    assert [e.block for e in palette.entries] == [
        BlockState.parse("minecraft:stone_bricks"),
        BlockState.parse("minecraft:mossy_stone_bricks"),
    ]
    assert [e.weight for e in palette.entries] == [70.0, 1.0]


def test_load_from_file(tmp_path: Path) -> None:
    path = tmp_path / "bp.json"
    path.write_text(json.dumps(minimal(name="from file")), encoding="utf-8")
    assert load_blueprint(path).name == "from file"
    assert read_blueprint_json(path)["name"] == "from file"


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(BlueprintError, match="not found"):
        load_blueprint(tmp_path / "missing.json")


def test_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(BlueprintError, match="Invalid JSON"):
        load_blueprint(path)


def test_root_not_object(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(BlueprintError, match="JSON object"):
        load_blueprint(path)


@pytest.mark.parametrize(
    ("data", "match"),
    [
        (minimal(formatVersion=2), "formatVersion"),
        (minimal(operations=[]), "operations"),
        (minimal(name=""), "name"),
        (minimal(origin=[0, 0]), "origin"),
        (minimal(size="big"), "size"),
        (minimal(palettes={"p": []}), "palettes.p"),
        (minimal(palettes={"p": [{"block": "Bad Block"}]}), r"palettes\.p\[0\]\.block"),
        (minimal(palettes={"p": [{"block": "stone", "weight": 0}]}), r"palettes\.p\[0\]\.weight"),
    ],
)
def test_shape_errors(data: dict[str, Any], match: str) -> None:
    with pytest.raises(BlueprintError, match=match):
        load_blueprint_dict(data)
