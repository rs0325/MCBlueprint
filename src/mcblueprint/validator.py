"""Blueprint validation: JSON Schema first, then semantic checks (docs/ARCHITECTURE.md §8)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from functools import reduce
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaError

from mcblueprint import blockdata
from mcblueprint.errors import BlueprintError, ValidationError
from mcblueprint.loader import load_blueprint_dict
from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3
from mcblueprint.operations.base import MAX_DEPTH
from mcblueprint.schema import load_schema

DEFAULT_MAX_DIMENSION = 1024
MAX_VOLUME = 100_000_000

PLACEMENT_TYPES = frozenset(
    {"set", "fill", "box", "wall", "floor", "line", "circle", "cylinder", "sphere"}
)
NESTED_TYPES = frozenset({"mirror", "repeat"})
SAME_Y_TYPES = frozenset({"wall", "floor"})


def validate(
    data: Mapping[str, Any], *, max_dimension: int = DEFAULT_MAX_DIMENSION
) -> list[ValidationError]:
    """Return every problem found in ``data``; an empty list means the Blueprint is valid."""
    errors = validate_schema(data)
    if errors:
        return errors
    errors = _validate_semantics(data)
    if errors:
        return errors
    return _validate_bounds(data, max_dimension)


def validate_schema(data: Any) -> list[ValidationError]:
    validator = Draft202012Validator(load_schema())
    errors = [_convert_schema_error(err, data) for err in validator.iter_errors(data)]
    return _dedupe(sorted(errors, key=lambda e: e.path))


def format_errors(errors: Sequence[ValidationError]) -> str:
    if not errors:
        return "Blueprint is valid."
    blocks = [err.format() for err in errors]
    noun = "error" if len(errors) == 1 else "errors"
    return "\n\n".join(blocks) + f"\n\n{len(errors)} {noun} found."


# --- schema -----------------------------------------------------------------


def _convert_schema_error(err: SchemaError, data: Any) -> ValidationError:
    path = _format_path(err.absolute_path)
    op_type = _op_type_for_path(data, list(err.absolute_path))
    value = err.instance if isinstance(err.instance, str | int | float | bool) else None
    return ValidationError(path, _schema_message(err), op_type, value)


def _schema_message(err: SchemaError) -> str:
    key = err.absolute_path[-1] if err.absolute_path else None
    name = f"'{key}'" if isinstance(key, str) else "value"
    v = err.validator_value
    match err.validator:
        case "required":
            missing = [k for k in v if k not in err.instance]
            return f"Missing required {_plural('property', missing)}: {', '.join(missing)}."
        case "additionalProperties":
            extra = sorted(set(err.instance) - set(err.schema.get("properties", {})))
            return f"Unknown {_plural('property', extra)}: {', '.join(extra)}."
        case "minimum":
            return f"{name} must be >= {v}."
        case "maximum":
            return f"{name} must be <= {v}."
        case "exclusiveMinimum":
            return f"{name} must be > {v}."
        case "const":
            return f"{name} must be {v!r}."
        case "enum":
            return f"{name} must be one of: {', '.join(repr(x) for x in v)}."
        case "type":
            return f"{name} must be of type {v}."
        case "pattern":
            return f"{name} does not match the required format."
        case "minItems":
            return f"{name} must contain at least {v} item{'s' if v != 1 else ''}."
        case "maxItems":
            return f"{name} must contain at most {v} item{'s' if v != 1 else ''}."
        case "minLength":
            return f"{name} must not be empty."
        case "multipleOf":
            return f"{name} must be a multiple of {v}."
        case _:
            return err.message.rstrip(".") + "."


def _plural(word: str, items: Sequence[Any]) -> str:
    return word if len(items) == 1 else word[:-1] + "ies"


def _format_path(parts: Iterable[str | int]) -> str:
    out = ""
    for part in parts:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else part)
    return out


def _op_type_for_path(data: Any, parts: list[str | int]) -> str | None:
    """The ``type`` of the innermost operation that contains ``parts``."""
    node = data
    op_type = None
    for i, part in enumerate(parts):
        try:
            node = node[part]
        except (KeyError, IndexError, TypeError):
            break
        if (
            isinstance(part, int)
            and i > 0
            and parts[i - 1] == "operations"
            and isinstance(node, dict)
        ):
            t = node.get("type")
            if isinstance(t, str):
                op_type = t
    return op_type


def _dedupe(errors: list[ValidationError]) -> list[ValidationError]:
    seen: set[tuple[str, str]] = set()
    unique = []
    for err in errors:
        key = (err.path, err.message)
        if key not in seen:
            seen.add(key)
            unique.append(err)
    return unique


# --- semantics ----------------------------------------------------------------


def _validate_semantics(data: Mapping[str, Any]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    version = data["minecraftVersion"]
    if not blockdata.is_supported(version):
        supported = ", ".join(blockdata.supported_versions())
        errors.append(
            ValidationError(
                "minecraftVersion",
                f"Unsupported Minecraft version. Supported versions: {supported}.",
                None,
                version,
            )
        )
        return errors
    blocks = blockdata.load_block_data(version)

    palettes = data.get("palettes", {})
    for name, entries in palettes.items():
        for index, entry in enumerate(entries):
            _check_block(entry["block"], f"palettes.{name}[{index}].block", None, blocks, errors)

    _walk_operations(data["operations"], "operations", 1, palettes, blocks, errors)
    return errors


def _walk_operations(
    ops: Sequence[Mapping[str, Any]],
    path: str,
    depth: int,
    palettes: Mapping[str, Any],
    blocks: blockdata.BlockData,
    errors: list[ValidationError],
) -> None:
    for index, op in enumerate(ops):
        op_path = f"{path}[{index}]"
        op_type = op["type"]
        if op_type in PLACEMENT_TYPES:
            has_block, has_palette = "block" in op, "palette" in op
            if has_block == has_palette:
                errors.append(
                    ValidationError(
                        op_path, "Exactly one of 'block' or 'palette' must be given.", op_type
                    )
                )
            if has_block:
                _check_block(op["block"], f"{op_path}.block", op_type, blocks, errors)
            if has_palette and op["palette"] not in palettes:
                errors.append(
                    ValidationError(
                        f"{op_path}.palette", "Unknown palette name.", op_type, op["palette"]
                    )
                )
        if op_type in SAME_Y_TYPES and op["from"][1] != op["to"][1]:
            errors.append(
                ValidationError(
                    op_path,
                    "'from' and 'to' must have the same y coordinate.",
                    op_type,
                    f"from.y={op['from'][1]}, to.y={op['to'][1]}",
                )
            )
        if op_type in NESTED_TYPES:
            if depth + 1 > MAX_DEPTH:
                errors.append(
                    ValidationError(
                        f"{op_path}.operations",
                        f"Operations are nested deeper than {MAX_DEPTH} levels.",
                        op_type,
                    )
                )
            else:
                _walk_operations(
                    op["operations"], f"{op_path}.operations", depth + 1, palettes, blocks, errors
                )


def _check_block(
    text: str,
    path: str,
    op_type: str | None,
    blocks: blockdata.BlockData,
    errors: list[ValidationError],
) -> None:
    try:
        state = BlockState.parse(text)
    except BlueprintError as exc:
        errors.append(ValidationError(path, f"{exc}.", op_type, text))
        return
    message = blocks.check_state(state)
    if message is not None:
        errors.append(ValidationError(path, message, op_type, text))


# --- bounds -------------------------------------------------------------------


def _validate_bounds(data: Mapping[str, Any], max_dimension: int) -> list[ValidationError]:
    try:
        blueprint = load_blueprint_dict(data)
    except BlueprintError as exc:
        return [ValidationError("", f"{exc}.")]

    bounds: AABB = reduce(AABB.union, (op.bounds() for op in blueprint.operations))
    size = bounds.size
    errors: list[ValidationError] = []
    if max(size.x, size.y, size.z) > max_dimension:
        errors.append(
            ValidationError(
                "operations",
                f"Structure exceeds the maximum dimension of {max_dimension} blocks per axis.",
                None,
                f"{size.x} x {size.y} x {size.z} ({bounds})",
            )
        )
    elif bounds.volume > MAX_VOLUME:
        errors.append(
            ValidationError(
                "operations",
                f"Structure bounding box exceeds {MAX_VOLUME:,} cells.",
                None,
                f"{size.x} x {size.y} x {size.z}",
            )
        )
    limit: Vec3 | None = blueprint.size
    if limit is not None and (size.x > limit.x or size.y > limit.y or size.z > limit.z):
        errors.append(
            ValidationError(
                "size",
                "Structure is larger than the declared size.",
                None,
                f"actual {size.x} x {size.y} x {size.z}, size {limit.x} x {limit.y} x {limit.z}",
            )
        )
    return errors
