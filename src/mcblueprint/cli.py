"""Command-line entry point for MCBlueprint (see docs/ARCHITECTURE.md section 11).

mcblueprint validate <blueprint.json> [--strict] [--max-dimension N]
mcblueprint build    <blueprint.json> [-o DIR|FILE] [--format schem] [--seed N]
                                      [--strict] [--max-dimension N]
mcblueprint inspect  <blueprint.json> [--json] [--max-dimension N]
mcblueprint stats    <blueprint.json> [--json] [--seed N] [--max-dimension N]
mcblueprint preview  <blueprint.json> [-o DIR] [--views top,north,east,isometric] [--scale N]
                                      [--seed N] [--max-dimension N]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from functools import reduce
from pathlib import Path
from typing import Any, TextIO

from mcblueprint import __version__, components
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters import EXPORTERS
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict, read_blueprint_json
from mcblueprint.model.blueprint import Blueprint
from mcblueprint.model.vec import AABB
from mcblueprint.operations.base import Operation
from mcblueprint.operations.nested import NestedOperation
from mcblueprint.preview import DEFAULT_VIEWS, VIEWS, write_previews
from mcblueprint.support import check_support, format_warnings
from mcblueprint.validator import DEFAULT_MAX_DIMENSION, format_errors, validate
from mcblueprint.volume import BlockVolume

EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_USAGE_ERROR = 2

DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_PREVIEW_DIR = Path("preview")
AIR_ID = "minecraft:air"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcblueprint",
        description="Build Minecraft schematics from Blueprint JSON.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    validate_parser = subparsers.add_parser(
        "validate", help="check a blueprint and report every problem"
    )
    _add_common_arguments(validate_parser)
    _add_strict_argument(validate_parser)

    build_parser_ = subparsers.add_parser(
        "build", help="validate a blueprint and write the schematic"
    )
    _add_common_arguments(build_parser_)
    _add_strict_argument(build_parser_)
    build_parser_.add_argument(
        "-o",
        "--output",
        default=None,
        help="output file, or directory to place <name>.<ext> in (default: output/)",
    )
    build_parser_.add_argument(
        "--format",
        choices=sorted(EXPORTERS),
        default="schem",
        help="output format (default: schem)",
    )
    _add_seed_argument(build_parser_)

    inspect_parser = subparsers.add_parser(
        "inspect", help="show a blueprint's metadata and bounds without generating it"
    )
    _add_common_arguments(inspect_parser)
    inspect_parser.add_argument("--json", action="store_true", help="machine-readable output")

    stats_parser = subparsers.add_parser(
        "stats", help="generate a blueprint and count blocks by state"
    )
    _add_common_arguments(stats_parser)
    stats_parser.add_argument("--json", action="store_true", help="machine-readable output")
    _add_seed_argument(stats_parser)

    preview_parser = subparsers.add_parser(
        "preview", help="render PNG previews (needs the optional Pillow dependency)"
    )
    _add_common_arguments(preview_parser)
    preview_parser.add_argument(
        "-o", "--output", default=None, help="directory for the images (default: preview/)"
    )
    preview_parser.add_argument(
        "--views",
        default=",".join(DEFAULT_VIEWS),
        help=f"comma-separated views from {', '.join(VIEWS)} (default: {','.join(DEFAULT_VIEWS)})",
    )
    preview_parser.add_argument(
        "--scale", type=int, default=8, help="pixels per block (default: 8)"
    )
    _add_seed_argument(preview_parser)
    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("blueprint", type=Path, help="path to the Blueprint JSON file")
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=DEFAULT_MAX_DIMENSION,
        metavar="N",
        help=f"maximum size per axis in blocks (default: {DEFAULT_MAX_DIMENSION})",
    )


def _add_strict_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat support warnings (unsupported lanterns, torches, ...) as errors",
    )


def _add_seed_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--seed", type=int, default=None, help="override the blueprint's palette seed"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE_ERROR
    commands = {
        "validate": _run_validate,
        "build": _run_build,
        "inspect": _run_inspect,
        "stats": _run_stats,
        "preview": _run_preview,
    }
    try:
        paths = components.default_search_paths(args.blueprint)
        with components.component_search_paths(paths):
            return commands[args.command](args, sys.stdout)
    except BlueprintError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR


def _run_validate(args: argparse.Namespace, out: TextIO) -> int:
    data = read_blueprint_json(args.blueprint)
    errors = validate(data, max_dimension=args.max_dimension)
    print(format_errors(errors), file=out)
    if errors:
        return EXIT_VALIDATION_ERROR
    volume = generate(load_blueprint_dict(data))
    return _report_warnings(volume, args.strict, out)


def _report_warnings(volume: BlockVolume, strict: bool, out: TextIO) -> int:
    """Print support warnings; exit code 1 only when ``strict`` and there are any."""
    warnings = check_support(volume)
    if not warnings:
        return EXIT_OK
    print("", file=out)
    print(format_warnings(warnings), file=out)
    return EXIT_VALIDATION_ERROR if strict else EXIT_OK


def _load_validated(args: argparse.Namespace, out: TextIO) -> Blueprint | None:
    """Validate and load; prints the errors and returns None when invalid."""
    data = read_blueprint_json(args.blueprint)
    errors = validate(data, max_dimension=args.max_dimension)
    if errors:
        print(format_errors(errors), file=out)
        return None
    return load_blueprint_dict(data)


def _run_build(args: argparse.Namespace, out: TextIO) -> int:
    blueprint = _load_validated(args, out)
    if blueprint is None:
        return EXIT_VALIDATION_ERROR
    volume = generate(blueprint, seed=args.seed)
    warnings = check_support(volume)
    if warnings:
        print(format_warnings(warnings), file=out)
        print("", file=out)
        if args.strict:
            print("Not written because of warnings (--strict).", file=out)
            return EXIT_VALIDATION_ERROR
    exporter = EXPORTERS[args.format]()
    out_path = resolve_output_path(args.output, args.blueprint, exporter.extension)
    exporter.export(volume, blueprint, out_path)

    bounds = volume.bounds()
    assert bounds is not None  # export() rejects empty volumes
    size = bounds.size
    print(f"Wrote {out_path.as_posix()}", file=out)
    print(f"Bounds: {bounds}  ({size.x} x {size.y} x {size.z})", file=out)
    print(f"Blocks: {len(volume)}", file=out)
    return EXIT_OK


def _run_inspect(args: argparse.Namespace, out: TextIO) -> int:
    blueprint = _load_validated(args, out)
    if blueprint is None:
        return EXIT_VALIDATION_ERROR
    info = inspect_blueprint(blueprint)
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2), file=out)
        return EXIT_OK
    b = info["bounds"]
    s = info["size"]
    lines = [
        f"Name: {info['name']}",
        f"Minecraft: {info['minecraftVersion']}",
        "",
        "Bounds:",
        f"X: {b['min'][0]} .. {b['max'][0]}",
        f"Y: {b['min'][1]} .. {b['max'][1]}",
        f"Z: {b['min'][2]} .. {b['max'][2]}",
        f"Size: {s[0]} x {s[1]} x {s[2]}",
        "",
        f"Operations: {info['operations']} (top level: {info['topLevelOperations']})",
        f"Palettes: {info['palettes']}",
        f"Seed: {info['seed']}",
        f"Origin: {info['origin']}",
    ]
    if info["declaredSize"] is not None:
        lines.append(f"Declared size: {info['declaredSize']}")
    if info["description"]:
        lines.append(f"Description: {info['description']}")
    print("\n".join(lines), file=out)
    return EXIT_OK


def inspect_blueprint(blueprint: Blueprint) -> dict[str, Any]:
    """Metadata and analytic bounds (no generation) as a JSON-friendly dict."""
    bounds: AABB = reduce(AABB.union, (op.bounds() for op in blueprint.operations))
    return {
        "name": blueprint.name,
        "minecraftVersion": blueprint.minecraft_version,
        "description": blueprint.description,
        "author": blueprint.author,
        "seed": blueprint.seed,
        "origin": blueprint.origin.to_list(),
        "declaredSize": blueprint.size.to_list() if blueprint.size else None,
        "bounds": {"min": bounds.min.to_list(), "max": bounds.max.to_list()},
        "size": bounds.size.to_list(),
        "topLevelOperations": len(blueprint.operations),
        "operations": count_operations(blueprint.operations),
        "palettes": len(blueprint.palettes),
    }


def count_operations(operations: Sequence[Operation]) -> int:
    """Number of operations including those nested in mirror / repeat."""
    total = 0
    for op in operations:
        total += 1
        if isinstance(op, NestedOperation):
            total += count_operations(op.operations)
    return total


def _run_stats(args: argparse.Namespace, out: TextIO) -> int:
    blueprint = _load_validated(args, out)
    if blueprint is None:
        return EXIT_VALIDATION_ERROR
    volume = generate(blueprint, seed=args.seed)
    info = stats_volume(volume)
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2), file=out)
        return EXIT_OK
    print(f"Total blocks: {info['totalBlocks']} (air: {info['airBlocks']})", file=out)
    bounds = info["bounds"]
    if bounds is not None:
        s = info["size"]
        print(
            f"Bounds: X {bounds['min'][0]}..{bounds['max'][0]}  "
            f"Y {bounds['min'][1]}..{bounds['max'][1]}  "
            f"Z {bounds['min'][2]}..{bounds['max'][2]}  ({s[0]} x {s[1]} x {s[2]})",
            file=out,
        )
    print("", file=out)
    counts = info["blocks"]
    width = max((len(str(n)) for n in counts.values()), default=1)
    for state, count in counts.items():
        print(f"{count:>{width}}  {state}", file=out)
    return EXIT_OK


def stats_volume(volume: BlockVolume) -> dict[str, Any]:
    """Block counts (air excluded from the list and total) as a JSON-friendly dict."""
    counts = volume.count_by_state()
    air = counts.pop(AIR_ID, 0)
    bounds = volume.bounds()
    return {
        "totalBlocks": len(volume) - air,
        "airBlocks": air,
        "bounds": (
            None if bounds is None else {"min": bounds.min.to_list(), "max": bounds.max.to_list()}
        ),
        "size": None if bounds is None else bounds.size.to_list(),
        "blocks": counts,
    }


def _run_preview(args: argparse.Namespace, out: TextIO) -> int:
    views = [v.strip() for v in args.views.split(",") if v.strip()]
    unknown = [v for v in views if v not in VIEWS]
    if unknown or not views:
        raise BlueprintError(
            f"Unknown view(s): {', '.join(unknown) or '(none)'}; choose from {', '.join(VIEWS)}"
        )
    if args.scale < 1:
        raise BlueprintError("--scale must be >= 1")
    blueprint = _load_validated(args, out)
    if blueprint is None:
        return EXIT_VALIDATION_ERROR
    volume = generate(blueprint, seed=args.seed)
    out_dir = Path(args.output) if args.output else DEFAULT_PREVIEW_DIR
    for path in write_previews(volume, out_dir, args.blueprint.stem, views, args.scale):
        print(f"Wrote {path.as_posix()}", file=out)
    return EXIT_OK


def resolve_output_path(output: str | None, blueprint_path: Path, extension: str) -> Path:
    """``-o`` semantics: none -> output/<stem><ext>; a directory -> inside it; else the file.

    ``output`` counts as a directory when it exists as one, ends with a path
    separator, or has no file extension.
    """
    default_name = blueprint_path.stem + extension
    if output is None:
        return DEFAULT_OUTPUT_DIR / default_name
    path = Path(output)
    if path.is_dir() or output.endswith(("/", "\\")) or not path.suffix:
        return path / default_name
    return path
