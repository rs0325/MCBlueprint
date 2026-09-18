import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from mcblueprint.schema import load_schema

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_SCHEMA_PATH = REPO_ROOT / "schema" / "blueprint.schema.json"
PACKAGE_SCHEMA_PATH = REPO_ROOT / "src" / "mcblueprint" / "schema" / "blueprint.schema.json"


def blueprint(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "test",
        "operations": [{"type": "set", "position": [0, 0, 0], "block": "minecraft:stone"}],
    }
    data.update(overrides)
    return data


def errors(data: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(load_schema())
    return [e.message for e in validator.iter_errors(data)]


def test_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(load_schema())


def test_root_copy_matches_package_schema() -> None:
    root = json.loads(ROOT_SCHEMA_PATH.read_text(encoding="utf-8"))
    package = json.loads(PACKAGE_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert root == package


def test_minimal_blueprint_is_valid() -> None:
    assert errors(blueprint()) == []


def test_full_top_level_is_valid() -> None:
    data = blueprint(
        description="desc",
        author="me",
        seed=42,
        origin=[0, 0, 0],
        size=[16, 24, 16],
        palettes={
            "stone_wall": [
                {"block": "minecraft:stone_bricks", "weight": 70},
                {"block": "mossy_stone_bricks"},
            ]
        },
        metadata={"anything": {"goes": [1, 2, 3]}},
    )
    assert errors(data) == []


VALID_OPERATIONS = [
    {"type": "set", "position": [0, 0, 0], "block": "minecraft:stone"},
    {"type": "fill", "from": [0, 0, 0], "to": [4, 2, 4], "palette": "p"},
    {"type": "box", "from": [0, 0, 0], "to": [4, 2, 4], "mode": "solid", "block": "stone"},
    {
        "type": "wall",
        "from": [0, 0, 0],
        "to": [4, 0, 4],
        "height": 3,
        "thickness": 2,
        "block": "stone",
    },
    {"type": "floor", "from": [0, 0, 0], "to": [4, 0, 4], "block": "oak_planks"},
    {"type": "line", "from": [0, 0, 0], "to": [4, 2, 4], "block": "oak_fence", "comment": "c"},
    {
        "type": "circle",
        "center": [0, 0, 0],
        "radius": 3,
        "axis": "x",
        "mode": "hollow",
        "block": "a",
    },
    {"type": "cylinder", "center": [0, 0, 0], "radius": 3, "height": 5, "block": "a"},
    {"type": "sphere", "center": [0, 0, 0], "radius": 3, "mode": "solid", "block": "a"},
    {
        "type": "mirror",
        "axis": "x",
        "at": 0.5,
        "keepOriginal": False,
        "operations": [{"type": "set", "position": [1, 0, 0], "block": "a"}],
    },
    {
        "type": "repeat",
        "count": 3,
        "offset": [2, 0, 0],
        "operations": [
            {
                "type": "mirror",
                "axis": "z",
                "at": 0,
                "operations": [{"type": "set", "position": [1, 0, 1], "block": "a"}],
            }
        ],
    },
]


@pytest.mark.parametrize("operation", VALID_OPERATIONS, ids=lambda op: op["type"])
def test_valid_operation(operation: dict[str, Any]) -> None:
    assert errors(blueprint(operations=[operation])) == []


@pytest.mark.parametrize(
    "block",
    [
        "minecraft:stone",
        "stone",
        "minecraft:oak_stairs[facing=north,half=top]",
        "oak_slab[type=top]",
        "mymod:custom_block",
    ],
)
def test_valid_block_strings(block: str) -> None:
    op = {"type": "set", "position": [0, 0, 0], "block": block}
    assert errors(blueprint(operations=[op])) == []


@pytest.mark.parametrize(
    "block",
    [
        "Minecraft:Stone",
        "minecraft:stone[]",
        "minecraft:stone[facing]",
        "minecraft:stone[facing=north,]",
        "minecraft:stone[facing=north]extra",
        "minecraft stone",
        "",
    ],
)
def test_invalid_block_strings(block: str) -> None:
    op = {"type": "set", "position": [0, 0, 0], "block": block}
    assert errors(blueprint(operations=[op]))


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(
            {k: v for k, v in blueprint().items() if k != "formatVersion"},
            id="missing-formatVersion",
        ),
        pytest.param(blueprint(formatVersion=2), id="unsupported-formatVersion"),
        pytest.param(blueprint(minecraftVersion="1.21.x"), id="bad-minecraftVersion"),
        pytest.param(blueprint(name=""), id="empty-name"),
        pytest.param(blueprint(operations=[]), id="empty-operations"),
        pytest.param(blueprint(unknown=1), id="unknown-top-level-key"),
        pytest.param(blueprint(seed=1.5), id="non-integer-seed"),
        pytest.param(blueprint(origin=[0, 0]), id="origin-two-elements"),
        pytest.param(blueprint(size=[0, 1, 1]), id="size-zero"),
        pytest.param(blueprint(palettes={"Bad-Name": [{"block": "stone"}]}), id="bad-palette-name"),
        pytest.param(blueprint(palettes={"p": []}), id="empty-palette"),
        pytest.param(
            blueprint(palettes={"p": [{"block": "stone", "weight": 0}]}), id="zero-weight"
        ),
        pytest.param(
            blueprint(palettes={"p": [{"block": "stone", "extra": 1}]}), id="palette-extra-key"
        ),
        pytest.param(blueprint(metadata="text"), id="metadata-not-object"),
    ],
)
def test_invalid_top_level(data: dict[str, Any]) -> None:
    assert errors(data)


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param({"type": "unknown", "position": [0, 0, 0], "block": "a"}, id="unknown-type"),
        pytest.param({"position": [0, 0, 0], "block": "a"}, id="missing-type"),
        pytest.param({"type": "set", "block": "a"}, id="set-missing-position"),
        pytest.param(
            {"type": "set", "position": [0, 0, 0], "block": "a", "extra": 1}, id="extra-key"
        ),
        pytest.param({"type": "set", "position": [0, 0], "block": "a"}, id="position-two-elements"),
        pytest.param({"type": "set", "position": [0.5, 0, 0], "block": "a"}, id="position-float"),
        pytest.param(
            {"type": "set", "position": [0, 0, 0], "palette": "Bad"}, id="bad-palette-ref"
        ),
        pytest.param({"type": "fill", "from": [0, 0, 0], "block": "a"}, id="fill-missing-to"),
        pytest.param(
            {"type": "box", "from": [0, 0, 0], "to": [1, 1, 1], "mode": "thick", "block": "a"},
            id="bad-mode",
        ),
        pytest.param(
            {"type": "wall", "from": [0, 0, 0], "to": [1, 0, 1], "block": "a"},
            id="wall-missing-height",
        ),
        pytest.param(
            {"type": "wall", "from": [0, 0, 0], "to": [1, 0, 1], "height": 0, "block": "a"},
            id="wall-height-zero",
        ),
        pytest.param(
            {
                "type": "wall",
                "from": [0, 0, 0],
                "to": [1, 0, 1],
                "height": 1,
                "thickness": 0,
                "block": "a",
            },
            id="wall-thickness-zero",
        ),
        pytest.param(
            {"type": "circle", "center": [0, 0, 0], "radius": 0, "block": "a"},
            id="circle-radius-zero",
        ),
        pytest.param(
            {"type": "circle", "center": [0, 0, 0], "radius": 2, "axis": "w", "block": "a"},
            id="circle-bad-axis",
        ),
        pytest.param(
            {"type": "cylinder", "center": [0, 0, 0], "radius": 2, "block": "a"},
            id="cylinder-missing-height",
        ),
        pytest.param(
            {"type": "sphere", "center": [0, 0, 0], "radius": -1, "block": "a"},
            id="sphere-negative-radius",
        ),
        pytest.param(
            {"type": "sphere", "center": [0, 0, 0], "radius": 1, "axis": "y", "block": "a"},
            id="sphere-has-no-axis",
        ),
        pytest.param(
            {"type": "mirror", "axis": "x", "at": 0, "operations": []}, id="mirror-empty-operations"
        ),
        pytest.param(
            {
                "type": "mirror",
                "axis": "x",
                "at": 0.3,
                "operations": [{"type": "set", "position": [0, 0, 0], "block": "a"}],
            },
            id="mirror-at-not-half",
        ),
        pytest.param(
            {
                "type": "mirror",
                "axis": "x",
                "at": 0,
                "block": "a",
                "operations": [{"type": "set", "position": [0, 0, 0], "block": "a"}],
            },
            id="mirror-has-no-block",
        ),
        pytest.param(
            {
                "type": "repeat",
                "count": 0,
                "offset": [1, 0, 0],
                "operations": [{"type": "set", "position": [0, 0, 0], "block": "a"}],
            },
            id="repeat-count-zero",
        ),
        pytest.param(
            {
                "type": "repeat",
                "count": 513,
                "offset": [1, 0, 0],
                "operations": [{"type": "set", "position": [0, 0, 0], "block": "a"}],
            },
            id="repeat-count-too-large",
        ),
        pytest.param(
            {
                "type": "repeat",
                "count": 2,
                "offset": [1, 0, 0],
                "operations": [{"type": "set", "position": [0, 0, 0], "block": "a", "extra": 1}],
            },
            id="nested-extra-key",
        ),
    ],
)
def test_invalid_operation(operation: dict[str, Any]) -> None:
    assert errors(blueprint(operations=[operation]))
