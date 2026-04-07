# ABOUTME: Tests for the glob-based file-exclusion plumbing in parse_project / PythonPack.
# ABOUTME: Covers _compile_glob translation, default excludes, and gaudi.toml-driven excludes.
from __future__ import annotations

from pathlib import Path

from gaudi.packs.python.pack import PythonPack
from gaudi.packs.python.parser import (
    DEFAULT_EXCLUDE_GLOBS,
    _compile_glob,
    _is_excluded,
    parse_project,
)


class TestCompileGlob:
    def test_double_star_slash_matches_zero_segments(self) -> None:
        rx = _compile_glob("**/venv/**")
        assert rx.match("venv/lib/foo.py"), "**/venv/** should match a top-level venv dir"

    def test_double_star_slash_matches_nested(self) -> None:
        rx = _compile_glob("**/venv/**")
        assert rx.match("app/venv/lib/foo.py"), "**/venv/** should match a nested venv dir"

    def test_double_star_respects_segment_boundaries(self) -> None:
        """``**/venv/**`` must NOT match a directory named ``myvenv`` -- the segment must align."""
        rx = _compile_glob("**/venv/**")
        assert not rx.match("myvenv/foo.py"), (
            "**/venv/** should not match dirs that merely contain 'venv'"
        )

    def test_trailing_double_star_matches_subtree(self) -> None:
        rx = _compile_glob("tests/fixtures/**")
        assert rx.match("tests/fixtures/python/CPLX-001/fail_x.py")
        assert rx.match("tests/fixtures/sample.py")

    def test_single_star_does_not_cross_slash(self) -> None:
        rx = _compile_glob("src/*.py")
        assert rx.match("src/foo.py")
        assert not rx.match("src/sub/foo.py"), "* should not cross directory boundaries"

    def test_question_mark_single_char(self) -> None:
        rx = _compile_glob("file?.py")
        assert rx.match("file1.py")
        assert not rx.match("file12.py")

    def test_dot_in_pattern_is_literal(self) -> None:
        rx = _compile_glob("**/.git/**")
        assert rx.match(".git/HEAD")
        assert rx.match("sub/.git/objects/abc")
        assert not rx.match("git/HEAD"), ". in the pattern should be literal, not regex-any"


class TestIsExcluded:
    def test_normalizes_windows_separators(self) -> None:
        compiled = [_compile_glob("**/venv/**")]
        assert _is_excluded("app\\venv\\lib\\foo.py", compiled), (
            "Windows backslashes should be normalized before matching"
        )

    def test_no_patterns_excludes_nothing(self) -> None:
        assert not _is_excluded("anything/at/all.py", [])


class TestParseProjectDefaults:
    """Built-in DEFAULT_EXCLUDE_GLOBS skip the obvious infrastructure dirs."""

    def test_venv_files_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "real.py").write_text("x = 1\n")
        (tmp_path / "venv" / "lib").mkdir(parents=True)
        (tmp_path / "venv" / "lib" / "site.py").write_text("y = 2\n")

        ctx = parse_project(tmp_path)

        rels = {f.relative_path.replace("\\", "/") for f in ctx.files}
        assert "src/real.py" in rels
        assert all("venv" not in r.split("/") for r in rels), (
            f"venv files leaked into context: {rels}"
        )

    def test_pycache_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "real.py").write_text("x = 1\n")
        (tmp_path / "src" / "__pycache__").mkdir()
        (tmp_path / "src" / "__pycache__" / "real.cpython-312.pyc.py").write_text("# fake")

        ctx = parse_project(tmp_path)

        rels = {f.relative_path.replace("\\", "/") for f in ctx.files}
        assert "src/real.py" in rels
        assert all("__pycache__" not in r for r in rels)

    def test_default_globs_are_a_tuple(self) -> None:
        """Defaults must be immutable -- a list could be mutated by callers and break isolation."""
        assert isinstance(DEFAULT_EXCLUDE_GLOBS, tuple)


class TestParseProjectExtraExcludes:
    def test_extra_excludes_layered_on_top_of_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "real.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "real.py").write_text("x = 1\n")
        (tmp_path / "vendor").mkdir()
        (tmp_path / "vendor" / "third_party.py").write_text("y = 2\n")
        # venv is a default exclude -- it should still be filtered out
        (tmp_path / "venv").mkdir()
        (tmp_path / "venv" / "site.py").write_text("z = 3\n")

        ctx = parse_project(tmp_path, extra_excludes=["vendor/**"])

        rels = {f.relative_path.replace("\\", "/") for f in ctx.files}
        assert rels == {"src/real.py"}

    def test_none_extra_excludes_uses_only_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("x = 1\n")
        ctx = parse_project(tmp_path, extra_excludes=None)
        rels = {f.relative_path.replace("\\", "/") for f in ctx.files}
        assert "app.py" in rels


class TestPythonPackReadsGaudiToml:
    """End-to-end: PythonPack.parse must read gaudi.toml from the project root."""

    def test_excludes_from_gaudi_toml_are_applied(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 't'\n")
        (tmp_path / "gaudi.toml").write_text("[gaudi]\nexclude = ['third_party/**']\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n")
        (tmp_path / "third_party").mkdir()
        (tmp_path / "third_party" / "lib.py").write_text("y = 2\n")

        pack = PythonPack()
        ctx = pack.parse(tmp_path)

        rels = {f.relative_path.replace("\\", "/") for f in ctx.files}
        assert "src/app.py" in rels
        assert "third_party/lib.py" not in rels

    def test_no_gaudi_toml_falls_back_to_defaults_only(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 't'\n")
        (tmp_path / "app.py").write_text("x = 1\n")

        pack = PythonPack()
        ctx = pack.parse(tmp_path)

        rels = {f.relative_path.replace("\\", "/") for f in ctx.files}
        assert "app.py" in rels
