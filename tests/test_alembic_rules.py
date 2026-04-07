# ABOUTME: Tests for alembic library rules (ALM-ARCH-001, ALM-OPS-001).
# ABOUTME: Covers migration downgrade detection and branch divergence with positive/negative cases.
"""Tests for alembic library rules."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack
from gaudi.packs.python.parser import parse_project

_PYPROJECT_MINIMAL = '[project]\nname="t"\n'
_PYPROJECT_ALEMBIC = '[project]\nname="t"\ndependencies = ["alembic"]\n'
_PYPROJECT_TOML = "pyproject.toml"
_LOCK_FILE = "requirements-lock.txt"
_LIBRARY = "alembic"
_CODE_ARCH = "ALM-ARCH-001"
_CODE_OPS = "ALM-OPS-001"


def _findings_for(files: dict[str, str], code: str) -> list:
    """Create a temp project with alembic dependency, run pack, filter by rule code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / _PYPROJECT_TOML).write_text(_PYPROJECT_ALEMBIC)
        (root / _LOCK_FILE).write_text("")
        for name, content in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        pack = PythonPack()
        findings = pack.check(root)
        return [f for f in findings if f.code == code]


# -- ALM-ARCH-001: MigrationNoDowngrade --


_MIGRATION_NO_DOWNGRADE = """\
revision = "abc123"
down_revision = "def456"

def upgrade():
    pass

def downgrade():
    pass
"""

_MIGRATION_MISSING_DOWNGRADE = """\
revision = "abc123"
down_revision = "def456"

def upgrade():
    op.add_column("users", sa.Column("email", sa.String()))
"""

_MIGRATION_EMPTY_ELLIPSIS = """\
revision = "abc123"
down_revision = "def456"

def upgrade():
    op.add_column("users", sa.Column("email", sa.String()))

def downgrade():
    ...
"""

_MIGRATION_WITH_DOWNGRADE = """\
revision = "abc123"
down_revision = "def456"

def upgrade():
    op.add_column("users", sa.Column("email", sa.String()))

def downgrade():
    op.drop_column("users", "email")
"""


class TestMigrationNoDowngrade:
    """ALM-ARCH-001: Migration file without a working downgrade function."""

    def test_missing_downgrade_function(self):
        hits = _findings_for({"migration.py": _MIGRATION_MISSING_DOWNGRADE}, _CODE_ARCH)
        assert len(hits) == 1

    def test_empty_downgrade_pass(self):
        hits = _findings_for({"migration.py": _MIGRATION_NO_DOWNGRADE}, _CODE_ARCH)
        assert len(hits) == 1

    def test_empty_downgrade_ellipsis(self):
        hits = _findings_for({"migration.py": _MIGRATION_EMPTY_ELLIPSIS}, _CODE_ARCH)
        assert len(hits) == 1

    def test_real_downgrade_no_finding(self):
        hits = _findings_for({"migration.py": _MIGRATION_WITH_DOWNGRADE}, _CODE_ARCH)
        assert len(hits) == 0

    def test_non_migration_file_ignored(self):
        source = "x = 1\ndef upgrade():\n    pass\n"
        hits = _findings_for({"app.py": source}, _CODE_ARCH)
        assert len(hits) == 0


# -- ALM-OPS-001: MultipleHeads --


_MIGRATION_A = """\
revision = "aaa111"
down_revision = "root00"

def upgrade():
    op.add_column("users", sa.Column("email", sa.String()))

def downgrade():
    op.drop_column("users", "email")
"""

_MIGRATION_B = """\
revision = "bbb222"
down_revision = "root00"

def upgrade():
    op.add_column("users", sa.Column("name", sa.String()))

def downgrade():
    op.drop_column("users", "name")
"""

_MIGRATION_C = """\
revision = "ccc333"
down_revision = "aaa111"

def upgrade():
    op.add_column("users", sa.Column("age", sa.Integer()))

def downgrade():
    op.drop_column("users", "age")
"""


class TestMultipleHeads:
    """ALM-OPS-001: Multiple migrations sharing the same down_revision."""

    def test_branched_migrations(self):
        files = {
            "alembic/versions/a.py": _MIGRATION_A,
            "alembic/versions/b.py": _MIGRATION_B,
        }
        hits = _findings_for(files, _CODE_OPS)
        assert len(hits) == 1
        assert "root00" in hits[0].message

    def test_linear_chain_no_finding(self):
        files = {
            "alembic/versions/a.py": _MIGRATION_A,
            "alembic/versions/c.py": _MIGRATION_C,
        }
        hits = _findings_for(files, _CODE_OPS)
        assert len(hits) == 0

    def test_single_migration_no_finding(self):
        hits = _findings_for({"migration.py": _MIGRATION_A}, _CODE_OPS)
        assert len(hits) == 0


# -- Library activation --


class TestAlembicDetection:
    def test_rules_skipped_when_not_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / _PYPROJECT_TOML).write_text(_PYPROJECT_MINIMAL)
            (root / _LOCK_FILE).write_text("")
            (root / "app.py").write_text("def hello():\n    return 42\n")
            pack = PythonPack()
            findings = pack.check(root)
            alm_codes = [f.code for f in findings if f.code.startswith("ALM-")]
            assert alm_codes == [], f"ALM rules fired without library: {alm_codes}"

    def test_detect_from_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / _PYPROJECT_TOML).write_text(
                '[project]\nname = "myapp"\ndependencies = ["alembic>=1.0"]\n'
            )
            (root / "app.py").write_text("x = 1\n")
            ctx = parse_project(root)
            assert _LIBRARY in ctx.detected_libraries

    def test_detect_from_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / _PYPROJECT_TOML).write_text(_PYPROJECT_MINIMAL)
            (root / "app.py").write_text("from alembic import op\n")
            ctx = parse_project(root)
            assert _LIBRARY in ctx.detected_libraries
