"""
ABOUTME: Tests for the GitHub annotations and Markdown report formatters
ABOUTME: that back `gaudi check --format github` and `gaudi report`.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from gaudi.cli import main
from gaudi.core import Category, Finding, Severity
from gaudi.formats import format_github, format_markdown_report


def _make_finding(
    code: str = "STAB-008",
    severity: Severity = Severity.WARN,
    file: str | None = None,
    line: int | None = None,
    message: str = "retry loop without exponential backoff",
) -> Finding:
    return Finding(
        code=code,
        severity=severity,
        category=Category.STABILITY,
        message=message,
        recommendation="Use exponential backoff with jitter.",
        file=file,
        line=line,
    )


class TestGithubFormat:
    def test_emits_workflow_command_per_finding(self, tmp_path: Path) -> None:
        src = tmp_path / "foo.py"
        src.write_text("x = 1\n")
        findings = [_make_finding(file=str(src), line=1)]

        out = format_github(findings, project_path=tmp_path)

        assert out.startswith("::warning ")
        assert "file=foo.py" in out
        assert "line=1" in out
        assert "title=STAB-008" in out
        assert out.endswith("retry loop without exponential backoff")

    def test_severity_mapping(self) -> None:
        findings = [
            _make_finding(severity=Severity.ERROR),
            _make_finding(severity=Severity.WARN),
            _make_finding(severity=Severity.INFO),
        ]
        out = format_github(findings).splitlines()
        assert out[0].startswith("::error ")
        assert out[1].startswith("::warning ")
        assert out[2].startswith("::notice ")

    def test_escapes_newlines_and_commas_in_message(self) -> None:
        f = _make_finding(message="bad,\nthing")
        out = format_github([f])
        assert "%0A" in out
        # Commas in the message body don't need escaping (only properties do).
        assert "bad," in out

    def test_uses_relative_path_when_inside_project(self, tmp_path: Path) -> None:
        nested = tmp_path / "src" / "x.py"
        nested.parent.mkdir()
        nested.write_text("y = 2\n")
        out = format_github([_make_finding(file=str(nested), line=1)], project_path=tmp_path)
        assert "file=src/x.py" in out

    def test_no_file_omits_file_property(self) -> None:
        out = format_github([_make_finding()])
        assert "file=" not in out
        assert "title=STAB-008" in out


class TestMarkdownReport:
    def test_empty_report(self, tmp_path: Path) -> None:
        out = format_markdown_report([], tmp_path)
        assert "# Gaudi findings report" in out
        assert "Structurally sound" in out

    def test_groups_by_file_with_snippet_and_prompt(self, tmp_path: Path) -> None:
        src = tmp_path / "service.py"
        src.write_text("a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n")
        findings = [_make_finding(file=str(src), line=3)]

        out = format_markdown_report(findings, tmp_path)

        assert "## `service.py`" in out
        assert "### STAB-008" in out
        assert "[service.py:3](service.py#L3)" in out
        # Snippet contains the offending line marked with '>' and the surrounding lines.
        assert "> " in out  # discussion prompt blockquote
        assert "```python" in out
        assert "c = 3" in out
        assert "Discuss with LLM" in out
        assert "STAB-008" in out

    def test_summary_counts(self, tmp_path: Path) -> None:
        src = tmp_path / "x.py"
        src.write_text("z = 1\n")
        findings = [
            _make_finding(severity=Severity.ERROR, file=str(src), line=1),
            _make_finding(severity=Severity.WARN, file=str(src), line=1),
            _make_finding(severity=Severity.INFO, file=str(src), line=1),
        ]
        out = format_markdown_report(findings, tmp_path)
        assert "3 finding(s)" in out
        assert "1 error(s)" in out
        assert "1 warning(s)" in out
        assert "1 info" in out

    def test_unfiled_findings_get_their_own_section(self, tmp_path: Path) -> None:
        out = format_markdown_report([_make_finding()], tmp_path)
        assert "Project-level findings" in out


class TestPhilosophyAttribution:
    def test_universal_finding_has_empty_scope_label(self) -> None:
        f = _make_finding()
        assert f.scope_label == ""

    def test_scoped_finding_has_sorted_scope_label(self) -> None:
        f = Finding(
            code="DOM-001",
            severity=Severity.WARN,
            category=Category.DOMAIN_MODEL,
            message="anemic",
            recommendation="fix",
            philosophy_scope=frozenset({"convention", "classical"}),
        )
        assert f.scope_label == "classical, convention"

    def test_to_dict_omits_scope_for_universal(self) -> None:
        f = _make_finding()
        assert "philosophy_scope" not in f.to_dict()

    def test_to_dict_includes_scope_for_scoped(self) -> None:
        f = Finding(
            code="DOM-001",
            severity=Severity.WARN,
            category=Category.DOMAIN_MODEL,
            message="anemic",
            recommendation="fix",
            philosophy_scope=frozenset({"classical", "convention"}),
        )
        d = f.to_dict()
        assert d["philosophy_scope"] == ["classical", "convention"]

    def test_format_human_includes_scope(self) -> None:
        f = Finding(
            code="DOM-001",
            severity=Severity.WARN,
            category=Category.DOMAIN_MODEL,
            message="anemic",
            recommendation="fix",
            philosophy_scope=frozenset({"classical"}),
        )
        assert "(classical)" in f.format_human()

    def test_format_human_omits_scope_for_universal(self) -> None:
        f = _make_finding()
        human = f.format_human()
        assert "(" not in human.split(" - ")[0]

    def test_github_title_includes_scope(self) -> None:
        f = Finding(
            code="DOM-001",
            severity=Severity.WARN,
            category=Category.DOMAIN_MODEL,
            message="anemic",
            recommendation="fix",
            philosophy_scope=frozenset({"classical"}),
        )
        out = format_github([f])
        assert "title=DOM-001 (classical)" in out

    def test_markdown_heading_includes_scope(self, tmp_path: Path) -> None:
        src = tmp_path / "m.py"
        src.write_text("x = 1\n")
        f = Finding(
            code="DOM-001",
            severity=Severity.WARN,
            category=Category.DOMAIN_MODEL,
            message="anemic",
            recommendation="fix",
            file=str(src),
            line=1,
            philosophy_scope=frozenset({"classical", "convention"}),
        )
        out = format_markdown_report([f], tmp_path)
        assert "### DOM-001 (classical, convention)" in out
        assert "**Schools:** classical, convention" in out


class TestCliWiring:
    def test_check_format_github_runs_on_clean_dir(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tmp_path), "--format", "github"])
        assert result.exit_code == 0
        # Clean dir → no findings → no output lines (but command must succeed).
        assert result.output.strip() == ""

    def test_report_writes_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        out_file = tmp_path / "report.md"
        result = runner.invoke(main, ["report", str(tmp_path), "--output", str(out_file)])
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Gaudi findings report" in content

    def test_report_stdout(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["report", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "# Gaudi findings report" in result.output
