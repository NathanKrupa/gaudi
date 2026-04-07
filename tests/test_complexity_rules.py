"""Tests for Ousterhout complexity rules (CPLX-001 through CPLX-004)."""

import shutil
import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"

_PYPROJECT = "[project]\nname = 'test'\n"


def _findings_for_fixture(fixture_name: str, code: str):
    """Run pack on a temp dir containing only the given fixture, return matching findings.

    Test fixtures live under tests/fixtures/, but several rules skip paths
    containing 'tests' or 'fixtures'. So we copy the fixture into a clean
    temp project before running the pack.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "pyproject.toml").write_text(_PYPROJECT)
        (tmppath / "requirements-lock.txt").write_text("")
        target_name = fixture_name.replace("cplx_", "")
        shutil.copy(FIXTURES / fixture_name, tmppath / target_name)
        pack = PythonPack()
        findings = pack.check(tmppath)
        return [f for f in findings if f.code == code]


class TestComplexityRules:
    def test_cplx_001_shallow_module(self):
        hits = _findings_for_fixture("cplx_shallow_module.py", "CPLX-001")
        assert len(hits) == 1
        ctx = hits[0].context
        assert ctx["public_count"] == 6

    def test_cplx_001_deep_module_negative(self):
        hits = _findings_for_fixture("cplx_deep_module.py", "CPLX-001")
        assert hits == []

    def test_cplx_002_pass_through_variable(self):
        hits = _findings_for_fixture("cplx_pass_through.py", "CPLX-002")
        # `config` should be flagged as a pass-through (4 functions)
        params = {f.context.get("param") for f in hits}
        assert "config" in params

    def test_cplx_002_no_pass_through_negative(self):
        hits = _findings_for_fixture("cplx_no_pass_through.py", "CPLX-002")
        assert hits == []

    def test_cplx_003_information_leakage(self):
        hits = _findings_for_fixture("cplx_information_leakage.py", "CPLX-003")
        funcs = {f.context.get("func") for f in hits}
        # Public functions exposing _InternalRow
        assert "fetch_row" in funcs
        assert "store_row" in funcs
        # Public function with public type -- not flagged
        assert "safe_fetch" not in funcs
        # Private helper -- not flagged
        assert "_internal_helper" not in funcs

    def test_cplx_004_conjoined_methods(self):
        hits = _findings_for_fixture("cplx_conjoined_methods.py", "CPLX-004")
        assert len(hits) == 1
        ctx = hits[0].context
        assert ctx["cls"] == "Database"
        assert ctx["attr"] == "_conn"
        assert ctx["setter"] == "connect"
        assert ctx["checker"] == "query"
