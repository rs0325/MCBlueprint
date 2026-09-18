"""Exporter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from mcblueprint.model.blueprint import Blueprint
from mcblueprint.volume import BlockVolume


class Exporter(ABC):
    format: ClassVar[str]
    extension: ClassVar[str]

    @abstractmethod
    def export(self, volume: BlockVolume, blueprint: Blueprint, out_path: Path) -> None:
        """Write ``volume`` to ``out_path`` in this exporter's format."""
