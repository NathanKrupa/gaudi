"""Tests for Newman service boundary rules (SVC-001 through SVC-003)."""

from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestServiceRules:
    @staticmethod
    def _findings_for(fixture_name, code):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_svc_001_hardcoded_service_url(self):
        hits = self._findings_for("svc_hardcoded_url.py", "SVC-001")
        assert len(hits) == 2
        urls = {f.context.get("url") for f in hits}
        assert any("localhost" in u for u in urls)
        assert any("127.0.0.1" in u for u in urls)

    def test_svc_002_chatty_integration(self):
        hits = self._findings_for("svc_chatty_integration.py", "SVC-002")
        assert len(hits) == 1
        assert hits[0].context.get("function") == "sync_user_profile"
        assert hits[0].context.get("count") == 4

    def test_svc_003_no_api_versioning(self):
        hits = self._findings_for("svc_no_api_versioning.py", "SVC-003")
        assert len(hits) == 2  # /users and /orders, not /v1/products or /health
