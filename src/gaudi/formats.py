"""
ABOUTME: Output formatters for Gaudi findings — GitHub Actions annotations
ABOUTME: and Markdown reports designed for developer/LLM collaboration.

These formatters take a list of Findings and turn them into the artifacts the
developer actually consumes: workflow commands GitHub will surface inline on a
PR, or a Markdown report grouped by file that a developer can paste into a
conversation with an LLM.

Both formatters live in the middle layer — they take Findings (inner data
model) and emit text. The CLI (outer layer) decides which formatter to call.
"""

from __future__ import annotations

from pathlib import Path

from gaudi.core import Finding, Severity

# GitHub Actions workflow command severity mapping.
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
_GITHUB_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARN: "warning",
    Severity.INFO: "notice",
}


def _escape_github_data(value: str) -> str:
    """Escape a workflow-command message body."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_github_property(value: str) -> str:
    """Escape a workflow-command property value (title, file, etc.)."""
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def format_github(findings: list[Finding], project_path: Path | None = None) -> str:
    """
    Render findings as GitHub Actions workflow commands.

    The output is one line per finding, in the form:
        ::error file=path,line=N,title=CODE::message

    File paths are emitted relative to ``project_path`` when provided so that
    GitHub can match them against files in the checked-out repo.
    """
    lines: list[str] = []
    for f in findings:
        level = _GITHUB_LEVEL[f.severity]
        props: list[str] = []

        if f.file:
            file_path = f.file
            if project_path is not None:
                try:
                    file_path = str(Path(f.file).resolve().relative_to(project_path.resolve()))
                except ValueError:
                    file_path = f.file
            # GitHub annotations expect forward slashes regardless of host OS.
            file_path = file_path.replace("\\", "/")
            props.append(f"file={_escape_github_property(file_path)}")

        if f.line is not None:
            props.append(f"line={f.line}")

        props.append(f"title={_escape_github_property(f.code)}")

        prop_str = ",".join(props)
        message = _escape_github_data(f.message)
        lines.append(f"::{level} {prop_str}::{message}")

    return "\n".join(lines)


def _read_snippet(file_path: Path, line: int, context: int = 2) -> list[tuple[int, str]]:
    """Return ``(line_number, text)`` pairs around ``line`` for a code snippet."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    all_lines = text.splitlines()
    if not all_lines:
        return []
    start = max(1, line - context)
    end = min(len(all_lines), line + context)
    return [(n, all_lines[n - 1]) for n in range(start, end + 1)]


def _discussion_prompt(finding: Finding) -> str:
    """Compose a short conversational opener the developer can paste to an LLM."""
    location = ""
    if finding.file:
        location = f" in `{finding.file}`"
        if finding.line:
            location += f" at line {finding.line}"
    return (
        f"This file triggered {finding.code}{location}. Read the surrounding "
        f"code and propose a fix that fits the existing style. The rule says: "
        f"{finding.message} Recommendation: {finding.recommendation} "
        f"Do not apply the change yet — show me the diff first."
    )


def format_markdown_report(
    findings: list[Finding],
    project_path: Path,
    snippet_context: int = 2,
) -> str:
    """
    Render findings as a Markdown report grouped by file.

    The report is intended to be read by both a developer and an LLM. Each
    finding gets a code snippet with surrounding context and a pre-written
    discussion prompt the developer can paste into an LLM conversation.
    """
    project_path = project_path.resolve()
    out: list[str] = []
    out.append("# Gaudi findings report")
    out.append("")
    out.append(f"Project: `{project_path}`")
    out.append("")

    if not findings:
        out.append("No architectural issues found. Structurally sound.")
        out.append("")
        return "\n".join(out)

    errors = sum(1 for f in findings if f.severity == Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity == Severity.WARN)
    infos = sum(1 for f in findings if f.severity == Severity.INFO)
    files = sorted({f.file for f in findings if f.file})
    unfiled = [f for f in findings if not f.file]

    out.append(
        f"**Summary:** {len(findings)} finding(s) — "
        f"{errors} error(s), {warnings} warning(s), {infos} info — "
        f"across {len(files)} file(s)."
    )
    out.append("")
    out.append(
        "Each finding below is a starting point for a conversation with an LLM, "
        "not a mechanical autofix. Read the code, decide what (if anything) to "
        "do about it, then paste the discussion prompt into your assistant of "
        "choice."
    )
    out.append("")

    def _render_finding(f: Finding) -> None:
        location_link = ""
        if f.file:
            try:
                rel = Path(f.file).resolve().relative_to(project_path)
                rel_str = str(rel).replace("\\", "/")
            except ValueError:
                rel_str = f.file
            anchor = f"#L{f.line}" if f.line is not None else ""
            label = f"{rel_str}:{f.line}" if f.line is not None else rel_str
            location_link = f"[{label}]({rel_str}{anchor})"

        out.append(f"### {f.code} — {f.severity.label}")
        out.append("")
        out.append(f"- **Category:** {f.category.value}")
        if location_link:
            out.append(f"- **Location:** {location_link}")
        out.append(f"- **Message:** {f.message}")
        if f.recommendation:
            out.append(f"- **Recommendation:** {f.recommendation}")
        out.append("")

        if f.file and f.line is not None:
            snippet = _read_snippet(Path(f.file), f.line, context=snippet_context)
            if snippet:
                out.append("```python")
                for n, text in snippet:
                    marker = ">" if n == f.line else " "
                    out.append(f"{marker} {n:>4}  {text}")
                out.append("```")
                out.append("")

        out.append("**Discuss with LLM:**")
        out.append("")
        out.append("> " + _discussion_prompt(f))
        out.append("")

    for file in files:
        try:
            rel = Path(file).resolve().relative_to(project_path)
            rel_str = str(rel).replace("\\", "/")
        except ValueError:
            rel_str = file
        out.append(f"## `{rel_str}`")
        out.append("")
        file_findings = [f for f in findings if f.file == file]
        for f in file_findings:
            _render_finding(f)

    if unfiled:
        out.append("## Project-level findings")
        out.append("")
        for f in unfiled:
            _render_finding(f)

    return "\n".join(out)
