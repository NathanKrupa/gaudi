"""Fixture for STRUCT-010: an executable entrypoint bootstrapping sys.path.

The file has an ``if __name__ == "__main__":`` guard, so it is run directly
rather than imported. Prepending its own location to ``sys.path`` to find
siblings before the package is installed is the by-design pattern — STRUCT-010
must not fire.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    pass


if __name__ == "__main__":
    main()
