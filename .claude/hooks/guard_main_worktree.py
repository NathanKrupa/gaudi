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
# DUPLICATE — every guard in ``tests/dev/test_hook_lexer_drift.py``'s
# ``_HOOKS``, this one among them, carries a byte-identical copy of this lexer
# (``_SEPARATORS``, ``_BACKTICK``, ``_ASSIGNMENT``, ``_ShellLexer`` and every
# member below, through ``_invocations``); ``guard_gate_pipe.py`` and ``guard_endless_substitution.py``
# carry ``_ShellLexer`` too. It is NOT shared: each hook is a standalone
# byte-copy deployed into other repos' ``.claude/hooks/``, where a sibling
# import would not resolve. A change here must be made in every copy —
# ``tests/dev/test_hook_lexer_drift.py`` notices when one drifts.
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


# The shell's comment rule. A hash starts a comment only where a word could
# start: between tokens, outside quotes. Inside a word (``a#b``, ``$#``, a URL
# fragment) it is part of that word, and the shell runs the rest of the line.
# ``shlex`` consults ``commenters`` both between tokens and inside a word, never
# inside quotes, so the hash is offered only in its between-tokens state.
# ``shlex.__init__`` assigns ``commenters``; the setter discards that value.
# Identical in every Bash guard that lexes with ``shlex``:
# ``tests/dev/test_hook_lexer_drift.py`` compares the copies.
class _ShellLexer(shlex.shlex):
    @property
    def commenters(self) -> str:
        return "#" if self.state == " " else ""

    @commenters.setter
    def commenters(self, value: str) -> None:
        pass


# The nest-true text. Inside a double-quoted string the shell opens a fresh
# quoting context in ``$( )``, backticks and ``${ }``, but ``_ShellLexer``
# toggles on every double quote and so closes the outer string at the first
# inner one. ``_nest_true`` gives the text back with each double quote inside
# such a nested region preceded by an odd run of backslashes: the unchanged
# lexer reads that as a literal quote and stays in its double-quote state to
# the real closing quote. It vouches only for text it walked to the end with
# the constructs it models, every context closed, and returns None for the
# rest. Text with no nested quote comes back unchanged. Identical in every
# Bash guard that lexes with ``shlex``: ``tests/dev/test_hook_lexer_drift.py``
# compares the copies.
_NEST_WORD_BREAKS = " \t\n;&|()<>"
_NEST_DELIMITER = re.compile(r"[\w.-]+")
_NEST_MAX_DEPTH = 64


class _Unmodelled(Exception):
    """A construct the nest-true scanner does not model, or a context left open."""


class _NestScanner:
    """One walk over ``text``, building its nest-true form in ``out``.

    ``nested`` is True inside a substitution or expansion that sits in a
    double-quoted string, where every double quote read is escaped. A heredoc
    waits in ``heredocs`` for the line end of the code frame that named it.
    """

    def __init__(self, text: str) -> None:
        self.text, self.i, self.out = text, 0, []
        self.depth = self.frames = self.heredoc_frame = 0
        self.heredocs: list[tuple[str, bool]] = []

    def peek(self, offset: int = 0) -> str:
        return self.text[self.i + offset : self.i + offset + 1]

    def take(self, count: int = 1) -> None:
        self.out.append(self.text[self.i : self.i + count])
        self.i += count

    def data(self, nested: bool) -> None:
        """One character, a double quote escaped when ``nested`` and not already."""
        if nested and self.peek() == '"':
            run = 0
            while self.text[self.i - run - 1 : self.i - run] == "\\":
                run += 1
            if run % 2 == 0:
                self.out.append("\\")
        self.take()

    def quoted(self, nested: bool) -> None:
        """One character inside quotes or an expansion, which must not end there."""
        if not self.peek():
            raise _Unmodelled("unclosed")
        if self.peek() == "\n" and self.heredocs:
            raise _Unmodelled("heredoc-placement")
        self.data(nested)

    def enter(self) -> int:
        self.depth += 1
        self.frames += 1
        if self.depth > _NEST_MAX_DEPTH:
            raise _Unmodelled("depth")
        return self.frames

    def code(self, nested: bool, closing: bool) -> None:
        """Shell code, to the ``)`` closing its ``$(`` or, without ``closing``, to the end."""
        frame = self.enter()
        parens, word_start = 0, True
        while self.peek() and not (closing and self.peek() == ")" and not parens):
            char, start, word_start = self.peek(), word_start, False
            if char == "\\":
                word_start = start if self.peek(1) == "\n" else False
                self.take(2)
            elif char == "'":
                self.single(nested)
            elif char == '"':
                self.double(nested)
            elif char == "`":
                self.backtick(nested)
            elif char == "$":
                self.dollar(nested, False)
            elif self.text.startswith("<<", self.i):
                self.heredoc(nested, frame)
            elif char in "<>" and self.peek(1) == "(":
                raise _Unmodelled("process-substitution")
            elif start and char == "#":
                while self.peek() not in ("", "\n"):
                    self.data(nested)
            elif closing and start and self.text.startswith("case", self.i) and (
                self.peek(4) in _NEST_WORD_BREAKS
            ):
                raise _Unmodelled("case")
            elif char == "\n" and self.heredocs:
                if self.heredoc_frame != frame:
                    raise _Unmodelled("heredoc-placement")
                self.take()
                self.bodies(nested)
                word_start = True
            else:
                if closing and char in "()":
                    parens += 1 if char == "(" else -1
                self.take()
                word_start = char in _NEST_WORD_BREAKS
        if closing:
            if not self.peek():
                raise _Unmodelled("unclosed")
            self.take()
        elif self.heredocs:
            raise _Unmodelled("heredoc-placement")
        self.depth -= 1

    def single(self, nested: bool) -> None:
        self.take()
        while self.peek() != "'":
            self.quoted(nested)
        self.take()

    def double(self, nested: bool) -> None:
        """A double-quoted string; what it holds is nested, its own quotes only if it is."""
        self.enter()
        self.data(nested)
        while self.peek() != '"':
            char = self.peek()
            if char == "\\":
                self.take(2)
            elif char == "`":
                self.backtick(True)
            elif char == "$":
                self.dollar(True, True)
            else:
                self.quoted(nested)
        self.data(nested)
        self.depth -= 1

    def dollar(self, nested: bool, in_double: bool) -> None:
        after = self.peek(1)
        if after == "(" and self.peek(2) != "(":
            self.take(2)
            self.code(nested, True)
        elif after == "{":
            self.take(2)
            self.parameter(nested)
        elif after in ("(", "[") or (not in_double and after in ("'", '"')):
            raise _Unmodelled("arithmetic" if after in ("(", "[") else "ansi-c-or-locale")
        else:
            self.take()

    def parameter(self, nested: bool) -> None:
        self.enter()
        while self.peek() != "}":
            char = self.peek()
            if char in ("'", "{"):
                raise _Unmodelled("parameter")
            if char == "\\":
                self.take(2)
            elif char == '"':
                self.double(nested)
            elif char == "`":
                self.backtick(nested)
            elif char == "$":
                self.dollar(nested, False)
            else:
                self.quoted(nested)
        self.take()
        self.depth -= 1

    def backtick(self, nested: bool) -> None:
        """A backtick substitution holding no substitution, heredoc or open quote."""
        self.enter()
        self.take()
        quote = ""
        while self.peek() != "`" or quote:
            char = self.peek()
            if (
                char == "`"
                or (char == "\\" and nested and self.peek(1) == '"')
                or (char == "$" and self.peek(1) in ("(", "{", "[", "'", '"'))
                or self.text.startswith("<<", self.i)
            ):
                raise _Unmodelled("backtick")
            if char == "\\":
                self.take(2)
                continue
            if char == quote:
                quote = ""
            elif not quote and char in ("'", '"'):
                quote = char
            self.quoted(nested)
        self.take()
        self.depth -= 1

    def heredoc(self, nested: bool, frame: int) -> None:
        """A ``<<`` redirect: only a quoted delimiter, whose body is never expanded."""
        if self.text.startswith("<<<", self.i):
            self.take(3)
            return
        if self.heredocs and self.heredoc_frame != frame:
            raise _Unmodelled("heredoc-placement")
        self.take(2)
        strip = self.peek() == "-"
        if strip:
            self.take()
        while self.peek() in (" ", "\t"):
            self.take()
        word, quote, quoted = [], "", False
        while self.peek() and (quote or self.peek() not in _NEST_WORD_BREAKS):
            char = self.peek()
            if (quote and char == "\\") or char == "\n":
                raise _Unmodelled("heredoc")
            if char == "\\":
                quoted = True
                self.take()
                word.append(self.peek())
            elif char == quote:
                quote = ""
            elif not quote and char in ("'", '"'):
                quote, quoted = char, True
            else:
                word.append(char)
            self.data(nested)
        delimiter = "".join(word)
        if quote or not quoted or not _NEST_DELIMITER.fullmatch(delimiter):
            raise _Unmodelled("heredoc")
        self.heredocs.append((delimiter, strip))
        self.heredoc_frame = frame

    def bodies(self, nested: bool) -> None:
        """Each waiting heredoc's body, through its delimiter line."""
        for delimiter, strip in self.heredocs:
            line = None
            while line != delimiter:
                if not self.peek():
                    raise _Unmodelled("heredoc")
                end = self.text.find("\n", self.i)
                end = len(self.text) if end < 0 else end
                line = self.text[self.i : end]
                if not nested and ("'" in line or '"' in line):
                    raise _Unmodelled("heredoc-quote")
                while self.i < end:
                    self.data(nested)
                if self.peek():
                    self.take()
                line = line.lstrip("\t") if strip else line
        self.heredocs = []


def _nest_true(text: str) -> str | None:
    """``text`` with each double quote nested in a double-quoted string escaped, or None."""
    scanner = _NestScanner(text)
    try:
        scanner.code(False, False)
    except _Unmodelled:
        return None
    return "".join(scanner.out)


def _lex(text: str) -> list[str] | None:
    """``text`` as shell tokens, or None if a quote is left open."""
    lexer = _ShellLexer(text, posix=True, punctuation_chars=True)
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


# The line-true reading. Once a line leaves a quote open, ``_token_runs`` lexes
# the whole text as one unit, in which a newline outside quotes is whitespace.
# This reading lexes the whole text once through a stream that decides each
# newline from the lexer's own state. A guard that decides under both readings
# decides under each on its own and holds if either holds. Two marker
# characters stand in for newlines, taken from candidates the text does not
# hold; with fewer than two free, lines are joined until they lex.
_LINE_MARKER_CANDIDATES = "\x1c\x1d\x1e\x1f"
_DEFAULT_PUNCTUATION = shlex.shlex("", punctuation_chars=True).punctuation_chars


class _LineStream:
    """Each newline as the lexer's state reads it: escaped, the continuation
    marker; quoted, a newline; else the line-end marker. ``readline`` (shlex's
    comment skip) leaves the newline unread, so a comment ends at its line."""

    def __init__(self, text: str, line_end: str, continuation: str) -> None:
        self._text, self._position = text, 0
        self._line_end, self._continuation = line_end, continuation
        self.lexer: shlex.shlex | None = None

    def read(self, size: int = 1) -> str:
        char = self._text[self._position : self._position + 1]
        self._position += len(char)
        if char != "\n" or self.lexer is None:
            return char
        if self.lexer.state in self.lexer.escape:
            return self._continuation
        return char if self.lexer.state in self.lexer.quotes else self._line_end

    def readline(self, size: int = -1) -> str:
        end = self._text.find("\n", self._position)
        end = len(self._text) if end < 0 else end
        rest, self._position = self._text[self._position : end], end
        return rest


def _joined_line_runs(command: str) -> list[list[str]] | None:
    """Runs for text holding the marker characters: lines joined until they lex."""
    runs: list[list[str]] = []
    pending: list[str] = []
    for line in command.split("\n"):
        pending.append(line)
        tokens = _lex("\n".join(pending))
        if tokens is not None:
            runs.append(tokens)
            pending = []
    return None if pending else [run for run in runs if run]


def _line_runs(command: str) -> list[list[str]] | None:
    """Tokens of ``command``, one run per line end the shell acts on.

    Quoted text spanning lines stays one token, as in :func:`_token_runs`. None
    when the whole text does not lex. Empty runs are dropped.
    """
    markers = [char for char in _LINE_MARKER_CANDIDATES if char not in command]
    if len(markers) < 2:
        return _joined_line_runs(command)
    line_end, continuation = markers[:2]
    stream = _LineStream(command, line_end, continuation)
    lexer = _ShellLexer(stream, posix=True, punctuation_chars=_DEFAULT_PUNCTUATION + line_end)
    lexer.whitespace_split = True
    stream.lexer = lexer
    try:
        raw = list(lexer)
    except ValueError:
        return None
    runs: list[list[str]] = [[]]
    for token in raw:
        if continuation in token:
            token = token.replace(continuation, "")
            if not token:
                continue
        if line_end not in token:
            runs[-1].append(token)
            continue
        # A line end fused onto punctuation (``;``, ``&&``, ``|``) is split off it.
        for part in re.split(f"({re.escape(line_end)})", token):
            if part == line_end:
                runs.append([])
            elif part:
                runs[-1].append(part)
    return [run for run in runs if run]


def _readings(command: str) -> tuple[bool, ...]:
    """The readings a guard decides under: today's, then the line-true one if lines exist."""
    return (False, True) if "\n" in command else (False,)


def _reading_pairs(command: str) -> tuple[tuple[bool, bool], ...]:
    """Every reading a guard decides under, as (line_true, nest_true), today's first.

    Each of :func:`_readings` on today's text, then each again on the
    nest-true text where :func:`_nest_true` vouches for it. A guard decides
    each on its own and holds if any holds.

    A double quote is escaped only inside a ``$( )``, ``${ }`` or backtick
    region, so a text holding no double quote, or neither a dollar sign nor a
    backtick, comes back from :func:`_nest_true` unchanged. So does every
    script it hands a shell, since the lexer builds each token from the text's
    own characters. Its nest-true readings would repeat today's, and are not
    made.
    """
    nested = '"' in command and ("$" in command or "`" in command)
    nests = (False, True) if nested and _nest_true(command) is not None else (False,)
    return tuple((line, nest) for nest in nests for line in _readings(command))


def _invocations(
    command: str, line_true: bool = False, nest_true: bool = False
) -> list[tuple[list[str], list[str]]] | None:
    """Every simple command in ``command`` as (env assignments, argv).

    ``line_true`` selects the line-true reading, :func:`_line_runs`;
    today's reading, :func:`_token_runs`, is the default. ``nest_true``
    reads :func:`_nest_true`'s text in place of ``command`` where it vouches
    for it, and ``command`` itself where it does not.

    None means the text could not be lexed, which callers treat as
    un-analysable rather than as safe.
    """
    vouched = _nest_true(command) if nest_true else None
    text = command if vouched is None else vouched
    runs = _line_runs(text) if line_true else _token_runs(text)
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


def is_branch_switch(command: str, line_true: bool = False, nest_true: bool = False) -> bool:
    """True if ``command`` switches or creates a branch (not a file restore)."""
    invocations = _invocations(command, line_true, nest_true)
    if invocations is None:
        return _unlexable_branch_switch(command)
    return any(_is_branch_op(argv) for _assignments, argv in invocations)


def refuses(command: str) -> bool:
    """True if some reading holds a branch switch without that reading's override.

    Each reading is decided on its own: an overridden switch one reading makes
    visible must not clear a switch another reading holds without one.
    """
    return any(
        is_branch_switch(command, line_true, nest_true)
        and not has_override(command, line_true, nest_true)
        for line_true, nest_true in _reading_pairs(command)
    )


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


def has_override(command: str, line_true: bool = False, nest_true: bool = False) -> bool:
    """True if an override var is set — in the real environment or as a
    genuine leading assignment on the guarded git command.

    Environment detection uses ``os.environ`` only (an exported override).
    Inline detection requires the assignment to be that invocation's own
    prefix, so a quoted mention (``echo "CLAUDE_ALLOW_MAIN_GIT=1"``) or a
    prefix on some *other* command does not count.
    """
    if any(os.environ.get(var) == "1" for var in _OVERRIDE_VARS):
        return True
    invocations = _invocations(command, line_true, nest_true)
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
    if not refuses(command):
        return 0
    cwd = event.get("cwd") or os.getcwd()
    if not in_main_worktree(_git_dir(cwd)):
        return 0
    sys.stderr.write(_MESSAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
