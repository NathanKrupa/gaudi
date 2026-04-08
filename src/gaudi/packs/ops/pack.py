# ABOUTME: OpsPack -- discovers and runs rules against ops/build/deploy artifacts.
# ABOUTME: Currently handles Dockerfiles; CI configs and Makefiles will join later.
from __future__ import annotations

from pathlib import Path

from gaudi.core import Finding
from gaudi.pack import Pack
from gaudi.packs.ops.context import OpsContext
from gaudi.packs.ops.parser import parse_project
from gaudi.packs.ops.rules import ALL_RULES


class OpsPack(Pack):
    name = "ops"
    description = "Ops/build/deploy artifacts: Dockerfile, CI configs, Makefiles"
    extensions = ()
    filenames = ("Dockerfile",)

    def __init__(self) -> None:
        super().__init__()
        self._rules = list(ALL_RULES)

    def parse(self, path: Path) -> OpsContext:
        return parse_project(path)

    def check(self, path: Path) -> list[Finding]:
        context = self.parse(path)
        findings: list[Finding] = []
        for rule in self._rules:
            results = rule.check(context)
            if results:
                findings.extend(results)
        return sorted(findings, key=lambda f: (f.severity.priority, f.code))
