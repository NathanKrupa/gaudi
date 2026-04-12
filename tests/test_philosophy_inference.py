# ABOUTME: Tests for the philosophy inference engine that recommends a school
# ABOUTME: based on project dependencies, structure, and code patterns.
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from gaudi.cli import main
from gaudi.philosophy import SchoolSignal, InferenceResult, infer_philosophy


class TestSchoolSignal:
    def test_signal_default_weight(self) -> None:
        s = SchoolSignal(school="classical", reason="test")
        assert s.weight == 1


class TestInferenceResult:
    def test_empty_result(self) -> None:
        r = InferenceResult()
        assert r.scores == {}
        assert r.recommended is None

    def test_scores_sum_weights(self) -> None:
        r = InferenceResult(
            signals=[
                SchoolSignal("classical", "a", weight=2),
                SchoolSignal("classical", "b", weight=1),
                SchoolSignal("pragmatic", "c", weight=3),
            ]
        )
        assert r.scores == {"pragmatic": 3, "classical": 3}

    def test_recommended_is_highest_score(self) -> None:
        r = InferenceResult(
            signals=[
                SchoolSignal("convention", "django", weight=5),
                SchoolSignal("classical", "sqlalchemy", weight=2),
            ]
        )
        assert r.recommended == "convention"


class TestDependencyDetection:
    def test_django_signals_convention(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("django>=4.0\n")
        result = infer_philosophy(tmp_path)
        schools = [s.school for s in result.signals]
        assert "convention" in schools

    def test_numpy_signals_data_oriented(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("numpy>=1.26\n")
        result = infer_philosophy(tmp_path)
        schools = [s.school for s in result.signals]
        assert "data-oriented" in schools

    def test_tenacity_signals_resilient(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\ndependencies = ["tenacity>=8.0"]\n'
        )
        result = infer_philosophy(tmp_path)
        schools = [s.school for s in result.signals]
        assert "resilient" in schools

    def test_no_deps_no_signals(self, tmp_path: Path) -> None:
        result = infer_philosophy(tmp_path)
        assert result.signals == []


class TestStructureDetection:
    def test_models_and_admin_signal_convention(self, tmp_path: Path) -> None:
        (tmp_path / "models.py").write_text("class M: pass\n")
        (tmp_path / "admin.py").write_text("class A: pass\n")
        result = infer_philosophy(tmp_path)
        convention_signals = [s for s in result.signals if s.school == "convention"]
        assert len(convention_signals) >= 1

    def test_shell_scripts_signal_unix(self, tmp_path: Path) -> None:
        (tmp_path / "deploy.sh").write_text("#!/bin/bash\n")
        result = infer_philosophy(tmp_path)
        unix_signals = [s for s in result.signals if s.school == "unix"]
        assert len(unix_signals) >= 1


class TestCliPhilosophyCommand:
    def test_text_output(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("django>=4.0\n")
        runner = CliRunner()
        result = runner.invoke(main, ["philosophy", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "convention" in result.output
        assert "Recommended" in result.output

    def test_json_output(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("django>=4.0\n")
        runner = CliRunner()
        result = runner.invoke(main, ["philosophy", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0, result.output
        import json

        data = json.loads(result.output)
        assert data["recommended"] == "convention"
        assert "convention" in data["scores"]

    def test_empty_project(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["philosophy", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "No strong signals" in result.output
