"""Command-line entry point for MCBlueprint (see docs/ARCHITECTURE.md section 11).

mcblueprint validate <blueprint.json> [--max-dimension N]
mcblueprint build    <blueprint.json> [-o DIR|FILE] [--format schem] [--seed N]
                                      [--max-dimension N]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from mcblueprint import __version__
from mcblueprint.errors import BlueprintError
from mcblueprint.exporters import EXPORTERS
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint_dict, read_blueprint_json
from mcblueprint.validator import DEFAULT_MAX_DIMENSION, format_errors, validate

EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_USAGE_ERROR = 2

DEFAULT_OUTPUT_DIR = Path("output")


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

    build_parser_ = subparsers.add_parser(
        "build", help="validate a blueprint and write the schematic"
    )
    _add_common_arguments(build_parser_)
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
    build_parser_.add_argument(
        "--seed", type=int, default=None, help="override the blueprint's palette seed"
    )
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE_ERROR
    try:
        if args.command == "validate":
            return _run_validate(args, sys.stdout)
        return _run_build(args, sys.stdout)
    except BlueprintError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR


def _run_validate(args: argparse.Namespace, out: TextIO) -> int:
    data = read_blueprint_json(args.blueprint)
    errors = validate(data, max_dimension=args.max_dimension)
    print(format_errors(errors), file=out)
    return EXIT_VALIDATION_ERROR if errors else EXIT_OK


def _run_build(args: argparse.Namespace, out: TextIO) -> int:
    data = read_blueprint_json(args.blueprint)
    errors = validate(data, max_dimension=args.max_dimension)
    if errors:
        print(format_errors(errors), file=out)
        return EXIT_VALIDATION_ERROR

    blueprint = load_blueprint_dict(data)
    volume = generate(blueprint, seed=args.seed)
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
