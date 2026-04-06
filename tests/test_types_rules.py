"""Tests for type annotation and literal hygiene rules (STRUCT-020, STRUCT-021)."""

from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestTypesRules:
    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_struct_020_missing_return_types(self):
        hits = self._findings_for("arch90_missing_return_types.py", "STRUCT-020")
        assert len(hits) == 2
        funcs = {f.context.get("function") for f in hits}
        assert "calculate_total" in funcs
        assert "get_user_name" in funcs
        assert "_private_helper" not in funcs
        assert "typed_function" not in funcs

    def test_struct_021_magic_strings(self):
        hits = self._findings_for("arch90_magic_strings.py", "STRUCT-021")
        assert len(hits) >= 1
