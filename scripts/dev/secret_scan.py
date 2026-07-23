#!/usr/bin/env python3
# ABOUTME: Tier-1 secret-scan gate — gitleaks (redacted) over staged/pushed diff; never prints a secret value.
# ABOUTME: Canonical (OverSteward shared/scripts/dev/); deployed byte-identical to every repo's scripts/dev/.
"""Continuous secret-scanning gate for the estate red-team process (OS#219 Tier 1).

Tier 0 (the one-time history excavation, OS#220) established the baseline; this
is the *ongoing* floor — it scans only what a commit/push actually adds, so it
stays fast and quiet. It runs ``gitleaks`` through its official docker image (no
host install, so the same byte-identical script works in every repo), always
with ``--redact`` so a found secret's **value never touches stdout, stderr, a
report file, or the agent transcript** — only its rule, file, and line, which is
what a developer needs to fix it. That redaction is the whole point: a
secret-scanner that prints the secret it found is itself a leak (credential
hygiene, the same law that blocks ``source .env``).

Modes:

``--staged`` (default; pre-commit use)
    Scan the staged index — blocks a secret before it is ever committed.

``--range A..B`` (pre-push / CI use)
    Scan the commits in a revision range — catches anything a local pre-commit
    was bypassed on.

A repo-local ``.gitleaksignore`` (fingerprints of the Tier-0 inert findings) is
read automatically by gitleaks, so baselined noise never trips the gate.

Fail-open vs fail-closed: if docker/gitleaks is unavailable the gate **warns and
skips** by default (local gates are primary, CI is the watchdog — matching the
estate's pre-launch posture). Set ``SECRET_SCAN_REQUIRED=1`` (CI does) to
**fail closed** instead, so the watchdog cannot be silently no-op'd.

Exit codes: ``0`` clean or skipped, ``1`` findings, ``2`` required-but-unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_IMAGE = "ghcr.io/gitleaks/gitleaks:v8.18.4"


class Finding:
    """One gitleaks hit, reduced to non-sensitive fields only (never the value)."""

    __slots__ = ("rule", "file", "line")

    def __init__(self, rule: str, file: str, line: int) -> None:
        self.rule = rule
        self.file = file
        self.line = line

    def render(self) -> str:
        return f"  {self.file}:{self.line}  [{self.rule}]"


def parse_report(report_json: str) -> list[Finding]:
    """Reduce a gitleaks JSON report to non-sensitive findings.

    Deliberately reads only ``RuleID`` / ``File`` / ``StartLine`` — never
    ``Secret`` or ``Match`` — so no value can escape even if ``--redact`` were
    ever dropped upstream.
    """
    if not report_json.strip():
        return []
    data = json.loads(report_json)
    findings: list[Finding] = []
    for row in data:
        findings.append(
            Finding(
                rule=str(row.get("RuleID", "unknown")),
                file=str(row.get("File", "?")),
                line=int(row.get("StartLine", 0) or 0),
            )
        )
    return findings


def docker_available() -> bool:
    """True when a docker CLI is present and its daemon answers."""
    if shutil.which("docker") is None:
        return False
    return (
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def build_gitleaks_cmd(
    repo: Path, out_report: Path, image: str, *, staged: bool, rev_range: str | None
) -> list[str]:
    """Assemble the docker gitleaks invocation for the requested mode.

    Always ``--redact`` and ``--exit-code=0`` (we derive the gate result from the
    report, not gitleaks' own exit, so a scan error is distinguishable from a
    clean scan).
    """
    sub = "protect" if staged else "detect"
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{repo}:/repo:ro",
        "-v",
        f"{out_report.parent}:/out",
        image,
        sub,
        "--source=/repo",
        "--redact",
        "--report-format=json",
        f"--report-path=/out/{out_report.name}",
        "--exit-code=0",
        "--log-level=error",
    ]
    if staged:
        cmd.append("--staged")
    elif rev_range:
        cmd.append(f"--log-opts={rev_range}")
    return cmd


def run_scan(
    repo: Path, image: str, *, staged: bool, rev_range: str | None
) -> list[Finding]:
    """Run gitleaks in a container and return the reduced findings."""
    with tempfile.TemporaryDirectory() as td:
        report = Path(td) / "report.json"
        cmd = build_gitleaks_cmd(
            repo, report, image, staged=staged, rev_range=rev_range
        )
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
        if not report.exists():
            # gitleaks writes no report only when it never ran — surface stderr
            # (which carries no secret; --redact governs the report, and errors
            # here are config/plumbing) and treat as a scan failure.
            msg = proc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"gitleaks produced no report: {msg or 'unknown error'}")
        return parse_report(report.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tier-1 secret-scan gate (redacted).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--staged", action="store_true", help="Scan the staged index (default; pre-commit)."
    )
    mode.add_argument(
        "--range", dest="rev_range", metavar="A..B", help="Scan a commit range (pre-push/CI)."
    )
    parser.add_argument("--repo", default=".", help="Repo root to scan (default: cwd).")
    parser.add_argument(
        "--image", default=os.environ.get("SECRET_SCAN_IMAGE", DEFAULT_IMAGE),
        help="gitleaks docker image.",
    )
    args = parser.parse_args(argv)
    staged = args.rev_range is None  # default mode is staged

    required = os.environ.get("SECRET_SCAN_REQUIRED") == "1"
    if not docker_available():
        if required:
            print("secret-scan: docker/gitleaks unavailable and SECRET_SCAN_REQUIRED=1 — failing closed.", file=sys.stderr)
            return 2
        print("secret-scan: docker/gitleaks unavailable — skipping (CI is the watchdog).", file=sys.stderr)
        return 0

    repo = Path(args.repo).resolve()
    try:
        findings = run_scan(repo, args.image, staged=staged, rev_range=args.rev_range)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"secret-scan: scan failed — {exc}", file=sys.stderr)
        return 2 if required else 0

    if findings:
        scope = "staged changes" if staged else f"range {args.rev_range}"
        print(f"secret-scan: {len(findings)} potential secret(s) in {scope}:", file=sys.stderr)
        for f in findings:
            print(f.render(), file=sys.stderr)
        print(
            "\nIf a hit is a false positive or an accepted/rotated value, add its gitleaks "
            "fingerprint to .gitleaksignore. Never commit a live secret.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
