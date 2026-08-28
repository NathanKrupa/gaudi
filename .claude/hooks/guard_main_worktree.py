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
``git restore``), ``git worktree add``, and the conscious-override escape
hatch (promotes, one-off rebases). The override is honored two ways: exported
in the session environment (``export CLAUDE_ALLOW_MAIN_GIT=1``) so
``os.environ`` carries it, or as a bare leading assignment prefix on the
guarded command itself (``CLAUDE_ALLOW_MAIN_GIT=1 git checkout main``). Only a
genuine leading assignment counts — the token must sit at a command position
directly in front of the guarded ``git``, so a quoted mention or a token
before some *other* command (``echo "CLAUDE_ALLOW_MAIN_GIT=1" && git
checkout``) does NOT wave the guard through. ``GS_ALLOW_MAIN_GIT=1`` is also
honored as a back-compat alias for grantspider, which shipped this guard
first.

The command line is *lexed*, not pattern-matched, so a verb counts only where
the shell would run it: as the argv of a simple command. A quoted mention — a
commit message, a ``gh issue create --body``, a heredoc discussing this very
guard — is an argument, never an invocation, and must not be refused. That
false positive blocked the operator three times in one morning (OS#401), and a
guard that cries wolf gets overridden reflexively, which is how the real case
ends up unguarded. Lexing is also *stricter* than the regex it replaced, not
looser: ``git "switch" x`` is a real switch the old anchor missed.

Command substitution is a command position in both spellings. ``$(...)`` falls
out of the lexer's own parentheses; the backtick form is split by
:func:`_simple_commands`, because a backtick is not shell punctuation to the
lexer and arrives glued to the word beside it. A backtick inside quotes stays
prose, like every other quoted mention.

**Remote containers stand down.** A Claude Code web container is a plain
``.git`` clone with the feature branch already checked out, so
:func:`in_main_worktree` classifies it as the primary checkout and refuses
every switch — while the hazard this guard exists for cannot occur there: the
container *is* the isolation, with no sibling session sharing its tree. The
stand-down keys on ``CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE``, which only the
remote harness sets, and only on its exact remote-container value. Unset, or
any other value, leaves the guard fully armed. It deliberately does NOT key on
``CLAUDE_ALLOW_MAIN_GIT``: the escape hatch is a per-command conscious act, and
wiring an environment classification to it would let one wave through the
other.

Decision logic is split into pure functions so it is unit-tested without git.
"""

import json
import os
import re
import shlex
import subprocess  # list-form argv, no shell; cwd is the only input
import sys
from collections.abc import Mapping

# Env vars that wave the guard through. CLAUDE_ALLOW_MAIN_GIT is the standard;
# GS_ALLOW_MAIN_GIT is grantspider's original name, kept as an alias.
_OVERRIDE_VARS = ("CLAUDE_ALLOW_MAIN_GIT", "GS_ALLOW_MAIN_GIT")

# The Claude Code remote harness sets this to identify a hosted container. It
# is read for its exact value and nothing else — a prefix, a different casing
# or a different value is not a remote container and stays guarded.
_REMOTE_ENV_VAR = "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE"
_REMOTE_CONTAINER_VALUE = "cloud_default"

# The git verbs that move the branch pointer, and the separator that turns a
# ``git checkout`` into a file restore instead.
_BRANCH_VERBS = frozenset({"checkout", "switch"})
_PATH_SEPARATOR = "--"

# ---------------------------------------------------------------------------
# Shell lexing — a verb counts only where the shell would run it.
#
# DUPLICATE — ``guard_shared_venv.py`` carries a byte-identical copy of this
# lexer (``_SEPARATORS``, ``_BACKTICK``, ``_ASSIGNMENT`` and the four functions
# below). It is NOT shared: each hook is a standalone byte-copy deployed into
# other repos' ``.claude/hooks/``, where a sibling import would not resolve. A
# change here must be made in both files or only one guard gets it.
# ---------------------------------------------------------------------------

# Tokens that end one simple command and start the next, so the token after
# them sits in command position. Grouping and substitution parens count.
_SEPARATORS = frozenset({";", ";;", "&", "&&", "|", "||", "|&", "(", ")", "{", "}"})

# A backtick opens or closes a command substitution, so it ends one simple
# command and starts another exactly as ``;`` does. Unlike the separators
# above it never arrives as a token of its own: it is not shell punctuation to
# the lexer, so ``git checkout`` in backticks lexes as ["`git", "checkout`"]
# and the split has to be made on the token's own text.
_BACKTICK = "`"

# A leading ``VAR=value`` on a command sets that command's environment; it does
# not displace the command position, so a run of them is skipped over.
_ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")


def _lex(text: str) -> list[str] | None:
    """``text`` as shell tokens, or None if a quote is left open."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def _token_runs(command: str) -> list[list[str]] | None:
    """Tokens of ``command``, one run per line, so a newline ends a command.

    A quote still open at end of line means the quoting spans lines — a
    heredoc, a multi-line PR body — so the whole command is lexed as one unit
    instead, keeping that quoted text a single token rather than reading its
    contents as commands. None means no lexing succeeded at all.
    """
    runs: list[list[str]] = []
    for line in command.splitlines():
        tokens = _lex(line)
        if tokens is None:
            whole = _lex(command)
            return None if whole is None else [whole]
        runs.append(tokens)
    return runs


def _simple_commands(tokens: list[str]) -> list[list[str]]:
    """``tokens`` split at shell separators — one argv per simple command.

    Backticks separate too, and are split out of the token that carries them
    (see :data:`_BACKTICK`). A *quoted* backtick survives that split as prose:
    the lexer has already collapsed ``echo "`git checkout`"`` to the single
    token ```git checkout```, whose interior space is inside the token, so
    splitting it yields the one word ``git checkout`` — never the two-word
    ``git`` argv the branch verbs match.

    Environment assignments already collected in the enclosing command carry
    into the substitution, so an explicit override written outside a backtick
    still reads as that command's override instead of being stranded in the
    outer argv.
    """
    argvs: list[list[str]] = [[]]

    def _open_command() -> None:
        """Start the next argv, inheriting the current one's assignments."""
        carried, _ = _split_assignments(argvs[-1])
        argvs.append(list(carried))

    for token in tokens:
        if token in _SEPARATORS:
            argvs.append([])
        elif _BACKTICK in token:
            for index, fragment in enumerate(token.split(_BACKTICK)):
                if index:
                    _open_command()
                if fragment:
                    argvs[-1].append(fragment)
        else:
            argvs[-1].append(token)
    return [argv for argv in argvs if argv]


def _split_assignments(argv: list[str]) -> tuple[list[str], list[str]]:
    """``argv`` as (its leading environment assignments, the command it runs)."""
    index = 0
    while index < len(argv) and _ASSIGNMENT.match(argv[index]):
        index += 1
    return argv[:index], argv[index:]


def _invocations(command: str) -> list[tuple[list[str], list[str]]] | None:
    """Every simple command in ``command`` as (env assignments, argv).

    None means the text could not be lexed, which callers treat as
    un-analysable rather than as safe.
    """
    runs = _token_runs(command)
    if runs is None:
        return None
    return [
        _split_assignments(argv) for tokens in runs for argv in _simple_commands(tokens)
    ]


# ---------------------------------------------------------------------------
# Unlexable fallback.
#
# A command with an unbalanced quote is text no shell would run either, but the
# safe direction for a guard is to refuse rather than to wave it through, so the
# original command-position regex stays as the fallback for that one case.
#
# DUPLICATE — ``guard_trunk_pull.py`` carries a byte-identical copy of these
# three lines. They are NOT shared, for the same reason as the lexer above. Any
# change here must be made in BOTH files or only one guard gets it.
# ``check_destructive_command.py`` no longer carries them: its fallback drops
# the quote characters and lexes again, which needs no command-position regex.
# ---------------------------------------------------------------------------
_SEP = r"(?:^|[\n;&|`(])\s*"  # start-of-line, shell separator, or substitution opener
_ASSIGN = r"(?:\w+=\S+\s+)*"  # a run of ``VAR=value`` env assignments
_AT_CMD = _SEP + _ASSIGN
_BRANCH_OP = re.compile(_AT_CMD + r"git\s+(?:checkout|switch)\b")
_FILE_RESTORE = re.compile(_AT_CMD + r"git\s+checkout\b[^\n|;&]*\s--(\s|$)")
_RESTORE = re.compile(_AT_CMD + r"git\s+restore\b")

# The inline escape hatch, in the same unlexable fallback: an override var set
# to 1 as a real leading assignment on the guarded git command.
_OVERRIDE_NAMES = "|".join(_OVERRIDE_VARS)
_OVERRIDE_PREFIX = re.compile(
    _SEP
    + _ASSIGN
    + rf"(?:{_OVERRIDE_NAMES})=1\s+"
    + _ASSIGN
    + r"git\s+(?:checkout|switch|restore)\b"
)

_MESSAGE = (
    "BLOCKED — branch checkout/switch in the shared main worktree.\n\n"
    "Parallel agent sessions share this working tree; switching or creating a\n"
    "branch here strands another session's uncommitted work.\n\n"
    "Start an isolated session worktree instead:\n"
    "    scripts/dev/new-session.sh <name>\n\n"
    "Deliberate one-off (promote, rebase, etc.): prefix the command with\n"
    "    CLAUDE_ALLOW_MAIN_GIT=1 <your git command>\n"
)


def _is_branch_op(argv: list[str]) -> bool:
    """True if ``argv`` is a git invocation that moves the branch pointer.

    ``git checkout`` with a ``--`` path separator restores files instead, and
    is left alone; so is every other subcommand.
    """
    if argv[:1] != ["git"]:
        return False
    if len(argv) < 2 or argv[1] not in _BRANCH_VERBS:
        return False
    return _PATH_SEPARATOR not in argv[2:]


def _unlexable_branch_switch(command: str) -> bool:
    """The pre-lexer verdict, used only where the text could not be lexed."""
    if not _BRANCH_OP.search(command):
        return False
    return not (_FILE_RESTORE.search(command) or _RESTORE.search(command))


def is_branch_switch(command: str) -> bool:
    """True if ``command`` switches or creates a branch (not a file restore)."""
    invocations = _invocations(command)
    if invocations is None:
        return _unlexable_branch_switch(command)
    return any(_is_branch_op(argv) for _assignments, argv in invocations)


def in_main_worktree(git_dir: str) -> bool:
    """True if ``git_dir`` belongs to the primary worktree.

    Linked worktrees report a git-dir nested under ``.../worktrees/<name>``;
    the primary worktree's is the plain repository ``.git``.
    """
    return bool(git_dir) and "worktrees/" not in git_dir.replace(os.sep, "/")


def in_remote_container(env: Mapping[str, str]) -> bool:
    """True if ``env`` identifies a Claude Code remote container.

    A remote container is a disposable clone with no sibling session sharing
    its tree, so the collision this guard prevents cannot happen there. Only
    the harness-set environment type counts, and only at its exact value — an
    unset variable is the local case and stays guarded.
    """
    return env.get(_REMOTE_ENV_VAR) == _REMOTE_CONTAINER_VALUE


def _inline_override(assignments: list[str]) -> bool:
    """True if this invocation's own ``VAR=value`` prefix carries an override."""
    for assignment in assignments:
        name, _, value = assignment.partition("=")
        if name in _OVERRIDE_VARS and value == "1":
            return True
    return False


def has_override(command: str) -> bool:
    """True if an override var is set — in the real environment or as a
    genuine leading assignment on the guarded git command.

    Environment detection uses ``os.environ`` only (an exported override).
    Inline detection requires the assignment to be that invocation's own
    prefix, so a quoted mention (``echo "CLAUDE_ALLOW_MAIN_GIT=1"``) or a
    prefix on some *other* command does not count.
    """
    if any(os.environ.get(var) == "1" for var in _OVERRIDE_VARS):
        return True
    invocations = _invocations(command)
    if invocations is None:
        return bool(_OVERRIDE_PREFIX.search(command))
    return any(
        _is_branch_op(argv) and _inline_override(assignments)
        for assignments, argv in invocations
    )


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
    if in_remote_container(os.environ):
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
