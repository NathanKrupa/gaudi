from __future__ import annotations

from pathlib import Path

from gaudi.config import get_school, load_config
from gaudi.core import DEFAULT_SCHOOL, Finding
from gaudi.pack import Pack, rule_applies_to_school
from gaudi.packs.python.context import PythonContext
from gaudi.packs.python.parser import parse_project
from gaudi.packs.python.rules import ALL_RULES


class PythonPack(Pack):
    name = "python"
    description = (
        "Full Python stack: Django, FastAPI, SQLAlchemy, Flask, "
        "Celery, Pandas, DRF, and 3.14 compat"
    )
    extensions = (".py",)

    def __init__(self) -> None:
        super().__init__()
        self._rules = list(ALL_RULES)

    def parse(self, path: Path) -> PythonContext:
        project_root = path if path.is_dir() else path.parent
        config = load_config(project_root)
        extra_excludes = list(config.get("exclude") or [])
        context = parse_project(path, extra_excludes=extra_excludes)
        context.school = get_school(config)
        return context

    def check(self, path: Path, school: str | None = None) -> list[Finding]:
        context = self.parse(path)
        active_school = school or context.school or DEFAULT_SCHOOL
        findings: list[Finding] = []
        for rule in self._rules:
            if rule.requires_library and rule.requires_library not in context.detected_libraries:
                continue
            if not rule_applies_to_school(rule, active_school):
                continue
            results = rule.check(context)
            if results:
                findings.extend(results)
        return sorted(findings, key=lambda f: (f.severity.priority, f.code))
