"""
Tests for Gaudí's Python language pack.
"""

from pathlib import Path

import pytest

from gaudi.packs.python.pack import PythonPack
from gaudi.packs.python.parser import parse_project
from gaudi.engine import Engine


FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_MODELS = FIXTURES / "sample_models.py"


class TestParser:
    """Test the Python project parser."""

    def test_parse_sample_models(self):
        context = parse_project(SAMPLE_MODELS)
        assert context.framework == "django"
        assert len(context.models) == 9

    def test_model_names(self):
        context = parse_project(SAMPLE_MODELS)
        names = {m.name for m in context.models}
        expected = {
            "Donor", "Gift", "Campaign", "Fund",
            "Appeal", "Event", "Volunteer", "Communication", "Relationship",
        }
        assert names == expected

    def test_donor_columns(self):
        context = parse_project(SAMPLE_MODELS)
        donor = next(m for m in context.models if m.name == "Donor")
        assert len(donor.columns) >= 15
        assert donor.has_column("email")
        assert donor.has_column("first_name")

    def test_foreign_key_detection(self):
        context = parse_project(SAMPLE_MODELS)
        gift = next(m for m in context.models if m.name == "Gift")
        fks = gift.foreign_keys
        assert len(fks) >= 3
        fk_names = {fk.name for fk in fks}
        assert "donor" in fk_names

    def test_nullable_detection(self):
        context = parse_project(SAMPLE_MODELS)
        donor = next(m for m in context.models if m.name == "Donor")
        nullable = [c for c in donor.columns if c.nullable]
        assert len(nullable) >= 10


class TestRules:
    """Test individual rules against the sample models."""

    @pytest.fixture
    def findings(self):
        pack = PythonPack()
        return pack.check(SAMPLE_MODELS)

    def test_finds_issues(self, findings):
        """Should find multiple architectural issues in the sample."""
        assert len(findings) > 0

    def test_arch_001_no_tenant_isolation(self, findings):
        """Should flag missing tenant isolation."""
        arch_001 = [f for f in findings if f.code == "ARCH-001"]
        assert len(arch_001) == 1

    def test_arch_002_god_model(self, findings):
        """Should flag the Donor model as having too many fields."""
        arch_002 = [f for f in findings if f.code == "ARCH-002"]
        assert len(arch_002) >= 1
        assert any("Donor" in f.message for f in arch_002)

    def test_idx_001_missing_string_index(self, findings):
        """Should flag email and code fields without indexes."""
        idx_001 = [f for f in findings if f.code == "IDX-001"]
        assert len(idx_001) >= 1
        flagged_columns = {f.context.get("column") for f in idx_001}
        assert "email" in flagged_columns

    def test_schema_001_missing_timestamps(self, findings):
        """Should flag models without timestamp fields."""
        schema_001 = [f for f in findings if f.code == "SCHEMA-001"]
        assert len(schema_001) >= 1

    def test_schema_003_textfield_for_names(self, findings):
        """Should flag TextField used for name/title fields."""
        schema_003 = [f for f in findings if f.code == "SCHEMA-003"]
        assert len(schema_003) >= 1

    def test_struct_001_too_many_models(self, findings):
        """Should flag single file with 9 models."""
        struct_001 = [f for f in findings if f.code == "STRUCT-001"]
        assert len(struct_001) == 1

    def test_findings_sorted_by_severity(self, findings):
        """Findings should be sorted error → warn → info."""
        severities = [f.severity.priority for f in findings]
        assert severities == sorted(severities)


class TestEngine:
    """Test the main engine."""

    def test_engine_with_python_pack(self):
        engine = Engine()
        pack = PythonPack()
        engine.register_pack(pack)

        findings = engine.check(SAMPLE_MODELS)
        assert len(findings) > 0

    def test_summary_format(self):
        engine = Engine()
        pack = PythonPack()
        engine.register_pack(pack)

        findings = engine.check(SAMPLE_MODELS)
        summary = engine.format_summary(findings)
        assert "Found" in summary


class TestFindingOutput:
    """Test finding serialization."""

    def test_json_output(self):
        pack = PythonPack()
        findings = pack.check(SAMPLE_MODELS)
        for f in findings:
            d = f.to_dict()
            assert "code" in d
            assert "severity" in d
            assert "message" in d
            assert "recommendation" in d

    def test_human_output(self):
        pack = PythonPack()
        findings = pack.check(SAMPLE_MODELS)
        for f in findings:
            text = f.format_human()
            assert f.code in text
            assert "->" in text
