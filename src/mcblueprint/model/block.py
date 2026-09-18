"""Block state parsing and normalisation (see docs/FORMAT.md section 4)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from mcblueprint.errors import BlueprintError

DEFAULT_NAMESPACE = "minecraft"

BLOCK_PATTERN = re.compile(
    r"^(?:(?P<namespace>[a-z0-9_.-]+):)?(?P<id>[a-z0-9_./-]+)"
    r"(?:\[(?P<props>[a-z_]+=[a-z0-9_]+(?:,[a-z_]+=[a-z0-9_]+)*)\])?$"
)


@dataclass(frozen=True, slots=True)
class BlockState:
    """A namespaced block id with sorted properties, e.g. ``minecraft:oak_stairs``."""

    id: str
    properties: tuple[tuple[str, str], ...] = ()

    @classmethod
    def parse(cls, text: str) -> BlockState:
        """Parse ``[namespace:]id[prop=value,...]`` and normalise it."""
        match = BLOCK_PATTERN.match(text)
        if match is None:
            raise BlueprintError(f"Invalid block specification: {text!r}")
        namespace = match.group("namespace") or DEFAULT_NAMESPACE
        block_id = f"{namespace}:{match.group('id')}"
        props: dict[str, str] = {}
        if match.group("props"):
            for pair in match.group("props").split(","):
                name, value = pair.split("=", 1)
                if name in props:
                    raise BlueprintError(f"Duplicate property {name!r} in block {text!r}")
                props[name] = value
        return cls(block_id, tuple(sorted(props.items())))

    @classmethod
    def of(cls, block_id: str, **properties: str) -> BlockState:
        """Build a state from an id and keyword properties (internal / test helper)."""
        namespace, _, name = block_id.rpartition(":")
        full_id = f"{namespace or DEFAULT_NAMESPACE}:{name}"
        return cls(full_id, tuple(sorted(properties.items())))

    def get(self, name: str) -> str | None:
        for key, value in self.properties:
            if key == name:
                return value
        return None

    def with_property(self, name: str, value: str) -> BlockState:
        props = dict(self.properties)
        props[name] = value
        return BlockState(self.id, tuple(sorted(props.items())))

    def with_defaults(self, defaults: Mapping[str, str]) -> BlockState:
        """Fill in unspecified properties from ``defaults`` (used by exporters)."""
        props = dict(defaults)
        props.update(self.properties)
        return BlockState(self.id, tuple(sorted(props.items())))

    def to_string(self) -> str:
        if not self.properties:
            return self.id
        props = ",".join(f"{k}={v}" for k, v in self.properties)
        return f"{self.id}[{props}]"

    def __str__(self) -> str:
        return self.to_string()
