"""Tests for operational scaffolding rules (OPS-002 through OPS-005)."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack


class TestOpsRules:
    def test_ops_002_missing_precommit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-002"]
            assert len(hits) == 1

    def test_ops_003_missing_pr_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-003"]
            assert len(hits) == 1

    def test_ops_003_has_pr_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            gh = tmppath / ".github"
            gh.mkdir()
            (gh / "PULL_REQUEST_TEMPLATE.md").write_text("## Summary\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-003"]
            assert len(hits) == 0

    def test_ops_004_missing_codeowners(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-004"]
            assert len(hits) == 1

    def test_ops_005_missing_contrib_guide(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-005"]
            assert len(hits) == 1
