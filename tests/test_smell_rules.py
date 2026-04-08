"""Tests for SMELL rules — Martin Fowler's 24 code smells."""

from pathlib import Path

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

    def test_smell_014_lazy_element(self):
        hits = self._findings_for("smell_lazy_element.py", "SMELL-014")
        assert len(hits) == 2
        names = {f.context.get("class_name") for f in hits}
        assert "Calculator" not in names

    def test_smell_017_message_chains(self):
        hits = self._findings_for("smell_message_chains.py", "SMELL-017")
        assert len(hits) == 2

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

    def test_smell_007_divergent_change(self):
        hits = self._findings_for("smell_divergent_change.py", "SMELL-007")
        assert len(hits) == 1

    def test_smell_009_feature_envy(self):
        hits = self._findings_for("smell_feature_envy.py", "SMELL-009")
        assert len(hits) == 1
        assert "get_customer_summary" in hits[0].context.get("method", "")

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
