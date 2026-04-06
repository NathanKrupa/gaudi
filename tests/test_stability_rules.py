"""Tests for Nygard stability rules (STAB-001 through STAB-007)."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"

_PYPROJECT = "[project]" + chr(10) + "name = 'test'" + chr(10)


class TestStabilityRules:

    @staticmethod
    def _findings_for(fixture_name, code):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    @staticmethod
    def _findings_from_source(source, code):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "pyproject.toml").write_text(_PYPROJECT)
            (tmppath / "requirements-lock.txt").write_text("")
            (tmppath / "app.py").write_text(source)
            pack = PythonPack()
            findings = pack.check(tmppath)
            return [f for f in findings if f.code == code]

    def test_stab_001_unbounded_result_set(self):
        hits = self._findings_for("stab_unbounded_result_set.py", "STAB-001")
        assert len(hits) >= 2
        methods = {f.context.get("method") for f in hits}
        assert "all" in methods
        assert "filter" in methods

    def test_stab_003_retry_without_backoff(self):
        hits = self._findings_for("stab_retry_without_backoff.py", "STAB-003")
        assert len(hits) >= 2

    def test_stab_004_unbounded_cache(self):
        hits = self._findings_for("stab_unbounded_cache.py", "STAB-004")
        assert len(hits) == 2

    def test_stab_005_blocking_in_async(self):
        hits = self._findings_for("stab_blocking_in_async.py", "STAB-005")
        assert len(hits) == 2
        functions = {f.context.get("function") for f in hits}
        assert "poll_status" in functions
        assert "fetch_data" in functions

    def test_stab_006_unmanaged_resource(self):
        hits = self._findings_for("stab_unmanaged_resource.py", "STAB-006")
        assert len(hits) == 3  # 2 bare open() + 1 bare Session()
        resources = {f.context.get("resource") for f in hits}
        assert "open" in resources
        assert "Session" in resources

    def test_stab_007_unbounded_thread_pool(self):
        hits = self._findings_for("stab_unbounded_thread_pool.py", "STAB-007")
        assert len(hits) == 1
