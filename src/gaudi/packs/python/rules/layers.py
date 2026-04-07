# ABOUTME: Architectural layering rules enforcing import direction and separation.
# ABOUTME: Detects outer-to-inner import violations, connector logic leaks, and fat scripts.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# ARCH-010  ImportDirectionViolation
# ---------------------------------------------------------------

_OUTER_KEYWORDS = ("scripts.", "cli.", "commands.", "views.")


class ImportDirectionViolation(Rule):
    """Detect inner-layer files importing from outer layers (import direction violation).

    Principles: #1 (The structure tells the story), #9 (Dependencies flow toward stability).
    Source: ARCH90 Day 3 — arrows point inward only.
    """

    code = "ARCH-010"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Inner-layer file imports from outer layer: '{imported}' at line {line}"
    recommendation_template = (
        "Import direction should flow inward only."
        " Outer imports middle, middle imports inner."
        " Never reverse."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                mod_name: str | None = None
                lineno = 0
                if isinstance(node, ast.ImportFrom):
                    mod_name = node.module
                    lineno = node.lineno
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(alias.name.startswith(k) for k in _OUTER_KEYWORDS):
                            findings.append(
                                self.finding(
                                    file=fi.relative_path,
                                    line=node.lineno,
                                    imported=alias.name,
                                )
                            )
                    continue
                if mod_name and any(mod_name.startswith(k) for k in _OUTER_KEYWORDS):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=lineno,
                            imported=mod_name,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# ARCH-011  ConnectorLogicLeak
# ---------------------------------------------------------------

_DATA_LAYER_KEYWORDS = ("connector", "store", "repository", "db")


class ConnectorLogicLeak(Rule):
    """Detect data-layer files containing business logic (connector logic leak).

    Principles: #10 (Boundaries are real or fictional).
    Source: ARCH90 Day 3 — connectors translate, services decide.
    """

    code = "ARCH-011"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Business logic (if/elif) in data-layer file '{file}' at line {line}"
    recommendation_template = (
        "Connectors should only talk to external systems."
        " Move decision-making to the service layer."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            path_lower = fi.relative_path.lower()
            is_data_layer = any(kw in path_lower for kw in _DATA_LAYER_KEYWORDS)
            if not is_data_layer:
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for child in ast.walk(node):
                    if isinstance(child, ast.If) and child.orelse:
                        findings.append(
                            self.finding(
                                file=fi.relative_path,
                                line=child.lineno,
                            )
                        )
                        break
        return findings


# ---------------------------------------------------------------
# ARCH-013  FatScript
# ---------------------------------------------------------------


class FatScript(Rule):
    """Detect entry-point functions with too much business logic (fat scripts).

    Principles: #1 (The structure tells the story), #7 (Layers must earn their existence).
    Source: ARCH90 Day 3 — thin entry points, fat services.
    """

    code = "ARCH-013"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Entry point '{function}' has {lines} lines of business logic"
    recommendation_template = (
        "Entry points should be thin — parse input,"
        " call a service, format output."
        " Move logic to service functions."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            source_lines = fi.source.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not self._is_entry_point(node, fi.source):
                    continue
                body_lines = self._count_logic_lines(node, source_lines)
                if body_lines > 15:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                            function=node.name,
                            lines=body_lines,
                        )
                    )
        return findings

    @staticmethod
    def _is_entry_point(func: ast.FunctionDef, source: str) -> bool:
        for dec in func.decorator_list:
            name = ""
            if isinstance(dec, ast.Attribute):
                name = dec.attr
            elif isinstance(dec, ast.Name):
                name = dec.id
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Attribute):
                    name = dec.func.attr
                elif isinstance(dec.func, ast.Name):
                    name = dec.func.id
            if name in ("command", "group"):
                return True
        if "argparse" in source:
            for child in ast.walk(func):
                if isinstance(child, ast.Attribute):
                    if child.attr in (
                        "ArgumentParser",
                        "add_argument",
                        "parse_args",
                    ):
                        return True
        return False

    @staticmethod
    def _count_logic_lines(
        func: ast.FunctionDef,
        source_lines: list[str],
    ) -> int:
        if not func.body:
            return 0
        start = func.body[0].lineno
        end = func.end_lineno or start
        count = 0
        for i in range(start - 1, end):
            if i >= len(source_lines):
                break
            line = source_lines[i].strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith('"""') or line.startswith("'''"):
                continue
            if line.startswith("@"):
                continue
            count += 1
        return count


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

LAYERS_RULES = (
    ImportDirectionViolation(),
    ConnectorLogicLeak(),
    FatScript(),
)
