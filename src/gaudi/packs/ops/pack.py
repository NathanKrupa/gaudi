# ABOUTME: OpsPack -- discovers and runs rules against ops/build/deploy artifacts.
# ABOUTME: Currently handles Dockerfiles; CI configs and Makefiles will join later.
from __future__ import annotations

from pathlib import Path

from gaudi.config import get_school, load_config
from gaudi.core import DEFAULT_SCHOOL, Finding
from gaudi.pack import Pack, rule_applies_to_school
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

    def check(self, path: Path, school: str | None = None) -> list[Finding]:
        if school is None:
            project_root = path if path.is_dir() else path.parent
            school = get_school(load_config(project_root))
        active_school = school or DEFAULT_SCHOOL
        context = self.parse(path)
        findings: list[Finding] = []
        for rule in self._rules:
            if not rule_applies_to_school(rule, active_school):
                continue
            results = rule.check(context)
            if results:
                findings.extend(results)
        return sorted(findings, key=lambda f: (f.severity.priority, f.code))
