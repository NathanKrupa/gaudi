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


from gaudi.core import DEFAULT_SCHOOL, VALID_SCHOOLS, Severity

DEFAULT_CONFIG: dict[str, Any] = {
    "packs": [],  # empty = auto-detect
    "severity": "info",
    "exclude": [],
    "rules": {},
    "philosophy": {"school": DEFAULT_SCHOOL},
}

_VALID_SEVERITIES = frozenset(s.value for s in Severity)


def load_config(project_path: Path) -> dict[str, Any]:
    """
    Load configuration from gaudi.toml in the project root.

    Falls back to defaults if no config file exists. Merges the
    ``[gaudi]`` table (general settings) with the ``[philosophy]``
    table (architectural school selection).
    """
    config_path = project_path / "gaudi.toml"

    if not config_path.exists():
        return _clone_defaults()

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    config = _clone_defaults()

    gaudi_config = raw.get("gaudi", {})
    config.update({k: v for k, v in gaudi_config.items() if k in config and k != "philosophy"})

    philosophy_table = raw.get("philosophy")
    if isinstance(philosophy_table, dict):
        merged = dict(config["philosophy"])
        merged.update(philosophy_table)
        config["philosophy"] = merged

    school = config["philosophy"].get("school", DEFAULT_SCHOOL)
    if school not in VALID_SCHOOLS:
        raise ValueError(
            f"gaudi.toml [philosophy].school is {school!r}; must be one of {sorted(VALID_SCHOOLS)}"
        )

    # Parse per-rule severity overrides: [gaudi.rules] RULE-ID = "severity"
    rules_table = gaudi_config.get("rules", {})
    if isinstance(rules_table, dict):
        for rule_code, sev_value in rules_table.items():
            if isinstance(sev_value, str) and sev_value in _VALID_SEVERITIES:
                config["rules"][rule_code] = sev_value
            elif sev_value == "off":
                config["rules"][rule_code] = "off"

    return config


def _clone_defaults() -> dict[str, Any]:
    clone = dict(DEFAULT_CONFIG)
    clone["philosophy"] = dict(DEFAULT_CONFIG["philosophy"])
    return clone


def get_school(config: dict[str, Any]) -> str:
    """Return the active philosophy school for a loaded config dict."""
    philosophy = config.get("philosophy") or {}
    return philosophy.get("school", DEFAULT_SCHOOL)


def get_rule_overrides(config: dict[str, Any]) -> dict[str, str]:
    """Return per-rule severity overrides from ``[gaudi.rules]``.

    Maps rule code → severity string (``"error"``, ``"warn"``, ``"info"``,
    or ``"off"`` to suppress entirely).
    """
    return dict(config.get("rules") or {})
