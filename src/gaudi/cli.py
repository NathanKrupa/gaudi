"""
Gaudí CLI — the `gaudi` command.

Usage:
    gaudi check .
    gaudi check . --pack python
    gaudi check . --format json
    gaudi check . --severity error --exit-code
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.text import Text

from gaudi.config import get_rule_overrides, get_school, load_config
from gaudi.core import Severity
from gaudi.engine import Engine
from gaudi.formats import format_github, format_markdown_report

console = Console()


@click.group()
@click.version_option(package_name="gaudi-linter")
def main():
    """Gaudí — Not just structurally sound. Beautiful."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--pack", "-p", multiple=True, help="Specific language pack(s) to use.")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "github"]),
    default="text",
    help="Output format. 'github' emits GitHub Actions workflow commands.",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["error", "warn", "info"]),
    default="info",
    help="Minimum severity to report.",
)
@click.option(
    "--exit-code/--no-exit-code",
    default=False,
    help="Exit with non-zero code if findings exist.",
)
def check(
    path: str,
    pack: tuple[str, ...],
    output_format: str,
    severity: str,
    exit_code: bool,
):
    """Check a project or file for architectural issues."""
    project_path = Path(path).resolve()

    # Load config from gaudi.toml, then let CLI flags override
    config = load_config(project_path)
    min_severity = Severity(severity or config.get("severity", "info"))

    # Initialize engine and discover packs
    engine = Engine()
    engine.discover_packs()

    # CLI --pack flags override config; config packs override auto-detect
    pack_names = list(pack) if pack else (config["packs"] or None)

    if pack_names:
        missing = [p for p in pack_names if p not in engine.packs]
        if missing:
            console.print(f"[red]Unknown pack(s): {', '.join(missing)}[/red]")
            console.print(f"Available packs: {', '.join(engine.packs.keys()) or 'none installed'}")
            sys.exit(1)

    # Run checks
    school = get_school(config)
    rule_overrides = get_rule_overrides(config)
    findings = engine.check(
        project_path,
        pack_names=pack_names,
        min_severity=min_severity,
        school=school,
        rule_overrides=rule_overrides,
    )

    # Output results
    if output_format == "json":
        from gaudi import __version__

        output = {
            "version": __version__,
            "path": str(project_path),
            "findings": [f.to_dict() for f in findings],
            "summary": engine.format_summary(findings),
        }
        click.echo(json.dumps(output, indent=2))
    elif output_format == "github":
        click.echo(format_github(findings, project_path=project_path))
    else:
        if not findings:
            console.print()
            console.print("[green]No architectural issues found. Structurally sound.[/green]")
            console.print()
        else:
            console.print()
            for finding in findings:
                style = finding.severity.style
                label = finding.severity.label

                # Code and severity
                header = Text()
                header.append(finding.code, style="bold")
                header.append(" [", style="dim")
                header.append(label, style=style)
                header.append("]", style="dim")

                # Philosophy scope (only for scoped rules)
                if finding.scope_label:
                    header.append(f" ({finding.scope_label})", style="magenta")

                # Location
                if finding.file:
                    header.append(f" {finding.file}", style="cyan")
                    if finding.line:
                        header.append(f":{finding.line}", style="cyan")

                # Message
                header.append(f" - {finding.message}")

                console.print(header)

                # Recommendation
                if finding.recommendation:
                    console.print(f"  [dim]-> {finding.recommendation}[/dim]")

                console.print()

            console.print(f"[dim]{engine.format_summary(findings)}[/dim]")
            console.print()

    # Exit code
    if exit_code and findings:
        has_errors = any(f.severity == Severity.ERROR for f in findings)
        sys.exit(1 if has_errors else 0)


@main.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--pack", "-p", multiple=True, help="Specific language pack(s) to use.")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write the report to this file instead of stdout.",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["error", "warn", "info"]),
    default="info",
    help="Minimum severity to include in the report.",
)
@click.option(
    "--snippet-context",
    type=int,
    default=2,
    help="Lines of context to show above/below each finding's line.",
)
def report(
    path: str,
    pack: tuple[str, ...],
    output: str | None,
    severity: str,
    snippet_context: int,
):
    """Generate a Markdown findings report for developer/LLM collaboration.

    The report groups findings by file, embeds a code snippet around each
    finding, and includes a pre-written discussion prompt the developer can
    paste into a conversation with an LLM. It is intentionally not an
    autofix — Gaudi's rules are judgment calls, and the report is the
    opening move in a conversation, not a patch.
    """
    project_path = Path(path).resolve()

    config = load_config(project_path)
    min_severity = Severity(severity or config.get("severity", "info"))

    engine = Engine()
    engine.discover_packs()

    pack_names = list(pack) if pack else (config["packs"] or None)
    if pack_names:
        missing = [p for p in pack_names if p not in engine.packs]
        if missing:
            console.print(f"[red]Unknown pack(s): {', '.join(missing)}[/red]")
            console.print(f"Available packs: {', '.join(engine.packs.keys()) or 'none installed'}")
            sys.exit(1)

    school = get_school(config)
    rule_overrides = get_rule_overrides(config)
    findings = engine.check(
        project_path,
        pack_names=pack_names,
        min_severity=min_severity,
        school=school,
        rule_overrides=rule_overrides,
    )
    markdown = format_markdown_report(findings, project_path, snippet_context=snippet_context)

    if output:
        Path(output).write_text(markdown, encoding="utf-8")
        console.print(f"[green]Wrote report to {output}[/green]")
    else:
        click.echo(markdown)


@main.command(name="list-packs")
def list_packs():
    """List available language packs."""
    engine = Engine()
    engine.discover_packs()

    if not engine.packs:
        console.print("[yellow]No language packs installed.[/yellow]")
        console.print("Install the Python pack: pip install gaudi")
        return

    console.print()
    console.print("[bold]Installed language packs:[/bold]")
    console.print()
    for name, pack in engine.packs.items():
        console.print(f"  [cyan]{name}[/cyan] — {pack.description}")
        console.print(f"    Extensions: {', '.join(pack.extensions)}")
        console.print(f"    Rules: {len(pack.rules)}")
        console.print()


@main.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
def philosophy(path: str, output_format: str):
    """Infer the architectural philosophy of a project.

    Analyzes dependencies, project structure, and code patterns to
    recommend which philosophy school best matches the project. Use
    this to decide what to put in [philosophy].school in gaudi.toml.
    """
    from gaudi.philosophy import infer_philosophy

    project_path = Path(path).resolve()
    result = infer_philosophy(project_path)

    if output_format == "json":
        import json as json_mod

        output = {
            "path": str(project_path),
            "recommended": result.recommended,
            "scores": result.scores,
            "signals": [
                {"school": s.school, "reason": s.reason, "weight": s.weight} for s in result.signals
            ],
        }
        click.echo(json_mod.dumps(output, indent=2))
    else:
        console.print()
        if not result.signals:
            console.print("[yellow]No strong signals detected.[/yellow]")
            console.print("Default school: [bold]classical[/bold]")
            console.print()
            return

        console.print("[bold]Philosophy inference[/bold]")
        console.print()

        # Show signals grouped by school
        for school, score in result.scores.items():
            console.print(f"  [cyan]{school}[/cyan] (score: {score})")
            school_signals = [s for s in result.signals if s.school == school]
            for s in school_signals:
                console.print(f"    — {s.reason}")
            console.print()

        recommended = result.recommended
        console.print(f"[bold green]Recommended:[/bold green] {recommended}")
        console.print()
        console.print(
            f"  [dim]echo '[philosophy]\\nschool = \"{recommended}\"' >> gaudi.toml[/dim]"
        )
        console.print()


@main.command(name="cheat-sheet")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write the cheat-sheet to this file instead of stdout.",
)
@click.option(
    "--check",
    is_flag=True,
    default=False,
    help="Exit 1 if the file at -o differs from generated output.",
)
def cheat_sheet(output: str | None, check: bool):
    """Generate a rule cheat-sheet from the live registry.

    Renders one line per rule, grouped by severity, suitable for
    @-reference from CLAUDE.md. Use --check in CI to guard against
    drift between the committed artifact and the rule catalog.
    """
    import difflib

    from gaudi.services.cheat_sheet import render_cheat_sheet

    engine = Engine()
    engine.discover_packs()

    all_rules = []
    for pack in engine.packs.values():
        all_rules.extend(pack.rules)

    rendered = render_cheat_sheet(all_rules)

    if check:
        if not output:
            console.print("[red]--check requires -o to specify the file to verify.[/red]")
            sys.exit(1)
        target = Path(output)
        if not target.exists():
            console.print(f"[red]{output} does not exist. Generate it first:[/red]")
            console.print(f"  gaudi cheat-sheet -o {output}")
            sys.exit(1)
        existing = target.read_text(encoding="utf-8")
        if existing == rendered:
            console.print(f"[green]{output} is up to date.[/green]")
            return
        diff = difflib.unified_diff(
            existing.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=output,
            tofile="generated",
        )
        console.print(f"[red]{output} is out of date.[/red]")
        console.print()
        console.print("The rule registry has changed since this file was last regenerated.")
        console.print("To fix:")
        console.print()
        console.print(f"    gaudi cheat-sheet -o {output}")
        console.print(f"    git add {output}")
        console.print("    git commit")
        console.print()
        console.print("Diff:")
        for line in diff:
            click.echo(line, nl=False)
        sys.exit(1)

    if output:
        Path(output).write_text(rendered, encoding="utf-8")
        console.print(f"[green]Wrote cheat-sheet to {output}[/green]")
    else:
        click.echo(rendered)


if __name__ == "__main__":
    main()
