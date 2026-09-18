"""Command-line entry point for MCBlueprint.

Subcommands (validate, build) are added by later issues; for now the CLI only
exposes ``--version``.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from mcblueprint import __version__

EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_USAGE_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcblueprint",
        description="Build Minecraft schematics from Blueprint JSON.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_subparsers(dest="command", metavar="<command>")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE_ERROR
    return EXIT_OK
