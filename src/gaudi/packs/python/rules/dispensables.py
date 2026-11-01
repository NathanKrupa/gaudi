# ABOUTME: Fowler "dispensables" code smells: things that could be removed without loss.
# ABOUTME: Lazy elements, speculative generality, excess and history-narrating comments, data class, temporal names.
from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Iterator

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.ast_helpers import is_test_path
from gaudi.packs.python.context import FileInfo, PythonContext


# Dunder method sets shared with couplers.py.
# _BOILERPLATE_DUNDERS is the base; _DATA_DUNDERS extends it.
_BOILERPLATE_DUNDERS = frozenset({"__init__", "__repr__", "__str__", "__eq__", "__hash__"})


# ---------------------------------------------------------------
# SMELL-014  LazyElement
# ---------------------------------------------------------------


class LazyElement(Rule):
    """SMELL-014: Classes with a single trivial method.

    Principles: #6 (The best line is the one not written).
    Source: FOWLER Ch. 3 — Lazy Element.
    """

    code = "SMELL-014"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    # Scoped away from Classical/Convention/Resilient/Event-Sourced:
    # single-method classes are how Classical wires Protocols and
    # Repositories; Convention builds them for framework seams;
    # Resilient wraps for circuit breakers; Event-Sourced wraps
    # aggregates. See docs/philosophy/classical.md rubric #3.
    philosophy_scope = frozenset({"pragmatic", "unix", "functional", "data-oriented"})
    message_template = "Class '{class_name}' has only one method — consider inlining"
    recommendation_template = (
        "A class with a single method that just returns is "
        "likely overengineered. Use a function instead."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                real = [m for m in methods if m.name not in _BOILERPLATE_DUNDERS]
                if len(real) != 1:
                    continue
                body = real[0].body
                if len(body) == 1 and isinstance(body[0], ast.Return):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-015  SpeculativeGenerality
# ---------------------------------------------------------------


class SpeculativeGenerality(Rule):
    """SMELL-015: Premature abstractions or unused parameters.

    Principles: #6 (The best line is the one not written).
    Source: FOWLER Ch. 3 — Speculative Generality.
    """

    code = "SMELL-015"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    # Scoped away from Classical/Convention/Resilient/Event-Sourced:
    # extensibility seams are a Classical virtue. See
    # docs/philosophy/pragmatic.md catechism #1 — this is the
    # canonical Pragmatic rule.
    philosophy_scope = frozenset({"pragmatic", "unix", "functional", "data-oriented"})
    message_template = "{detail}"
    recommendation_template = "{advice}"

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            findings.extend(self._check_abstract(tree, f.relative_path))
            findings.extend(self._check_unused_params(tree, f.relative_path))
        return findings

    def _check_abstract(
        self,
        tree: ast.Module,
        path: str,
    ) -> list[Finding]:
        results: list[Finding] = []
        # Find abstract classes and their subclasses
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        abc_classes: set[str] = set()
        for cls in classes:
            for node in ast.walk(cls):
                if isinstance(node, ast.Name):
                    if node.id in ("abstractmethod", "ABC"):
                        abc_classes.add(cls.name)
                        break
                if isinstance(node, ast.Attribute):
                    if node.attr == "abstractmethod":
                        abc_classes.add(cls.name)
                        break
        # Count subclasses per abstract class
        for abc_name in abc_classes:
            subs = sum(
                1
                for cls in classes
                if cls.name != abc_name
                and any((isinstance(b, ast.Name) and b.id == abc_name) for b in cls.bases)
            )
            if subs <= 1:
                results.append(
                    self.finding(
                        file=path,
                        line=1,
                        detail=f"Abstract class '{abc_name}' has only {subs} subclass",
                        advice="If there's only one implementation, the abstraction is premature.",
                        class_name=abc_name,
                        count=subs,
                    )
                )
        return results

    def _check_unused_params(
        self,
        tree: ast.Module,
        path: str,
    ) -> list[Finding]:
        results: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Find params with default None
            args = node.args
            defaults = list(args.defaults)
            # Pad defaults to align with args
            num_no_default = len(args.args) - len(defaults)
            padded = [None] * num_no_default + defaults
            none_params: list[str] = []
            for arg, default in zip(args.args, padded):
                if arg.arg in ("self", "cls"):
                    continue
                if (
                    default is not None
                    and isinstance(default, ast.Constant)
                    and default.value is None
                ):
                    none_params.append(arg.arg)
            # Also check kwonlyargs
            for arg, default in zip(args.kwonlyargs, args.kw_defaults):
                if (
                    default is not None
                    and isinstance(default, ast.Constant)
                    and default.value is None
                ):
                    none_params.append(arg.arg)
            if len(none_params) < 2:
                continue
            # Check which are unused in body
            body_names: set[str] = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    body_names.add(child.id)
            unused = [p for p in none_params if p not in body_names]
            if len(unused) >= 2:
                results.append(
                    self.finding(
                        file=path,
                        line=node.lineno,
                        detail=(
                            f"Function '{node.name}' has "
                            f"{len(unused)} unused parameters: "
                            f"{', '.join(unused)}"
                        ),
                        advice="Remove unused parameters. They add complexity without value.",
                        function=node.name,
                        count=len(unused),
                        params=", ".join(unused),
                    )
                )
        return results


# ---------------------------------------------------------------
# SMELL-024  Comments
# ---------------------------------------------------------------


class Comments(Rule):
    """SMELL-024: Functions with excessive comment density.

    Principles: #3 (Names are contracts), #11 (The reader is the user).
    Source: FOWLER Ch. 3 — Comments.
    """

    code = "SMELL-024"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = (
        "Function '{function}' has {comment_count} comments in {code_count} lines of code"
    )
    recommendation_template = (
        "High comment density suggests the code should be "
        "clearer. Rename variables and extract methods "
        "instead of adding comments."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            source_lines = f.source.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.end_lineno is None:
                    continue
                # Include preceding comment block
                start = node.lineno - 1
                while start > 0 and source_lines[start - 1].strip().startswith("#"):
                    start -= 1
                end = node.end_lineno
                func_lines = source_lines[start:end]
                comment_count = 0
                code_count = 0
                for line in func_lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("#"):
                        comment_count += 1
                    else:
                        code_count += 1
                if (
                    comment_count >= 5
                    and code_count > 0
                    and comment_count / (comment_count + code_count) > 0.5
                ):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            function=node.name,
                            comment_count=comment_count,
                            code_count=code_count,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-022  DataClassSmell
# ---------------------------------------------------------------

_DATA_DUNDERS = _BOILERPLATE_DUNDERS | {"__lt__", "__le__", "__gt__", "__ge__"}


class DataClassSmell(Rule):
    """SMELL-022: Classes that are pure data holders.

    Principles: #6 (The best line is the one not written).
    Source: FOWLER Ch. 3 — Data Class.
    """

    code = "SMELL-022"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    # Scoped to Classical/Convention only: Functional, Data-Oriented,
    # Event-Sourced, and Unix treat pure data as the primary building
    # block. Frozen dataclasses and events are the point, not a smell.
    philosophy_scope = frozenset({"classical", "convention"})
    message_template = "Class '{class_name}' is a pure data holder — consider using a dataclass"
    recommendation_template = (
        "Use @dataclass or a NamedTuple for pure data "
        "containers. They provide __init__, __repr__, and "
        "__eq__ automatically."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if not methods:
                    continue
                has_init = any(m.name == "__init__" for m in methods)
                if not has_init:
                    continue
                all_data = all(m.name in _DATA_DUNDERS for m in methods)
                if all_data:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-025  TemporalIdentifier
# ---------------------------------------------------------------

# Temporal markers that should not appear as standalone words in identifiers.
_TEMPORAL_WORDS = re.compile(
    r"(?:^|(?<=[a-z]))(?:New|Old|Legacy|Deprecated|Obsolete|Refactored)(?=[A-Z]|$)"  # camelCase
    r"|(?:^|_)(?:new|old|legacy|deprecated|obsolete|refactored)(?:_|$)",  # snake_case
    re.IGNORECASE,
)
# Version suffixes like V2, v3, _v10 — matched on split words.
_VERSION_WORD = re.compile(r"^v\d+$", re.IGNORECASE)

# Domain terms where a version number is part of the name, not a temporal marker.
# Checked against the full identifier before reporting a version-suffix match.
_PROTOCOL_ALLOWLIST = re.compile(
    r"(?:IP|IPv|OAuth|HTTP|Http|http|TLS|Tls|tls|H|Python|python|SSL|ssl"
    r"|QUIC|quic|Quic|USB|usb|Usb|HDMI|hdmi|Hdmi|MP|mp|Mp"
    r"|WebSocket|websocket|WS|ws)v?\d",
    re.IGNORECASE,
)


def _split_identifier(name: str) -> list[str]:
    """Split an identifier into word components for matching.

    Handles both snake_case and camelCase/PascalCase.
    """
    # Split on underscores first
    parts = name.split("_")
    words: list[str] = []
    for part in parts:
        # Split camelCase: insert boundary between lower-to-upper transitions
        tokens = re.sub(r"([a-z])([A-Z])", r"\1_\2", part).split("_")
        words.extend(t for t in tokens if t)
    return words


def _has_temporal_marker(name: str) -> bool:
    """Check if an identifier contains a temporal marker word."""
    words = _split_identifier(name)
    for word in words:
        if word.lower() in {"new", "old", "legacy", "deprecated", "obsolete", "refactored"}:
            return True
        # Check version suffixes on split words, but skip protocol/domain versions
        if _VERSION_WORD.match(word) and not _PROTOCOL_ALLOWLIST.search(name):
            return True

    return False


class TemporalIdentifier(Rule):
    """SMELL-025: Temporal markers in identifiers.

    Principles: #3 (Names are contracts).
    Source: Ousterhout, *A Philosophy of Software Design* Ch. 14 —
    names should describe what a thing is, not when it was added.

    Fires on class names, function names, and module-level variable names
    that contain temporal words (new, old, legacy, deprecated, obsolete,
    refactored) or version suffixes (V2, v3).

    Does NOT fire on protocol/domain versions (IPv4, IPv6, OAuth2, HTTP2,
    Python3) — these are part of the domain name, not change history.
    Allowlist: IP, IPv, OAuth, HTTP, TLS, H, Python, SSL, QUIC, USB,
    HDMI, MP, WebSocket, WS.

    Also does NOT fire on a constant whose version-suffix marker pins its
    string value (``SCHEMA_V1 = "v1"``): the literal is a persisted/DB-pinned
    contract, and the ``_V1`` names the version the value encodes rather than
    recording change history.
    """

    code = "SMELL-025"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = (
        "Identifier '{name}' contains temporal marker '{marker}' — "
        "names should describe what a thing is, not when it was added"
    )
    recommendation_template = (
        "Rename to describe the current purpose. If the 'old' version "
        "is dead, delete it. If it's current, drop the temporal prefix. "
        "For version suffixes, the canonical name belongs to the active "
        "implementation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            durable_assigns = self._durable_assign_ids(tree)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)) and (
                    id(node) not in durable_assigns
                ):
                    continue
                names_and_lines = self._extract_names(node)
                for name, line in names_and_lines:
                    marker = self._find_marker(name)
                    if not marker:
                        continue
                    if self._is_pinned_version_literal(node, marker):
                        continue
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=line,
                            name=name,
                            marker=marker,
                        )
                    )
        return findings

    @staticmethod
    def _durable_assign_ids(tree: ast.Module) -> set[int]:
        """Assignments that create a durable name: module-level and class-body.

        A local variable inside a function is ephemeral — it has no callers, no
        importers, and dies at the end of the call. ``new`` there is the
        ordinary English adjective (``new = tuple(i for i in issues if i not in
        ruled)`` means the issues not seen before), and renaming it makes the
        code worse. The rule's subject is names that outlive the moment they
        were written, which is what its docstring always said: it walked every
        assignment in the file regardless.
        """
        durable: set[int] = set()
        bodies: list[list[ast.stmt]] = [list(tree.body)]
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bodies.append(list(node.body))
        for body in bodies:
            for stmt in body:
                if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                    durable.add(id(stmt))
        return durable

    @staticmethod
    def _is_pinned_version_literal(node: ast.AST, marker: str) -> bool:
        """Exempt a constant whose name's version marker pins its string value.

        ``SCHEMA_V1 = "v1"`` / ``PROMPT_VERSION_V1 = "...v1"`` is a persisted,
        DB-pinned literal: the ``_V1`` in the name is not change history, it
        names the version the stored value encodes. The literal IS the
        contract. Only a version-suffix marker (V\\d) whose digits appear in a
        string-literal value qualifies — a temporal WORD ('old', 'legacy') or
        a non-string value (``OLD_API_TIMEOUT = 30``) never does.
        """
        if not _VERSION_WORD.match(marker):
            return False
        if not isinstance(node, ast.Assign):
            return False
        value = node.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            return False
        version_digits = marker[1:]  # 'V1' -> '1'
        return version_digits in value.value

    @staticmethod
    def _extract_names(node: ast.AST) -> list[tuple[str, int]]:
        """Extract (name, lineno) pairs from AST nodes worth checking."""
        results: list[tuple[str, int]] = []
        if isinstance(node, ast.ClassDef):
            results.append((node.name, node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            results.append((node.name, node.lineno))
        elif isinstance(node, ast.Assign):
            # Module-level constants / variables
            for target in node.targets:
                if isinstance(target, ast.Name):
                    results.append((target.id, node.lineno))
        return results

    @staticmethod
    def _find_marker(name: str) -> str | None:
        """Return the temporal marker found in name, or None."""
        words = _split_identifier(name)
        for word in words:
            if word.lower() in {
                "new",
                "old",
                "legacy",
                "deprecated",
                "obsolete",
                "refactored",
            }:
                return word

        words = _split_identifier(name)
        for word in words:
            if _VERSION_WORD.match(word) and not _PROTOCOL_ALLOWLIST.search(name):
                return word

        return None


# ---------------------------------------------------------------
# SMELL-026  HistoryNarratingComment
# ---------------------------------------------------------------

# Pronoun subjects that make "X used to <verb>" a statement about the past. A
# noun before "used to" is usually a participle ("the helper used to look up
# rows"), and "is used to" is passive purpose, so neither is listed.
_USED_TO_SUBJECTS = "it|this|that|these|those|we|they|which|who"
# A data verb ahead of "before #<n>" ("rows written before ...") dates the data
# a line handles, which is provenance the reader needs, not a story about the
# code; after any other word the phrase narrates the change.
_DATA_VERBS = ("written", "entered", "made", "created", "sent", "stored", "saved", "recorded")
_UNQUALIFIED_BEFORE = "".join(rf"(?<!{verb}\s)" for verb in _DATA_VERBS) + "before"
_CODE_NOUNS = (
    "code|behaviou?r|implementation|approach|logic|version|way|path|helper|function|method|api"
)

# Phrases that narrate change history. Each is narrow on purpose: words like
# "previously", "no longer" and "old" are ordinary runtime vocabulary
# ("the previously fetched page", "rows that no longer match", "the old
# value"), so only their history-telling forms are listed. A bare issue
# citation ("see #412") is provenance and never matches.
_HISTORY_PHRASES = re.compile(
    "|".join(
        (
            rf"\b(?:{_USED_TO_SUBJECTS})\s+used\s+to\b",
            r"\bused\s+to\s+be\b",
            r"(?:^|(?<=[.;:]\s))previously,",
            r"\b(?:this|it|we|they|which)\s+(?:was\s+|were\s+|had\s+)?previously\b",
            r"\b(?:was|were|has\s+been|have\s+been)\s+refactored\b",
            r"\b(?:renamed|refactored)\s+from\b",
            rf"\b(?:since|{_UNQUALIFIED_BEFORE}|prior\s+to)\s+(?:PR\s*|issue\s*|[A-Za-z]{{1,4}})?#\d+",
            r"\bwe\s+no\s+longer\b",
            r"\bno\s+longer\s+(?:needed|used|required|necessary|supported|called)\b",
            rf"\bthe\s+old\s+(?:{_CODE_NOUNS})\b",
            r"\bformerly\b",
            r"(?:^|(?<=[.;:]\s))originally,",
            r"\b(?:was|were)\s+originally\b",
        )
    ),
    re.IGNORECASE,
)


def _comment_lines(source: str) -> Iterator[tuple[int, str]]:
    """Yield ``(line, text)`` for every ``#`` comment in ``source``."""
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                yield tok.start[0], tok.string.lstrip("#")
    except (tokenize.TokenError, SyntaxError):
        return


def _docstring_lines(tree: ast.Module) -> Iterator[tuple[int, str]]:
    """Yield ``(line, text)`` for each line of every module, class and function docstring."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        first = node.body[0] if node.body else None
        if not (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            continue
        for offset, text in enumerate(first.value.value.splitlines()):
            yield first.lineno + offset, text


class HistoryNarratingComment(Rule):
    """SMELL-026: Comments and docstrings that narrate the code's change history.

    A pronoun followed by "used to", "since #<issue> it now...", a sentence
    opening with "previously," or "the old" naming an implementation all
    describe a version of the code the reader cannot see. They age into falsehood as the code
    moves on, and they push the one sentence the reader needs, what the code
    does now and why, out of view. History belongs in the commit log and the
    issue tracker; the comment should state the present behaviour.

    Precision over recall: only phrases whose history reading is unambiguous
    are matched, so "the key used to look up a row", "a previously fetched
    page" and "rows that no longer match" do not fire, and a bare issue
    citation ("see #412") is provenance, not narration. Test files are
    skipped: a regression test's comment explaining the bug it pins is the
    point of the test. One finding per line.

    Principles: #11 (The reader is the user), #13 (The system must explain itself).
    Source: MARTIN, *Clean Code* Ch. 4 — Journal Comments; OUSTERHOUT Ch. 13 —
    comments describe what is not obvious from the code, now.
    """

    code = "SMELL-026"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = (
        "Comment narrates change history ('{phrase}') — describe what the code does now"
    )
    recommendation_template = (
        "Rewrite the comment in the present tense: what the code does and why. "
        "Move the history to the commit message or the issue it cites."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            if is_test_path(f.relative_path):
                continue
            findings.extend(self._check_file(f))
        return findings

    def _check_file(self, f: FileInfo) -> list[Finding]:
        lines: list[tuple[int, str]] = list(_comment_lines(f.source))
        if f.ast_tree is not None:
            lines.extend(_docstring_lines(f.ast_tree))
        findings: list[Finding] = []
        for line, text in sorted(lines):
            match = _HISTORY_PHRASES.search(text.strip())
            if match is None:
                continue
            findings.append(
                self.finding(file=f.relative_path, line=line, phrase=match.group(0).strip())
            )
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

DISPENSABLE_RULES = (
    LazyElement(),
    SpeculativeGenerality(),
    Comments(),
    DataClassSmell(),
    TemporalIdentifier(),
    HistoryNarratingComment(),
)
