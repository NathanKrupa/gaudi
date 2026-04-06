"""Tests for library activation system."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack
from gaudi.packs.python.parser import parse_project


class TestLibraryDetection:
    def test_detect_from_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "myapp"\ndependencies = ["django>=4.2", "pandas"]\n'
            )
            (root / "app.py").write_text("x = 1\n")
            ctx = parse_project(root)
            assert "django" in ctx.detected_libraries
            assert "pandas" in ctx.detected_libraries
            assert "fastapi" not in ctx.detected_libraries

    def test_detect_from_requirements(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text('[project]\nname="t"\n')
            (root / "requirements.txt").write_text(
                "django==4.2\ndjangorestframework>=3.14\npandas\n"
            )
            (root / "app.py").write_text("x = 1\n")
            ctx = parse_project(root)
            assert "django" in ctx.detected_libraries
            assert "drf" in ctx.detected_libraries
            assert "pandas" in ctx.detected_libraries

    def test_detect_from_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text('[project]\nname="t"\n')
            (root / "app.py").write_text("import fastapi\nimport celery\n")
            ctx = parse_project(root)
            assert "fastapi" in ctx.detected_libraries
            assert "celery" in ctx.detected_libraries


class TestLibraryFiltering:
    def test_library_rules_skipped_when_not_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text('[project]\nname="t"\n')
            (root / "requirements-lock.txt").write_text("")
            (root / "app.py").write_text("def hello():\n    return 42\n")
            pack = PythonPack()
            findings = pack.check(root)
            lib_prefixes = [
                "DJ-",
                "FAPI-",
                "SA-",
                "FLASK-",
                "CELERY-",
                "PD-",
                "HTTP-",
                "PYD-",
                "TEST-",
                "DRF-",
            ]
            lib_codes = [
                f.code for f in findings if any(f.code.startswith(p) for p in lib_prefixes)
            ]
            assert lib_codes == [], f"Library rules fired without library: {lib_codes}"

    def test_general_rules_always_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text('[project]\nname="t"\n')
            (root / "requirements-lock.txt").write_text("")
            body = "\n".join(f"    x{i} = {i}" for i in range(30))
            (root / "app.py").write_text(f"def big():\n{body}\n")
            pack = PythonPack()
            findings = pack.check(root)
            smell_hits = [f for f in findings if f.code == "SMELL-003"]
            assert len(smell_hits) >= 1

    def test_library_rules_fire_when_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text('[project]\nname="t"\n')
            (root / "requirements-lock.txt").write_text("")
            source = (
                "import requests\n\ndef fetch():\n    return requests.get('http://example.com')\n"
            )
            (root / "app.py").write_text(source)
            pack = PythonPack()
            findings = pack.check(root)
            http_hits = [f for f in findings if f.code == "HTTP-SCALE-001"]
            assert len(http_hits) >= 1
