"""Tests for Architecture 90 curriculum rules."""

from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestArch90Rules:
    """Each method tests one Architecture 90 rule against its fixture."""

    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    # -- Week 1: Project Shape --

    def test_struct_010_path_hacks(self):
        hits = self._findings_for("arch90_path_hacks.py", "STRUCT-010")
        assert len(hits) == 2

    def test_struct_011_missing_pyproject(self):
        """Tested at project level — fixture just marks the test."""
        # Create a temp dir without pyproject.toml to test
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "STRUCT-011"]
            assert len(hits) == 1

    def test_struct_012_no_entry_point(self):
        hits = self._findings_for("arch90_no_entry_point.py", "STRUCT-012")
        assert len(hits) == 1

    def test_struct_013_no_lock_file(self):
        """Tested at project level."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            (tmppath / "pyproject.toml").write_text("[project]\nname = 'test'\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "STRUCT-013"]
            assert len(hits) == 1

    # -- Week 2: Layers and Responsibilities --

    def test_arch_010_import_direction(self):
        hits = self._findings_for("arch90_import_direction.py", "ARCH-010")
        assert len(hits) >= 1

    def test_arch_011_connector_logic(self):
        hits = self._findings_for("arch90_connector_logic.py", "ARCH-011")
        assert len(hits) >= 1

    def test_arch_013_fat_script(self):
        hits = self._findings_for("arch90_fat_script.py", "ARCH-013")
        assert len(hits) == 1

    # -- Week 3: Configuration --

    def test_arch_020_env_leakage(self):
        hits = self._findings_for("arch90_env_leakage.py", "ARCH-020")
        assert len(hits) >= 2
        # Factory function should NOT be flagged
        methods = {f.context.get("method", f.context.get("function", "")) for f in hits}
        assert "create_service" not in methods

    def test_arch_022_scattered_config(self):
        import tempfile

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

    # -- Week 4: Data and Types --

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

    # -- Week 6: Error Handling --

    def test_err_001_bare_except(self):
        hits = self._findings_for("arch90_bare_except.py", "ERR-001")
        assert len(hits) == 2

    def test_err_003_error_swallowing(self):
        hits = self._findings_for("arch90_error_swallowing.py", "ERR-003")
        assert len(hits) == 1

    # -- Week 6: Logging --

    def test_log_001_unstructured_logging(self):
        hits = self._findings_for("arch90_unstructured_logging.py", "LOG-001")
        assert len(hits) == 3

    # -- Week 11: Ops --

    def test_ops_002_missing_precommit(self):
        """Tested at project level."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-002"]
            assert len(hits) == 1

    def test_ops_003_missing_pr_template(self):
        """Project without PR template triggers OPS-003."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-003"]
            assert len(hits) == 1

    def test_ops_003_has_pr_template(self):
        """Project with PR template does not trigger OPS-003."""
        import tempfile

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
        """Project without CODEOWNERS triggers OPS-004."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-004"]
            assert len(hits) == 1

    def test_ops_005_missing_contrib_guide(self):
        """Project without CONTRIBUTING.md triggers OPS-005."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "OPS-005"]
            assert len(hits) == 1
