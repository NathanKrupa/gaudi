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

from gaudi.config import load_config
from gaudi.core import Severity
from gaudi.engine import Engine

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
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
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
    findings = engine.check(project_path, pack_names=pack_names, min_severity=min_severity)

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
    else:
        if not findings:
            console.print()
            console.print("[green]✓ No architectural issues found. Structurally sound.[/green]")
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


if __name__ == "__main__":
    main()
