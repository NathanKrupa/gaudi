# ABOUTME: Reports which pack rules have / lack a fixture directory under tests/fixtures/<pack>/.
# ABOUTME: Wired as the `gaudi-fixture-coverage` console entry point in pyproject.toml.
"""Fixture coverage reporter for the Gaudi rule corpus.

Walks every Rule registered across every pack and checks whether
``tests/fixtures/<pack-name>/<RULE-ID>/`` exists with the minimum required
artifacts (one fail file, one pass file, one expected.json).

Default exit code is 0 even when rules are uncovered: this is the warn-mode
described in docs/testing-fixtures.md. CI can be flipped to ``--strict`` once
the migration backlog is drained.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from gaudi.core import Rule
from gaudi.packs.ops.rules import ALL_RULES as OPS_RULES
from gaudi.packs.python.rules import ALL_RULES as PYTHON_RULES


# Resolve the project root by walking up until we find pyproject.toml. This lets
# the tool be invoked as a console script from anywhere inside a Gaudi checkout.
def _find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return start


REPO_ROOT = _find_repo_root(Path.cwd())
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"

# Each entry maps a pack name (= subdirectory under tests/fixtures/) to its
# rule list. Adding a new pack means adding one row here.
_PACK_RULES: tuple[tuple[str, tuple[Rule, ...]], ...] = (
    ("python", tuple(PYTHON_RULES)),
    ("ops", tuple(OPS_RULES)),
)

_COL_RULE = "<14"
_COL_STATUS = "<8"
_COL_COUNT = ">4"
_COL_EXPECTED = "<14"


@dataclass
class RuleCoverage:
    rule_id: str
    has_dir: bool
    fail_count: int
    pass_count: int
    has_expected_json: bool
    expected_json_valid: bool
    vacuous_pass: bool = False

    @property
    def is_complete(self) -> bool:
        return (
            self.has_dir
            and self.fail_count >= 1
            and self.pass_count >= 1
            and self.has_expected_json
            and self.expected_json_valid
            and not self.vacuous_pass
        )

    @property
    def status(self) -> str:
        if self.vacuous_pass:
            return "VACUOUS"
        if self.is_complete:
            return "OK"
        if not self.has_dir:
            return "MISSING"
        return "PARTIAL"


def _validate_expected_json(path: Path, rule_id: str) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return data.get("rule_id") == rule_id and "fixtures" in data


def _count_fixtures(rule_dir: Path, prefix: str) -> int:
    """Count fixtures with the given prefix -- both single-file (.py) and multi-file (dir)."""
    files = sum(1 for p in rule_dir.glob(f"{prefix}*.py") if p.is_file())
    dirs = sum(1 for p in rule_dir.glob(f"{prefix}*") if p.is_dir())
    return files + dirs


def _has_library_import(fixture_path: Path, library: str) -> bool:
    """Check if a fixture file imports a library the detector would recognize."""
    try:
        source = fixture_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return library in source


def _check_vacuous_pass(rule_dir: Path, rule: Rule) -> bool:
    """Return True if any pass fixture is vacuous (library gate not satisfied)."""
    if rule.requires_library is None:
        return False
    for path in rule_dir.glob("pass_*.py"):
        if not _has_library_import(path, rule.requires_library):
            return True
    return False


def _inspect_rule_dir(pack_name: str, rule_id: str, rule: Rule) -> RuleCoverage:
    rule_dir = FIXTURES_ROOT / pack_name / rule_id
    if not rule_dir.exists():
        return RuleCoverage(rule_id, False, 0, 0, False, False)

    expected_path = rule_dir / "expected.json"
    has_expected = expected_path.exists()
    return RuleCoverage(
        rule_id=rule_id,
        has_dir=True,
        fail_count=_count_fixtures(rule_dir, "fail_"),
        pass_count=_count_fixtures(rule_dir, "pass_"),
        has_expected_json=has_expected,
        expected_json_valid=has_expected and _validate_expected_json(expected_path, rule_id),
        vacuous_pass=_check_vacuous_pass(rule_dir, rule),
    )


def collect_coverage() -> list[RuleCoverage]:
    seen: set[str] = set()
    coverage: list[RuleCoverage] = []
    for pack_name, rules in _PACK_RULES:
        for rule in rules:
            if rule.code in seen:
                continue
            seen.add(rule.code)
            coverage.append(_inspect_rule_dir(pack_name, rule.code, rule))
    return sorted(coverage, key=lambda c: c.rule_id)


def _expected_state(c: RuleCoverage) -> str:
    if c.expected_json_valid:
        return "valid"
    return "invalid" if c.has_expected_json else "absent"


def _format_row(c: RuleCoverage) -> str:
    return (
        f"{c.rule_id:{_COL_RULE}} {c.status:{_COL_STATUS}} "
        f"{c.fail_count:{_COL_COUNT}} {c.pass_count:{_COL_COUNT}} "
        f"{_expected_state(c):{_COL_EXPECTED}}"
    )


def _summary_lines(coverage: list[RuleCoverage]) -> list[str]:
    total = len(coverage)
    complete = sum(1 for c in coverage if c.is_complete)
    partial = sum(1 for c in coverage if c.status == "PARTIAL")
    missing = sum(1 for c in coverage if c.status == "MISSING")
    return [
        "Gaudi Fixture Corpus Coverage",
        "=" * 60,
        f"Total rules : {total}",
        f"Complete    : {complete}",
        f"Partial     : {partial}",
        f"Missing     : {missing}",
        "",
    ]


def render_report(coverage: list[RuleCoverage]) -> str:
    header = (
        f"{'Rule ID':{_COL_RULE}} {'Status':{_COL_STATUS}} "
        f"{'Fail':{_COL_COUNT}} {'Pass':{_COL_COUNT}} {'expected.json':{_COL_EXPECTED}}"
    )
    lines = _summary_lines(coverage) + [header, "-" * len(header)]
    lines.extend(_format_row(c) for c in coverage)
    return "\n".join(lines)


def _render_json(coverage: list[RuleCoverage]) -> str:
    return json.dumps(
        [
            {
                "rule_id": c.rule_id,
                "status": c.status,
                "fail_count": c.fail_count,
                "pass_count": c.pass_count,
                "expected_json_valid": c.expected_json_valid,
            }
            for c in coverage
        ],
        indent=2,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report Gaudi rule fixture coverage.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any rule lacks complete fixture coverage.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of the human-readable table.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    coverage = collect_coverage()
    print(_render_json(coverage) if args.json else render_report(coverage))
    if args.strict and any(not c.is_complete for c in coverage):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
