# ABOUTME: Reports which Python pack rules have / lack a fixture directory under tests/fixtures/python/.
# ABOUTME: Runs in warn-mode by default; pass --strict to fail when any rule is missing fixtures.
"""Fixture coverage reporter for the Gaudi rule corpus.

Walks every Rule registered in the Python pack and checks whether
``tests/fixtures/python/<RULE-ID>/`` exists with the minimum required
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

from gaudi.packs.python.rules import ALL_RULES

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "python"


@dataclass
class RuleCoverage:
    rule_id: str
    has_dir: bool
    fail_count: int
    pass_count: int
    has_expected_json: bool
    expected_json_valid: bool

    @property
    def is_complete(self) -> bool:
        return (
            self.has_dir
            and self.fail_count >= 1
            and self.pass_count >= 1
            and self.has_expected_json
            and self.expected_json_valid
        )

    @property
    def status(self) -> str:
        if self.is_complete:
            return "OK"
        if not self.has_dir:
            return "MISSING"
        return "PARTIAL"


def _inspect_rule_dir(rule_id: str) -> RuleCoverage:
    rule_dir = PYTHON_FIXTURES / rule_id
    if not rule_dir.exists():
        return RuleCoverage(
            rule_id=rule_id,
            has_dir=False,
            fail_count=0,
            pass_count=0,
            has_expected_json=False,
            expected_json_valid=False,
        )

    fail_files = sorted(rule_dir.glob("fail_*.py"))
    pass_files = sorted(rule_dir.glob("pass_*.py"))
    expected_path = rule_dir / "expected.json"
    has_expected = expected_path.exists()
    valid = False
    if has_expected:
        try:
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            valid = data.get("rule_id") == rule_id and "fixtures" in data
        except json.JSONDecodeError:
            valid = False

    return RuleCoverage(
        rule_id=rule_id,
        has_dir=True,
        fail_count=len(fail_files),
        pass_count=len(pass_files),
        has_expected_json=has_expected,
        expected_json_valid=valid,
    )


def collect_coverage() -> list[RuleCoverage]:
    seen: set[str] = set()
    coverage: list[RuleCoverage] = []
    for rule in ALL_RULES:
        if rule.code in seen:
            continue
        seen.add(rule.code)
        coverage.append(_inspect_rule_dir(rule.code))
    return sorted(coverage, key=lambda c: c.rule_id)


def render_report(coverage: list[RuleCoverage]) -> str:
    total = len(coverage)
    complete = sum(1 for c in coverage if c.is_complete)
    partial = sum(1 for c in coverage if c.status == "PARTIAL")
    missing = sum(1 for c in coverage if c.status == "MISSING")

    lines: list[str] = []
    lines.append("Gaudi Fixture Corpus Coverage")
    lines.append("=" * 60)
    lines.append(f"Total rules : {total}")
    lines.append(f"Complete    : {complete}")
    lines.append(f"Partial     : {partial}")
    lines.append(f"Missing     : {missing}")
    lines.append("")
    header = f"{'Rule ID':<14} {'Status':<8} {'Fail':>4} {'Pass':>4} {'expected.json':<14}"
    lines.append(header)
    lines.append("-" * len(header))
    for c in coverage:
        exp_state = (
            "valid" if c.expected_json_valid else ("invalid" if c.has_expected_json else "absent")
        )
        lines.append(
            f"{c.rule_id:<14} {c.status:<8} {c.fail_count:>4} {c.pass_count:>4} {exp_state:<14}"
        )
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
