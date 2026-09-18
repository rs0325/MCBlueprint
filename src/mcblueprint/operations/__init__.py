"""Operation implementations. Importing this package registers every built-in type."""

from mcblueprint.operations.base import (
    BlockSpec,
    ExecutionContext,
    Operation,
    PlacementOperation,
    Transform,
)
from mcblueprint.operations.registry import OPERATIONS, build_operation, build_operations, register

__all__ = [
    "OPERATIONS",
    "BlockSpec",
    "ExecutionContext",
    "Operation",
    "PlacementOperation",
    "Transform",
    "build_operation",
    "build_operations",
    "register",
]
