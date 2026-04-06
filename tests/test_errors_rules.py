"""Tests for error handling rules (ERR-001, ERR-003)."""

from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestErrorsRules:
    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_err_001_bare_except(self):
        hits = self._findings_for("arch90_bare_except.py", "ERR-001")
        assert len(hits) == 2

    def test_err_003_error_swallowing(self):
        hits = self._findings_for("arch90_error_swallowing.py", "ERR-003")
        assert len(hits) == 1
