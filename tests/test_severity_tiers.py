# ABOUTME: Style-tier rules sit at info; rules needing project context sit out single-file runs.
# ABOUTME: Both make a per-file `--severity warn` gate report on structure rather than idiom.

from __future__ import annotations

from pathlib import Path

import pytest

from gaudi.core import Severity
from gaudi.engine import Engine
from gaudi.packs.python.pack import PythonPack
from gaudi.packs.python.rules import ALL_RULES

# Rules whose findings are idiom, not debt. #256 measured them as 58% and 21%
# of aigranthelper's warnings — Django field names in admin/model definitions
# and the explicit parameter threading the estate's own architecture doctrine
# prescribes. They stay in the catalog and stay reportable; they stop
# outranking structural findings.
STYLE_TIER = ("STRUCT-021", "CPLX-002", "SMELL-025")

# Rules that answer a question about the whole project. Pointed at one file
# they cannot see the evidence that would clear them, so they fire on every
# invocation — which is why aigranthelper disabled both repo-wide.
PROJECT_CONTEXT_RULES = ("STAB-011", "SVC-006")


def _rule(code: str):
    return next(r for r in ALL_RULES if r.code == code)


class TestStyleTier:
    @pytest.mark.parametrize("code", STYLE_TIER)
    def test_style_rule_is_info(self, code: str):
        assert _rule(code).severity is Severity.INFO

    @pytest.mark.parametrize("code", STYLE_TIER)
    def test_severity_warn_excludes_the_style_tier(self, code: str, tmp_path: Path):
        """The demotion is only worth something if `--severity warn` acts on it."""
        assert _rule(code).severity.priority > Severity.WARN.priority


class TestProjectContextRules:
    @pytest.mark.parametrize("code", PROJECT_CONTEXT_RULES)
    def test_rule_declares_it_needs_the_project(self, code: str):
        assert _rule(code).requires_project_context is True

    def test_most_rules_do_not_declare_it(self):
        """The default must stay False, or a single-file run reports nothing."""
        declaring = [r.code for r in ALL_RULES if r.requires_project_context]
        assert set(declaring) == set(PROJECT_CONTEXT_RULES)

    def test_svc_006_fires_on_the_project_but_not_on_the_file_alone(self, tmp_path: Path):
        """SVC-006 wants a paired test file. One file can never contain one."""
        module = tmp_path / "client.py"
        module.write_text(
            "import requests\n\n\ndef fetch(url):\n    return requests.get(url)\n",
            encoding="utf-8",
        )
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\ndependencies = ["requests"]\n', encoding="utf-8"
        )

        pack = PythonPack()
        project_codes = {f.code for f in pack.check(tmp_path)}
        single_file_codes = {f.code for f in pack.check(module)}

        assert "SVC-006" in project_codes
        assert "SVC-006" not in single_file_codes

    def test_single_file_run_still_reports_ordinary_rules(self, tmp_path: Path):
        """The exclusion must be surgical: a single-file run is still a real run."""
        module = tmp_path / "client.py"
        module.write_text(
            "import requests\n\n\ndef fetch(url):\n    return requests.get(url)\n",
            encoding="utf-8",
        )

        codes = {f.code for f in PythonPack().check(module)}

        assert codes, "a single-file invocation reported nothing at all"

    def test_engine_single_file_run_excludes_project_context_rules(self, tmp_path: Path):
        module = tmp_path / "client.py"
        module.write_text(
            "import requests\n\n\ndef fetch(url):\n    return requests.get(url)\n",
            encoding="utf-8",
        )

        engine = Engine()
        engine.discover_packs()
        codes = {f.code for f in engine.check(module)}

        assert "SVC-006" not in codes

    def test_context_marks_a_single_file_parse(self, tmp_path: Path):
        module = tmp_path / "client.py"
        module.write_text("x = 1\n", encoding="utf-8")

        pack = PythonPack()
        assert pack.parse(module).single_file is True
        assert pack.parse(tmp_path).single_file is False
