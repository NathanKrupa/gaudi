"""
The Gaudí engine — orchestrates pack discovery, loading, and execution.
"""

from __future__ import annotations

import logging
import sys
from importlib.metadata import entry_points
from pathlib import Path

from gaudi.core import Finding, Severity
from gaudi.pack import Pack

logger = logging.getLogger(__name__)


def apply_overrides(
    findings: list[Finding],
    rule_overrides: dict[str, str],
) -> list[Finding]:
    """Apply per-rule severity overrides and suppressions.

    ``rule_overrides`` maps rule code → severity string or ``"off"``.
    """
    if not rule_overrides:
        return findings
    result: list[Finding] = []
    for f in findings:
        override = rule_overrides.get(f.code)
        if override is None:
            result.append(f)
        elif override == "off":
            continue
        else:
            result.append(f.with_severity(Severity(override)))
    return result


class Engine:
    def __init__(self) -> None:
        self._packs: dict[str, Pack] = {}

    def discover_packs(self) -> None:
        if sys.version_info >= (3, 12):
            eps = entry_points(group="gaudi.packs")
        else:
            eps = entry_points().get("gaudi.packs", [])

        for ep in eps:
            try:
                pack_class = ep.load()
                pack = pack_class()
                self._packs[ep.name] = pack
            except Exception as e:
                logger.warning("Failed to load pack '%s': %s", ep.name, e)

    def register_pack(self, pack: Pack) -> None:
        self._packs[pack.name] = pack

    @property
    def packs(self) -> dict[str, Pack]:
        return dict(self._packs)

    def detect_packs(self, path: Path) -> list[Pack]:
        return [pack for pack in self._packs.values() if pack.can_handle(path)]

    def check(
        self,
        path: Path,
        pack_names: list[str] | None = None,
        min_severity: Severity = Severity.INFO,
        school: str | None = None,
        rule_overrides: dict[str, str] | None = None,
    ) -> list[Finding]:
        """
        Run architectural checks on the given path.

        Args:
            path: File or directory to check.
            pack_names: Specific packs to use. If None, auto-detect.
            min_severity: Minimum severity level to include in results.
            school: Philosophy school to filter rules by.
            rule_overrides: Per-rule severity overrides (code → severity or "off").

        Returns:
            List of findings sorted by severity then code.
        """
        if pack_names:
            packs = [self._packs[name] for name in pack_names if name in self._packs]
        else:
            packs = self.detect_packs(path)

        if not packs:
            return []

        findings: list[Finding] = []
        for pack in packs:
            pack_findings = pack.check(path, school=school)
            findings.extend(pack_findings)

        # Apply per-rule severity overrides and suppressions
        if rule_overrides:
            findings = apply_overrides(findings, rule_overrides)

        # Filter by minimum severity
        findings = [f for f in findings if f.severity.priority <= min_severity.priority]

        return sorted(findings, key=lambda f: (f.severity.priority, f.code))

    def format_summary(self, findings: list[Finding]) -> str:
        errors = sum(1 for f in findings if f.severity == Severity.ERROR)
        warnings = sum(1 for f in findings if f.severity == Severity.WARN)
        infos = sum(1 for f in findings if f.severity == Severity.INFO)

        # Count unique files
        files = {f.file for f in findings if f.file}

        parts = []
        if errors:
            parts.append(f"{errors} error{'s' if errors != 1 else ''}")
        if warnings:
            parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")
        if infos:
            parts.append(f"{infos} info{'s' if infos != 1 else ''}")

        if not parts:
            return "No architectural issues found. Structurally sound."

        count_str = ", ".join(parts)
        file_str = f" across {len(files)} file{'s' if len(files) != 1 else ''}" if files else ""
        return f"Found {count_str}{file_str}."
