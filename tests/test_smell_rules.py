"""Tests for SMELL rules — Martin Fowler's 24 code smells."""

from pathlib import Path

import pytest

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestSmellRules:
    """Each method tests one smell against its dedicated fixture."""

    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    # -- Tier 1: Easy (AST metrics) --

    def test_smell_001_mysterious_name(self):
        hits = self._findings_for("smell_mysterious_name.py", "SMELL-001")
        assert len(hits) >= 2
        assert all(f.severity.value == "info" for f in hits)

    def test_smell_003_long_function(self):
        hits = self._findings_for("smell_long_function.py", "SMELL-003")
        assert len(hits) == 1
        assert "process_order" in hits[0].context.get("function", "")

    def test_smell_004_long_parameter_list(self):
        hits = self._findings_for("smell_long_params.py", "SMELL-004")
        assert len(hits) == 2

    def test_smell_005_global_data(self):
        hits = self._findings_for("smell_global_data.py", "SMELL-005")
        assert len(hits) == 3
        flagged = {f.context.get("name") for f in hits}
        assert "REGISTRY" in flagged
        assert "_CACHE" in flagged
        assert "CONFIG" in flagged
        assert "MAX_RETRIES" not in flagged

    def test_smell_013_loops(self):
        hits = self._findings_for("smell_loops.py", "SMELL-013")
        assert len(hits) == 2

    def test_smell_014_lazy_element(self):
        hits = self._findings_for("smell_lazy_element.py", "SMELL-014")
        assert len(hits) == 2
        names = {f.context.get("class_name") for f in hits}
        assert "Calculator" not in names

    def test_smell_017_message_chains(self):
        hits = self._findings_for("smell_message_chains.py", "SMELL-017")
        assert len(hits) == 2

    def test_smell_020_large_class(self):
        hits = self._findings_for("smell_large_class.py", "SMELL-020")
        assert len(hits) == 1
        assert "GodObject" in hits[0].context.get("class_name", "")

    def test_smell_022_data_class(self):
        hits = self._findings_for("smell_data_class.py", "SMELL-022")
        assert len(hits) == 2
        names = {f.context.get("class_name") for f in hits}
        assert "Point" in names
        assert "ActiveRecord" not in names

    def test_smell_023_refused_bequest(self):
        hits = self._findings_for("smell_refused_bequest.py", "SMELL-023")
        assert len(hits) == 1
        assert "LimitedHandler" in hits[0].context.get("class_name", "")

    def test_smell_024_comments(self):
        hits = self._findings_for("smell_comments.py", "SMELL-024")
        assert len(hits) == 1

    # -- Tier 2: Moderate (intra-file cross-reference) --

    def test_smell_006_mutable_data(self):
        hits = self._findings_for("smell_mutable_data.py", "SMELL-006")
        assert len(hits) >= 2

    def test_smell_007_divergent_change(self):
        hits = self._findings_for("smell_divergent_change.py", "SMELL-007")
        assert len(hits) == 1

    def test_smell_009_feature_envy(self):
        hits = self._findings_for("smell_feature_envy.py", "SMELL-009")
        assert len(hits) == 1
        assert "get_customer_summary" in hits[0].context.get("method", "")

    def test_smell_010_data_clumps(self):
        hits = self._findings_for("smell_data_clumps.py", "SMELL-010")
        assert len(hits) >= 1

    def test_smell_011_primitive_obsession(self):
        hits = self._findings_for("smell_primitive_obsession.py", "SMELL-011")
        assert len(hits) >= 1

    def test_smell_012_repeated_switches(self):
        hits = self._findings_for("smell_repeated_switches.py", "SMELL-012")
        assert len(hits) >= 1

    def test_smell_015_speculative_generality(self):
        hits = self._findings_for("smell_speculative_generality.py", "SMELL-015")
        assert len(hits) >= 1

    def test_smell_016_temporary_field(self):
        hits = self._findings_for("smell_temporary_field.py", "SMELL-016")
        assert len(hits) == 1

    def test_smell_018_middle_man(self):
        hits = self._findings_for("smell_middle_man.py", "SMELL-018")
        assert len(hits) == 1
        assert "ServiceProxy" in hits[0].context.get("class_name", "")

    def test_smell_019_insider_trading(self):
        hits = self._findings_for("smell_insider_trading.py", "SMELL-019")
        assert len(hits) >= 1

    # -- Tier 3: Hard (structural comparison) --

    def test_smell_002_duplicated_code(self):
        hits = self._findings_for("smell_duplicated_code.py", "SMELL-002")
        assert len(hits) >= 1

    def test_smell_008_shotgun_surgery(self):
        hits = self._findings_for("smell_shotgun_surgery.py", "SMELL-008")
        assert len(hits) >= 1

    def test_smell_021_alt_interfaces(self):
        hits = self._findings_for("smell_alt_interfaces.py", "SMELL-021")
        assert len(hits) >= 1
