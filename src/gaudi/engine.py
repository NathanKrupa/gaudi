"""
The Gaudí engine — orchestrates pack discovery, loading, and execution.
"""

from __future__ import annotations

import logging
import sys
from importlib.metadata import entry_points
from pathlib import Path

from gaudi.core import CheckResult, FileSkip, Finding, PackError, Severity
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
        self._pack_errors: list[PackError] = []

    def discover_packs(self) -> None:
        """Load every installed pack, recording the ones that could not load.

        A pack that fails to load takes its whole rule catalog with it, so a
        run that ignored the failure would report nothing about everything that
        pack measures — indistinguishable from a clean project. The failure is
        recorded on :attr:`pack_errors`, which rides on every ``CheckResult``
        and turns the run red under ``--exit-code``. The log line stays, but it
        is no longer the only signal: nothing reads a logger in CI.

        Each discovery replaces the previous error record, since the record
        describes the discovery that just ran.
        """
        if sys.version_info >= (3, 12):
            eps = entry_points(group="gaudi.packs")
        else:
            eps = entry_points().get("gaudi.packs", [])

        errors: list[PackError] = []
        for ep in eps:
            try:
                pack_class = ep.load()
                pack = pack_class()
            except Exception as e:
                # Broad by necessity: an entry point can fail in any way its
                # author's import chain can fail, and one broken pack must not
                # cost the others their run. Nothing is swallowed — the failure
                # is recorded below, reported in every output format, and
                # exits 2.
                errors.append(PackError(pack=ep.name, error=f"{type(e).__name__}: {e}"))
                continue
            self._packs[ep.name] = pack

        self._pack_errors = errors
        for failure in errors:
            logger.warning("Failed to load pack '%s': %s", failure.pack, failure.error)

    def register_pack(self, pack: Pack) -> None:
        self._packs[pack.name] = pack

    @property
    def packs(self) -> dict[str, Pack]:
        return dict(self._packs)

    @property
    def pack_errors(self) -> list[PackError]:
        """The packs the last discovery could not load, and why."""
        return list(self._pack_errors)

    def detect_packs(self, path: Path) -> list[Pack]:
        return [pack for pack in self._packs.values() if pack.can_handle(path)]

    def check_result(
        self,
        path: Path,
        pack_names: list[str] | None = None,
        min_severity: Severity = Severity.INFO,
        school: str | None = None,
        rule_overrides: dict[str, str] | None = None,
    ) -> CheckResult:
        """
        Run architectural checks on the given path.

        Args:
            path: File or directory to check.
            pack_names: Specific packs to use. If None, auto-detect.
            min_severity: Minimum severity level to include in results.
            school: Philosophy school to filter rules by.
            rule_overrides: Per-rule severity overrides (code → severity or "off").

        Returns:
            Findings sorted by severity then code, the files no pack could
            read, and the packs that could not be loaded at all. Neither skips
            nor pack errors are filtered by ``min_severity`` or suppressed by
            ``rule_overrides`` — both are the absence of evidence, not findings
            whose importance a caller can rank down.
        """
        if pack_names:
            packs = [self._packs[name] for name in pack_names if name in self._packs]
        else:
            packs = self.detect_packs(path)

        if not packs:
            return CheckResult(pack_errors=list(self._pack_errors))

        findings: list[Finding] = []
        skipped: list[FileSkip] = []
        for pack in packs:
            result = pack.check_result(path, school=school)
            findings.extend(result.findings)
            skipped.extend(result.skipped)

        # Apply per-rule severity overrides and suppressions
        if rule_overrides:
            findings = apply_overrides(findings, rule_overrides)

        # Filter by minimum severity
        findings = [f for f in findings if f.severity.priority <= min_severity.priority]

        return CheckResult(
            findings=sorted(findings, key=lambda f: (f.severity.priority, f.code)),
            skipped=sorted(skipped, key=lambda s: s.file),
            pack_errors=list(self._pack_errors),
        )

    def check(
        self,
        path: Path,
        pack_names: list[str] | None = None,
        min_severity: Severity = Severity.INFO,
        school: str | None = None,
        rule_overrides: dict[str, str] | None = None,
    ) -> list[Finding]:
        """Findings only. See :meth:`check_result` for the skipped files too."""
        return self.check_result(
            path,
            pack_names=pack_names,
            min_severity=min_severity,
            school=school,
            rule_overrides=rule_overrides,
        ).findings

    def format_skips(self, skipped: list[FileSkip]) -> str:
        """One line summarising what the run could not read.

        Returns the empty string when nothing was skipped, so a clean run says
        nothing about skips at all and the two states never read alike.
        """
        if not skipped:
            return ""
        count = len(skipped)
        return f"{count} file{'s' if count != 1 else ''} skipped — Gaudi could not parse them."

    def format_pack_errors(self, pack_errors: list[PackError]) -> str:
        """One line summarising which rule catalogs never ran.

        Returns the empty string when every pack loaded, so a healthy run says
        nothing about pack errors at all and the two states never read alike.
        """
        if not pack_errors:
            return ""
        count = len(pack_errors)
        return (
            f"{count} pack{'s' if count != 1 else ''} failed to load — "
            f"the rules {'they own' if count != 1 else 'it owns'} never ran."
        )

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
