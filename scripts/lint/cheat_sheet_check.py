#!/usr/bin/env python3
# ABOUTME: Pre-commit drift guard for docs/gaudi-rules.md, run against THIS checkout's src/.
# ABOUTME: Immune to PATH and PYTHONPATH; exits 2 (never 0) when it cannot import gaudi.

"""Checkout-correct wrapper for ``gaudi cheat-sheet --check``.

Why this wrapper exists (gaudi#266):
  The hook used to be ``entry: gaudi cheat-sheet --check -o docs/gaudi-rules.md``
  with ``language: system``, which resolves ``gaudi`` from ``PATH``. On a machine
  carrying a ``uv tool`` install (``~/.local/bin/gaudi``) that binary's shebang
  names *its own* interpreter, so the drift guard regenerated the cheat-sheet
  from whichever tree that installation holds — never the checkout being
  committed. In a worktree that reported drift which did not exist; in the other
  direction it passes while the committed artifact is stale.

How this is checkout-correct by construction:
  The repository root is derived from ``__file__`` — not from ``PATH``, the
  working directory, or ``PYTHONPATH``. ``<root>/src`` goes to ``sys.path[0]``,
  ahead of every ``PYTHONPATH`` entry and every site-packages install, so
  ``import gaudi`` can only resolve to this checkout. The working directory is
  anchored to that root as well, so the artifact resolves under this checkout
  however the hook was invoked, while the remediation commands the CLI prints
  stay short and copy-pasteable.

Interpreter resolution:
  Rendering the cheat-sheet needs gaudi's runtime dependencies (``click``,
  ``rich``), which a contributor's bare ``python3`` may not have. When this
  checkout has a ``.venv``, the script re-executes itself under that interpreter
  once — guarded by ``_REEXEC_ENV`` so it can never loop — and otherwise runs
  under whatever interpreter invoked it. If the import still fails, it exits
  **2** with the reason on stderr: "gaudi could not be imported" and "the
  cheat-sheet is up to date" must never exit the same.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Cheat-sheet artifact, relative to the repository root.
ARTIFACT = Path("docs") / "gaudi-rules.md"

#: Set on the re-executed child so a missing dependency cannot loop forever.
_REEXEC_ENV = "GAUDI_CHEAT_SHEET_REEXEC"


def repo_root() -> Path:
    """The checkout this script belongs to (``scripts/lint/`` → two levels up)."""
    return Path(__file__).resolve().parents[2]


def venv_interpreter(root: Path) -> Path | None:
    """This checkout's own venv interpreter, or ``None`` if it has no venv."""
    for relative in ("bin/python", "Scripts/python.exe"):
        candidate = root / ".venv" / relative
        if candidate.exists():
            return candidate
    return None


def reexec_target(root: Path, environ: dict[str, str], executable: str) -> Path | None:
    """The interpreter to re-exec into, or ``None`` to run under this one.

    ``None`` when the guard variable is already set (we *are* the child), when
    the checkout has no venv, and when the venv interpreter is already running.
    """
    if environ.get(_REEXEC_ENV):
        return None
    candidate = venv_interpreter(root)
    if candidate is None or candidate == Path(executable):
        return None
    return candidate


def reexec_into_own_venv(root: Path, argv: list[str]) -> None:
    """Re-run this script under the checkout's own interpreter, if it has one."""
    target = reexec_target(root, dict(os.environ), sys.executable)
    if target is None:
        return
    os.environ[_REEXEC_ENV] = "1"
    # Fixed argv: this checkout's own interpreter and this very script. No shell
    # and no caller-supplied program name, so B606's "process without a shell"
    # blacklist warning has nothing to bite on here.
    os.execv(str(target), [str(target), str(Path(__file__).resolve()), *argv])  # nosec B606


def report_unimportable(root: Path, exc: BaseException) -> None:
    """Say what could not be imported and that nothing was therefore checked."""
    sys.stderr.write(
        f"gaudi-cheat-sheet: COULD NOT LOOK — cannot import gaudi from {root / 'src'} "
        f"under {sys.executable}: {exc}\n"
        "  Nothing was checked; the cheat-sheet may be stale.\n"
        "  Install this checkout's dependencies: uv sync --extra dev\n"
    )


def main(argv: list[str]) -> int:
    root = repo_root()
    reexec_into_own_venv(root, argv)

    # STRUCT-010 deliberately exempts self-locating ``__main__`` bootstraps like
    # this one: the whole point of the hook is to find THIS checkout's package
    # ahead of any installed copy, which packaging alone cannot express.
    sys.path.insert(0, str(root / "src"))
    # Anchor the relative artifact path to this checkout, not the caller's cwd.
    os.chdir(root)

    try:
        from gaudi.cli import main as gaudi_cli
    # Broad on purpose: a stale interpreter raises SyntaxError, not ImportError,
    # on modern gaudi source. Every failure is reported and exits 2 — none is
    # swallowed. (Trailing prose after the codes would break gaudi's own noqa
    # parser, which splits the rest of the comment on commas.)
    except Exception as exc:  # noqa: BLE001, ERR-001
        report_unimportable(root, exc)
        return 2

    try:
        gaudi_cli.main(
            args=["cheat-sheet", "--check", "-o", str(ARTIFACT)],
            prog_name="gaudi",
            standalone_mode=True,
        )
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
