"""Access to the bundled Blueprint JSON Schema.

The canonical schema lives in this package so it is always available at runtime.
``schema/blueprint.schema.json`` at the repository root is a copy for editors and
external tools; ``tests/test_schema.py`` checks that both files are identical.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

SCHEMA_FILENAME = "blueprint.schema.json"


@cache
def load_schema() -> dict[str, Any]:
    """Return the bundled Blueprint JSON Schema as a dict (cached)."""
    text = resources.files(__name__).joinpath(SCHEMA_FILENAME).read_text(encoding="utf-8")
    return json.loads(text)
