"""Tests for configuration hygiene rules (ARCH-020, ARCH-022)."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestConfigRules:
    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_arch_020_env_leakage(self):
        hits = self._findings_for("arch90_env_leakage.py", "ARCH-020")
        assert len(hits) >= 2
        methods = {f.context.get("method", f.context.get("function", "")) for f in hits}
        assert "create_service" not in methods

    def test_arch_022_scattered_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            for i in range(5):
                (tmppath / f"module_{i}.py").write_text(
                    f'import os\nval_{i} = os.getenv("KEY_{i}")\n'
                )
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "ARCH-022"]
            assert len(hits) >= 1
