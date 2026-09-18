"""Exception and error types shared across MCBlueprint."""

from __future__ import annotations

from dataclasses import dataclass


class BlueprintError(Exception):
    """I/O, syntax or internal consistency error (CLI exit code 2)."""


@dataclass(frozen=True)
class ValidationError:
    """One problem found while validating a Blueprint.

    ``path`` is a JSON path such as ``operations[4]`` or
    ``palettes.stone_wall[1].block`` (empty string for the top level).
    """

    path: str
    message: str
    op_type: str | None = None
    value: object | None = None

    def format(self) -> str:
        header = f"ERROR {self.path}" if self.path else "ERROR (top level)"
        if self.op_type:
            header += f" ({self.op_type})"
        lines = [header, f"  {self.message}"]
        if self.value is not None:
            lines.append(f"  Current value: {self.value}")
        return "\n".join(lines)


class BlueprintValidationError(BlueprintError):
    """Raised when a Blueprint fails validation (CLI exit code 1)."""

    def __init__(self, errors: list[ValidationError]) -> None:
        self.errors = list(errors)
        count = len(self.errors)
        noun = "error" if count == 1 else "errors"
        super().__init__(f"{count} {noun} found.")
