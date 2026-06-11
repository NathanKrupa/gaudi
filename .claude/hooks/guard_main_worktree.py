#!/usr/bin/env python3
# ABOUTME: PreToolUse(Bash) guard — refuse branch checkout/switch in the primary worktree.
# ABOUTME: Canonical in OverSteward shared/scripts/dev/; deployed to <repo>/.claude/hooks/.
"""Block branch-mutating git in the primary worktree.

Parallel Claude sessions that share one working tree collide: a
``git checkout -b`` / ``git checkout <branch>`` in the shared main checkout
yanks another session's branch out from under it and strands its uncommitted
work. This hook refuses those commands when the session is anchored in the
*primary* worktree and points at ``scripts/dev/new-session.sh`` instead. Linked
worktrees (``.git/worktrees/<name>``) are exempt — that is where work belongs.

Allowed even in the main tree: file restores (``git checkout -- <path>`` /
``git restore``), ``git worktree add``, and anything prefixed with
``CLAUDE_ALLOW_MAIN_GIT=1`` — the conscious-override escape hatch (promotes,
one-off rebases). ``GS_ALLOW_MAIN_GIT=1`` is also honored as a back-compat
alias for grantspider, which shipped this guard first.

Decision logic is split into pure functions so it is unit-tested without git.
"""

import json
import os
import re
import subprocess  # list-form argv, no shell; cwd is the only input
import sys

# Env vars that wave the guard through. CLAUDE_ALLOW_MAIN_GIT is the standard;
# GS_ALLOW_MAIN_GIT is grantspider's original name, kept as an alias.
_OVERRIDE_VARS = ("CLAUDE_ALLOW_MAIN_GIT", "GS_ALLOW_MAIN_GIT")

# ``git`` only at a command position — start of line, or after a shell
# separator (``; & | && ||``). This skips string mentions (echo / printf /
# test data) that merely contain "git checkout", which would otherwise
# false-positive constantly. It can miss git buried behind an unusual prefix
# (e.g. ``VAR=x git checkout``), but the launcher + discipline are the primary
# mechanism; this hook is the backstop.
_AT_CMD = r"(?:^|[\n;&|])\s*"
_BRANCH_OP = re.compile(_AT_CMD + r"git\s+(?:checkout|switch)\b")
_FILE_RESTORE = re.compile(_AT_CMD + r"git\s+checkout\b[^\n|;&]*\s--(\s|$)")
_RESTORE = re.compile(_AT_CMD + r"git\s+restore\b")

_MESSAGE = (
    "BLOCKED — branch checkout/switch in the shared main worktree.\n\n"
    "Parallel agent sessions share this working tree; switching or creating a\n"
    "branch here strands another session's uncommitted work.\n\n"
    "Start an isolated session worktree instead:\n"
    "    scripts/dev/new-session.sh <name>\n\n"
    "Deliberate one-off (promote, rebase, etc.): prefix the command with\n"
    "    CLAUDE_ALLOW_MAIN_GIT=1 <your git command>\n"
)


def is_branch_switch(command: str) -> bool:
    """True if ``command`` switches or creates a branch (not a file restore)."""
    if not _BRANCH_OP.search(command):
        return False
    return not (_FILE_RESTORE.search(command) or _RESTORE.search(command))


def in_main_worktree(git_dir: str) -> bool:
    """True if ``git_dir`` belongs to the primary worktree.

    Linked worktrees report a git-dir nested under ``.../worktrees/<name>``;
    the primary worktree's is the plain repository ``.git``.
    """
    return bool(git_dir) and "worktrees/" not in git_dir.replace(os.sep, "/")


def has_override(command: str) -> bool:
    """True if an override env var is set in the environment or inline."""
    return any(os.environ.get(var) == "1" or f"{var}=1" in command for var in _OVERRIDE_VARS)


def _git_dir(cwd: str) -> str:
    try:
        result = subprocess.run(  # list-form argv, no shell
            ["git", "-C", cwd, "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:  # any failure → do not block
        return ""
    return result.stdout.strip()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # unparseable input → don't block
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    command = (event.get("tool_input") or {}).get("command", "") or ""
    if not is_branch_switch(command):
        return 0
    if has_override(command):
        return 0
    cwd = event.get("cwd") or os.getcwd()
    if not in_main_worktree(_git_dir(cwd)):
        return 0
    sys.stderr.write(_MESSAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
