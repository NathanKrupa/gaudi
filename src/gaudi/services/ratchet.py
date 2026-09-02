# ABOUTME: The debt rule set and finding-counting used by CI ratchets.
# ABOUTME: Counting by rule code is gaudi data; repos should not rebuild it in scripts.
"""Ratchet support.

A ratchet asks one question: is this branch carrying less debt than the branch
it came from? That only works if "debt" names a fixed, defensible set of rules.
Counting *every* finding makes a ratchet payable by deleting an explanatory
comment or renaming a variable, and repos measurably did exactly that — ~50%
of ratchet-payment diffs across two estate repos were churn and ~19% were
outright harm.

:data:`RATCHET_RULE_CODES` is the answer to "which findings are debt": rules
whose findings are structural facts about the code, not idiom. Style-tier rules
(STRUCT-021, CPLX-002, SMELL-025) sit at ``info`` and are deliberately absent.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from gaudi.core import Finding

# The debt set. Each member reports a structural fact a reviewer would
# recognize as debt, and each is payable by a change that leaves the code
# better rather than merely different.
#
#   DEP-001   circular import between modules
#   DEP-004   unstable dependency (depends on something less stable than itself)
#   SMELL-003 long function
#   SMELL-007 divergent change (one module changing for many reasons)
#   STAB-006  unbounded resource use
RATCHET_RULE_CODES: tuple[str, ...] = (
    "DEP-001",
    "DEP-004",
    "SMELL-003",
    "SMELL-007",
    "STAB-006",
)


def count_by_code(
    findings: Iterable[Finding],
    codes: Sequence[str] | None = None,
) -> dict[str, int]:
    """Count findings per rule code.

    When ``codes`` is given the result has exactly those keys — including the
    ones that scored zero. A baseline whose key set shifts with the findings
    cannot be compared against a later run, and a missing key reads as "no
    findings" when it may mean "the rule did not run".
    """
    counts: dict[str, int] = {code: 0 for code in codes} if codes is not None else {}
    wanted = set(codes) if codes is not None else None
    for finding in findings:
        if wanted is not None and finding.code not in wanted:
            continue
        counts[finding.code] = counts.get(finding.code, 0) + 1
    return dict(sorted(counts.items()))
