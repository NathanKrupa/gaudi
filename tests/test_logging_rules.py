"""Tests for logging hygiene rules (LOG-001)."""

from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoggingRules:
    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_log_001_unstructured_logging(self):
        hits = self._findings_for("arch90_unstructured_logging.py", "LOG-001")
        assert len(hits) == 3
