"""Top-level Blueprint model (see docs/FORMAT.md section 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mcblueprint.model.palette import Palette
from mcblueprint.model.vec import Vec3

if TYPE_CHECKING:
    from mcblueprint.operations.base import Operation

FORMAT_VERSION = 1


@dataclass
class Blueprint:
    format_version: int
    minecraft_version: str
    name: str
    operations: list[Operation]
    description: str | None = None
    author: str | None = None
    seed: int = 0
    origin: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    size: Vec3 | None = None
    palettes: dict[str, Palette] = field(default_factory=dict)
    metadata: dict[str, Any] | None = None
