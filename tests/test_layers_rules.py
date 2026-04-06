"""Tests for architectural layering rules (ARCH-010, ARCH-011, ARCH-013)."""

from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestLayersRules:
    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_arch_010_import_direction(self):
        hits = self._findings_for("arch90_import_direction.py", "ARCH-010")
        assert len(hits) >= 1

    def test_arch_011_connector_logic(self):
        hits = self._findings_for("arch90_connector_logic.py", "ARCH-011")
        assert len(hits) >= 1

    def test_arch_013_fat_script(self):
        hits = self._findings_for("arch90_fat_script.py", "ARCH-013")
        assert len(hits) == 1
