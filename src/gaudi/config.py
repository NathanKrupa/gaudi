"""
Configuration loader for Gaudí.

Reads gaudi.toml from the project root and provides defaults.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib


DEFAULT_CONFIG = {
    "packs": [],  # empty = auto-detect
    "severity": "info",
    "exclude": [],
    "rules": {},
}


def load_config(project_path: Path) -> dict[str, Any]:
    """
    Load configuration from gaudi.toml in the project root.

    Falls back to defaults if no config file exists.
    """
    config_path = project_path / "gaudi.toml"

    if not config_path.exists():
        return dict(DEFAULT_CONFIG)

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    gaudi_config = raw.get("gaudi", {})

    config = dict(DEFAULT_CONFIG)
    config.update({k: v for k, v in gaudi_config.items() if k in DEFAULT_CONFIG})

    return config
