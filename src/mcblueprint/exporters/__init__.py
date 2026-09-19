"""Output formats. ``EXPORTERS`` maps a ``--format`` name to its exporter class."""

from mcblueprint.exporters.base import Exporter
from mcblueprint.exporters.litematic import LitematicExporter
from mcblueprint.exporters.schem import SchemExporter

EXPORTERS: dict[str, type[Exporter]] = {
    SchemExporter.format: SchemExporter,
    LitematicExporter.format: LitematicExporter,
}

__all__ = ["EXPORTERS", "Exporter", "LitematicExporter", "SchemExporter"]
