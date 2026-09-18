"""Load Blueprint JSON into the :class:`~mcblueprint.model.Blueprint` model.

The loader expects data that already passed the JSON Schema (validator.py wires
that in); shape problems it still encounters are reported as
:class:`~mcblueprint.errors.BlueprintError` with a JSON path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcblueprint.errors import BlueprintError
from mcblueprint.model.block import BlockState
from mcblueprint.model.blueprint import FORMAT_VERSION, Blueprint
from mcblueprint.model.palette import Palette, PaletteEntry
from mcblueprint.model.vec import Vec3
from mcblueprint.operations.registry import build_operations


def read_blueprint_json(path: str | Path) -> dict[str, Any]:
    """Read and parse a Blueprint JSON file without converting it."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise BlueprintError(f"Blueprint file not found: {path}") from None
    except OSError as exc:
        raise BlueprintError(f"Cannot read blueprint file {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BlueprintError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BlueprintError(f"Blueprint root must be a JSON object: {path}")
    return data


def load_blueprint(path: str | Path) -> Blueprint:
    """Read a Blueprint JSON file and convert it to the model."""
    return load_blueprint_dict(read_blueprint_json(path))


def load_blueprint_dict(data: dict[str, Any]) -> Blueprint:
    """Convert already-parsed Blueprint JSON to the model."""
    format_version = data.get("formatVersion")
    if format_version != FORMAT_VERSION:
        raise BlueprintError(
            f"Unsupported formatVersion {format_version!r} (expected {FORMAT_VERSION})"
        )
    operations = data.get("operations")
    if not isinstance(operations, list) or not operations:
        raise BlueprintError("operations must be a non-empty array")

    return Blueprint(
        format_version=format_version,
        minecraft_version=_require_str(data, "minecraftVersion"),
        name=_require_str(data, "name"),
        operations=build_operations(operations, "operations"),
        description=_optional_str(data, "description"),
        author=_optional_str(data, "author"),
        seed=int(data.get("seed", 0)),
        origin=_vec(data.get("origin", [0, 0, 0]), "origin"),
        size=_vec(data["size"], "size") if "size" in data else None,
        palettes=_palettes(data.get("palettes", {})),
        metadata=data.get("metadata"),
    )


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise BlueprintError(f"{key} must be a non-empty string")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise BlueprintError(f"{key} must be a string")
    return value


def _vec(value: Any, path: str) -> Vec3:
    if not isinstance(value, list):
        raise BlueprintError(f"{path} must be an array of 3 integers")
    try:
        return Vec3.from_seq(value)
    except (ValueError, TypeError):
        raise BlueprintError(f"{path} must be an array of 3 integers") from None


def _palettes(value: Any) -> dict[str, Palette]:
    if not isinstance(value, dict):
        raise BlueprintError("palettes must be an object")
    palettes: dict[str, Palette] = {}
    for name, raw_entries in value.items():
        if not isinstance(raw_entries, list) or not raw_entries:
            raise BlueprintError(f"palettes.{name} must be a non-empty array")
        entries = []
        for index, raw in enumerate(raw_entries):
            path = f"palettes.{name}[{index}]"
            if not isinstance(raw, dict) or "block" not in raw:
                raise BlueprintError(f"{path} must be an object with a block")
            try:
                block = BlockState.parse(raw["block"])
            except BlueprintError as exc:
                raise BlueprintError(f"{path}.block: {exc}") from None
            weight = raw.get("weight", 1)
            if not isinstance(weight, int | float) or weight <= 0:
                raise BlueprintError(f"{path}.weight must be a positive number")
            entries.append(PaletteEntry(block, float(weight)))
        palettes[name] = Palette(name, tuple(entries))
    return palettes
