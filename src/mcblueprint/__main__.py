"""Allow running the CLI with ``python -m mcblueprint``."""

import sys

from mcblueprint.cli import main

if __name__ == "__main__":
    sys.exit(main())
