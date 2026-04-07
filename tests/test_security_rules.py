"""Tests for security fundamental rules (SEC-002 through SEC-005)."""

from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestSecurityRules:
    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_sec_002_raw_sql_injection(self):
        hits = self._findings_for("sec_raw_sql.py", "SEC-002")
        # 4 positives: f-string execute, .format() execute, concat execute, .raw() f-string
        assert len(hits) == 4

    def test_sec_003_hardcoded_credential(self):
        hits = self._findings_for("sec_hardcoded_credential.py", "SEC-003")
        # 4 positives: password, api_key, SECRET, auth_token
        assert len(hits) == 4

    def test_sec_004_eval_exec_usage(self):
        hits = self._findings_for("sec_eval_exec.py", "SEC-004")
        # 2 positives: eval, exec
        assert len(hits) == 2

    def test_sec_005_unsafe_deserialization(self):
        hits = self._findings_for("sec_unsafe_deserialization.py", "SEC-005")
        # 3 positives: pickle.load, pickle.loads, yaml.load (no SafeLoader)
        assert len(hits) == 3
