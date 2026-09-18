from typing import Any

import pytest

from mcblueprint.errors import ValidationError
from mcblueprint.validator import format_errors, validate, validate_schema


def bp(*operations: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "formatVersion": 1,
        "minecraftVersion": "1.21.11",
        "name": "t",
        "operations": list(operations) or [SET],
        **extra,
    }


SET = {"type": "set", "position": [0, 0, 0], "block": "stone"}


def paths(errors: list[ValidationError]) -> list[str]:
    return [e.path for e in errors]


class TestValid:
    def test_minimal(self) -> None:
        assert validate(bp()) == []

    def test_full(self) -> None:
        wall = {"type": "wall", "from": [1, 0, 1], "to": [4, 0, 4], "height": 3, "block": "stone"}
        data = bp(
            {"type": "cylinder", "center": [0, 0, 0], "radius": 5, "height": 10, "palette": "p"},
            {"type": "set", "position": [0, 1, -5], "block": "oak_door[facing=north,half=lower]"},
            {"type": "mirror", "axis": "x", "at": 0.5, "operations": [wall]},
            size=[12, 10, 12],
            palettes={
                "p": [{"block": "stone_bricks", "weight": 3}, {"block": "mossy_stone_bricks"}]
            },
        )
        assert validate(data) == []


class TestSchemaErrors:
    def test_radius(self) -> None:
        op = {"type": "cylinder", "center": [0, 0, 0], "radius": -5, "height": 3, "block": "stone"}
        errors = validate(bp(op))
        assert len(errors) == 1
        err = errors[0]
        assert err.path == "operations[0].radius"
        assert err.op_type == "cylinder"
        assert err.message == "'radius' must be >= 1."
        assert err.value == -5

    def test_missing_and_unknown_properties(self) -> None:
        errors = validate(bp({"type": "set", "block": "stone", "extra": 1}))
        assert paths(errors) == ["operations[0]", "operations[0]"]
        assert {e.message for e in errors} == {
            "Missing required property: position.",
            "Unknown property: extra.",
        }
        assert all(e.op_type == "set" for e in errors)

    def test_unknown_type(self) -> None:
        errors = validate(bp({"type": "nope"}))
        assert len(errors) == 1
        assert errors[0].path == "operations[0].type"
        assert errors[0].message.startswith("'type' must be one of: 'set', 'fill'")

    def test_top_level(self) -> None:
        errors = validate(bp(foo=1))
        assert len(errors) == 1
        assert errors[0].path == ""
        assert errors[0].message == "Unknown property: foo."
        assert errors[0].format().startswith("ERROR (top level)")

    def test_format_version(self) -> None:
        errors = validate({**bp(), "formatVersion": 2})
        assert paths(errors) == ["formatVersion"]
        assert errors[0].message == "'formatVersion' must be 1."

    def test_block_pattern(self) -> None:
        errors = validate(bp({"type": "set", "position": [0, 0, 0], "block": "Stone"}))
        assert paths(errors) == ["operations[0].block"]
        assert errors[0].message == "'block' does not match the required format."

    def test_nested_path_and_type(self) -> None:
        inner = {"type": "sphere", "center": [0, 0, 0], "radius": 0, "block": "stone"}
        errors = validate(
            bp({"type": "repeat", "count": 2, "offset": [1, 0, 0], "operations": [inner]})
        )
        assert paths(errors) == ["operations[0].operations[0].radius"]
        assert errors[0].op_type == "sphere"

    def test_schema_errors_stop_semantic_checks(self) -> None:
        # radius error (schema) and unknown block (semantic) -> only the schema error is reported
        op = {"type": "sphere", "center": [0, 0, 0], "radius": 0, "block": "not_a_block"}
        assert paths(validate(bp(op))) == ["operations[0].radius"]

    def test_validate_schema_non_object(self) -> None:
        errors = validate_schema([])
        assert len(errors) == 1
        assert errors[0].message == "value must be of type object."


class TestSemanticErrors:
    def test_unsupported_version(self) -> None:
        errors = validate({**bp(), "minecraftVersion": "1.0.0"})
        assert paths(errors) == ["minecraftVersion"]
        assert "1.21.11" in errors[0].message
        assert errors[0].value == "1.0.0"

    def test_unknown_block_in_operation_and_palette(self) -> None:
        data = bp(
            {"type": "set", "position": [0, 0, 0], "block": "stone_brick"},
            palettes={"p": [{"block": "stone"}, {"block": "mossy_stone_brick"}]},
        )
        errors = validate(data)
        assert paths(errors) == ["palettes.p[1].block", "operations[0].block"]
        assert all(e.message == "Unknown block id." for e in errors)
        assert errors[1].op_type == "set"
        assert errors[1].value == "stone_brick"

    def test_invalid_property(self) -> None:
        errors = validate(
            bp({"type": "set", "position": [0, 0, 0], "block": "oak_stairs[facing=up]"})
        )
        assert paths(errors) == ["operations[0].block"]
        assert errors[0].message.startswith("Invalid value 'up' for property 'facing'")

    def test_duplicate_property(self) -> None:
        errors = validate(
            bp(
                {
                    "type": "set",
                    "position": [0, 0, 0],
                    "block": "oak_stairs[facing=north,facing=south]",
                }
            )
        )
        assert paths(errors) == ["operations[0].block"]
        assert "Duplicate property" in errors[0].message

    @pytest.mark.parametrize(
        "op",
        [
            {"type": "fill", "from": [0, 0, 0], "to": [1, 1, 1]},
            {"type": "fill", "from": [0, 0, 0], "to": [1, 1, 1], "block": "stone", "palette": "p"},
        ],
    )
    def test_block_palette_exclusive(self, op: dict[str, Any]) -> None:
        errors = validate(bp(op, palettes={"p": [{"block": "stone"}]}))
        assert paths(errors) == ["operations[0]"]
        assert errors[0].message == "Exactly one of 'block' or 'palette' must be given."
        assert errors[0].op_type == "fill"

    def test_unknown_palette(self) -> None:
        errors = validate(bp({"type": "set", "position": [0, 0, 0], "palette": "missing"}))
        assert paths(errors) == ["operations[0].palette"]
        assert errors[0].message == "Unknown palette name."
        assert errors[0].value == "missing"

    @pytest.mark.parametrize("op_type", ["wall", "floor"])
    def test_same_y(self, op_type: str) -> None:
        op = {"type": op_type, "from": [0, 0, 0], "to": [3, 2, 3], "block": "stone"}
        if op_type == "wall":
            op["height"] = 1
        errors = validate(bp(op))
        assert paths(errors) == ["operations[0]"]
        assert errors[0].message == "'from' and 'to' must have the same y coordinate."
        assert errors[0].value == "from.y=0, to.y=2"

    def test_nesting_depth(self) -> None:
        data: dict[str, Any] = SET
        for _ in range(8):
            data = {"type": "repeat", "count": 1, "offset": [0, 0, 0], "operations": [data]}
        errors = validate(bp(data))
        assert len(errors) == 1
        assert errors[0].message == "Operations are nested deeper than 8 levels."
        assert errors[0].path.count(".operations") == 8

        data = SET
        for _ in range(7):
            data = {"type": "repeat", "count": 1, "offset": [0, 0, 0], "operations": [data]}
        assert validate(bp(data)) == []

    def test_multiple_errors_reported_together(self) -> None:
        data = bp(
            {"type": "set", "position": [0, 0, 0], "block": "nope"},
            {"type": "set", "position": [0, 0, 0], "palette": "q"},
            {"type": "floor", "from": [0, 0, 0], "to": [1, 1, 1], "block": "stone", "palette": "p"},
            palettes={"p": [{"block": "stone"}]},
        )
        errors = validate(data)
        assert paths(errors) == [
            "operations[0].block",
            "operations[1].palette",
            "operations[2]",
            "operations[2]",
        ]


class TestBoundsErrors:
    def test_declared_size(self) -> None:
        op = {"type": "fill", "from": [0, 0, 0], "to": [9, 3, 3], "block": "stone"}
        errors = validate(bp(op, size=[4, 4, 4]))
        assert paths(errors) == ["size"]
        assert errors[0].value == "actual 10 x 4 x 4, size 4 x 4 x 4"
        assert validate(bp(op, size=[10, 4, 4])) == []

    def test_size_ignores_position(self) -> None:
        op = {"type": "fill", "from": [100, -50, 100], "to": [103, -48, 103], "block": "stone"}
        assert validate(bp(op, size=[4, 3, 4])) == []

    def test_max_dimension(self) -> None:
        op = {"type": "line", "from": [0, 0, 0], "to": [2000, 0, 0], "block": "stone"}
        errors = validate(bp(op))
        assert paths(errors) == ["operations"]
        assert "1024" in errors[0].message
        assert validate(bp(op), max_dimension=2001) == []
        errors = validate(
            bp({"type": "line", "from": [0, 0, 0], "to": [1023, 0, 0], "block": "stone"})
        )
        assert errors == []

    def test_max_volume(self) -> None:
        op = {"type": "box", "from": [0, 0, 0], "to": [999, 999, 999], "block": "stone"}
        errors = validate(bp(op))
        assert paths(errors) == ["operations"]
        assert "100,000,000" in errors[0].message


class TestFormat:
    def test_valid_message(self) -> None:
        assert format_errors([]) == "Blueprint is valid."

    def test_layout(self) -> None:
        op = {"type": "cylinder", "center": [0, 0, 0], "radius": -5, "height": 3, "block": "stone"}
        text = format_errors(validate(bp(op)))
        assert text == (
            "ERROR operations[0].radius (cylinder)\n"
            "  'radius' must be >= 1.\n"
            "  Current value: -5\n"
            "\n"
            "1 error found."
        )

    def test_plural(self) -> None:
        errors = [ValidationError("", "a."), ValidationError("x", "b.")]
        assert format_errors(errors).endswith("\n\n2 errors found.")
