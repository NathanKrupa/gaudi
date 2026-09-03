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

from gaudi.core import FileSkip, Finding, PackError, Severity

# GitHub Actions workflow command severity mapping.
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
_GITHUB_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARN: "warning",
    Severity.INFO: "notice",
}


COMPLETE_RUN_VERDICT = "No architectural issues found. Structurally sound."
INCOMPLETE_RUN_VERDICT = "No architectural issues found in the parts that were examined."
NOTHING_EXAMINED_VERDICT = "No language pack applies here, so nothing was examined."


def format_empty_verdict(
    skipped: list[FileSkip] | None = None,
    pack_errors: list[PackError] | None = None,
    examined: bool = True,
) -> str:
    """The one sentence a run with nothing to report is allowed to say about itself.

    Three renderers make this claim — ``check``'s text output, the ``summary``
    field of its JSON document, and the Markdown report — and a sentence
    written in three places is a sentence that gets fixed in two. It lives here
    once, and every renderer asks for it.

    "Structurally sound" is a claim about the whole project, so only a run that
    examined the whole project may make it. A skip or a pack error outranks
    "nothing applied": a pack that failed to load is the pack that *would* have
    applied, and telling that reader no language pack applies would send them
    to install what is already there.
    """
    if skipped or pack_errors:
        return INCOMPLETE_RUN_VERDICT
    if not examined:
        return NOTHING_EXAMINED_VERDICT
    return COMPLETE_RUN_VERDICT


def nothing_applied(
    pack_errors: list[PackError] | None = None,
    examined: bool = True,
) -> bool:
    """True when the run examined nothing *and* no failed pack explains why.

    A pack that failed to load is the pack that would have applied, so saying
    "no language pack applies" beside it is the same misdiagnosis as reporting
    a broken install as "none installed": it sends the reader to install what
    is already there. Every renderer asks this one predicate rather than
    testing ``examined`` on its own.
    """
    return not examined and not pack_errors


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


def format_github(
    findings: list[Finding],
    project_path: Path | None = None,
    skipped: list[FileSkip] | None = None,
    pack_errors: list[PackError] | None = None,
    examined: bool = True,
) -> str:
    """
    Render findings as GitHub Actions workflow commands.

    The output is one line per finding, in the form:
        ::error file=path,line=N,title=CODE::message

    File paths are emitted relative to ``project_path`` when provided so that
    GitHub can match them against files in the checked-out repo.

    Files the parser could not read are annotated too. A file with no
    annotation reads to every PR reviewer as a file that passed; a skipped
    file must say on the diff that it was never examined.

    A pack that failed to load is annotated at ``error`` level, not the
    ``warning`` a file skip gets. It names no file, so GitHub can only show it
    in the workflow summary rather than on a diff line — the least visible
    place an annotation can land, carrying the most damaging news on the run:
    every rule that pack owns went unasked, so no other annotation on the run
    can be read as exhaustive.
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

        title = f.code
        if f.scope_label:
            title += f" ({f.scope_label})"
        props.append(f"title={_escape_github_property(title)}")

        prop_str = ",".join(props)
        message = _escape_github_data(f.message)
        lines.append(f"::{level} {prop_str}::{message}")

    for skip in skipped or []:
        file_path = _escape_github_property(skip.file.replace("\\", "/"))
        title = _escape_github_property("Skipped")
        message = _escape_github_data(f"Gaudi could not parse this file: {skip.reason}")
        lines.append(f"::warning file={file_path},title={title}::{message}")

    for pack_error in pack_errors or []:
        title = _escape_github_property("Pack load failure")
        message = _escape_github_data(
            f"Gaudi could not load the pack '{pack_error.pack}': {pack_error.error}. "
            f"Every rule it owns went unasked."
        )
        lines.append(f"::error title={title}::{message}")

    if nothing_applied(pack_errors, examined):
        title = _escape_github_property("Nothing examined")
        where = f" {project_path}" if project_path is not None else " this path"
        message = _escape_github_data(
            f"No installed Gaudi pack applies to{where}. Nothing was examined, "
            f"so this run reports nothing about it."
        )
        lines.append(f"::error title={title}::{message}")

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


def _incomplete_run_block(
    skipped: list[FileSkip] | None,
    pack_errors: list[PackError] | None,
    examined: bool = True,
) -> list[str]:
    """Render what the run could not examine, or nothing at all when it examined everything.

    The briefing is the opening move in a conversation with an LLM, and an LLM
    reads an unqualified report as the whole truth about the project. What was
    never examined has to be on the page, above the findings, or the reader
    draws conclusions from a silence that means nothing.
    """
    if not skipped and not pack_errors and examined:
        return []

    out = ["## Incomplete run", "", "**This report is not exhaustive.**", ""]
    if nothing_applied(pack_errors, examined):
        out.append(
            "- **No language pack applies to this path** — nothing was examined, "
            "so this report describes nothing."
        )
    for pack_error in pack_errors or []:
        out.append(
            f"- **Pack `{pack_error.pack}` failed to load** — {pack_error.error}. "
            f"Every rule it owns went unasked."
        )
    for skip in skipped or []:
        out.append(f"- **File `{skip.file}` was not read** — {skip.reason}.")
    out.append("")
    return out


def format_markdown_report(
    findings: list[Finding],
    project_path: Path,
    snippet_context: int = 2,
    skipped: list[FileSkip] | None = None,
    pack_errors: list[PackError] | None = None,
    examined: bool = True,
) -> str:
    """
    Render findings as a Markdown report grouped by file.

    The report is intended to be read by both a developer and an LLM. Each
    finding gets a code snippet with surrounding context and a pre-written
    discussion prompt the developer can paste into an LLM conversation.

    Files that could not be read and packs that could not be loaded are named
    at the top. "Structurally sound" is claimed only over a run that examined
    everything it was pointed at.
    """
    project_path = project_path.resolve()
    out: list[str] = []
    out.append("# Gaudi findings report")
    out.append("")
    out.append(f"Project: `{project_path}`")
    out.append("")

    incomplete = _incomplete_run_block(skipped, pack_errors, examined)
    out.extend(incomplete)

    if not findings:
        out.append(format_empty_verdict(skipped, pack_errors, examined))
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

        scope_tag = f" ({f.scope_label})" if f.scope_label else ""
        out.append(f"### {f.code}{scope_tag} — {f.severity.label}")
        out.append("")
        out.append(f"- **Category:** {f.category.value}")
        if f.scope_label:
            out.append(f"- **Schools:** {f.scope_label}")
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
