# ABOUTME: Fowler "change preventers" code smells: structures that resist modification.
# ABOUTME: Divergent change, shotgun surgery, duplicated code.
from __future__ import annotations

import ast
import copy

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# SMELL-007  DivergentChange
# ---------------------------------------------------------------


def _method_attr_set(
    method: ast.FunctionDef,
) -> set[str]:
    """Collect self.xxx attribute names accessed in a method."""
    attrs: set[str] = set()
    for node in ast.walk(method):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        ):
            attrs.add(node.attr)
    return attrs


class DivergentChange(Rule):
    """SMELL-007: Class methods touch disjoint attribute sets.

    Principles: #2 (One concept, one home), #7 (Layers must earn their existence).
    Source: FOWLER Ch. 3 — Divergent Change.
    """

    code = "SMELL-007"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Class '{class_name}' has methods touching disjoint attribute sets"
    recommendation_template = (
        "Split the class into focused classes, each handling one set of related attributes."
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
                if len(methods) < 4:
                    continue
                non_init = [m for m in methods if m.name != "__init__"]
                attr_sets = [_method_attr_set(m) for m in non_init]
                # Remove empty sets
                attr_sets = [s for s in attr_sets if s]
                if len(attr_sets) < 2:
                    continue
                if self._has_disjoint_groups(attr_sets):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                        )
                    )
        return findings

    def _has_disjoint_groups(
        self,
        attr_sets: list[set[str]],
    ) -> bool:
        """Check if there are 2+ groups sharing zero attrs."""
        # Union-find via simple clustering
        groups: list[set[str]] = []
        for s in attr_sets:
            merged = False
            for g in groups:
                if g & s:
                    g |= s
                    merged = True
                    break
            if not merged:
                groups.append(set(s))
        # Merge groups that now overlap after additions
        changed = True
        while changed:
            changed = False
            new_groups: list[set[str]] = []
            for g in groups:
                placed = False
                for ng in new_groups:
                    if ng & g:
                        ng |= g
                        placed = True
                        changed = True
                        break
                if not placed:
                    new_groups.append(g)
            groups = new_groups
        return len(groups) >= 2


# ---------------------------------------------------------------
# SMELL-008  ShotgunSurgery
# ---------------------------------------------------------------


class ShotgunSurgery(Rule):
    """SMELL-008: Module-level name used in 4+ functions.

    Principles: #2 (One concept, one home).
    Source: FOWLER Ch. 3 — Shotgun Surgery.
    """

    code = "SMELL-008"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = (
        "'{name}' is referenced in {count} functions — changing it requires shotgun surgery"
    )
    recommendation_template = (
        "Centralize usage behind a single function or class to reduce the blast radius of changes."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            # Find module-level names
            module_names: set[str] = set()
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            module_names.add(t.id)
            if not module_names:
                continue
            # Count references per function
            funcs = [
                n
                for n in tree.body
                if isinstance(
                    n,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                )
            ]
            name_users: dict[str, int] = {}
            for fn in funcs:
                used_in_fn: set[str] = set()
                for node in ast.walk(fn):
                    if isinstance(node, ast.Name) and node.id in module_names:
                        used_in_fn.add(node.id)
                for name in used_in_fn:
                    name_users[name] = name_users.get(name, 0) + 1
            for name, count in name_users.items():
                if count >= 4:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=1,
                            name=name,
                            count=count,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-002  DuplicatedCode
# ---------------------------------------------------------------


class _Normalizer(ast.NodeTransformer):
    """Replace all names with placeholders for comparison."""

    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = "VAR"
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = "ARG"
        return node


class DuplicatedCode(Rule):
    """SMELL-002: Functions with identical normalized structure.

    Principles: #2 (One concept, one home).
    Source: FOWLER Ch. 3 — Duplicated Code.
    """

    code = "SMELL-002"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Functions '{func1}' and '{func2}' have duplicate structure"
    recommendation_template = (
        "Extract the shared logic into a single function parameterized by the differences."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            # Normalize and dump each function
            dumps: list[tuple[str, str]] = []
            for fn in funcs:
                fn_copy = copy.deepcopy(fn)
                fn_copy.name = "FUNC"
                _Normalizer().visit(fn_copy)
                dumps.append((fn.name, ast.dump(fn_copy)))
            seen_pairs: set[frozenset[str]] = set()
            for i in range(len(dumps)):
                for j in range(i + 1, len(dumps)):
                    if dumps[i][1] == dumps[j][1]:
                        pair = frozenset({dumps[i][0], dumps[j][0]})
                        if pair not in seen_pairs:
                            seen_pairs.add(pair)
                            names = sorted(pair)
                            findings.append(
                                self.finding(
                                    file=f.relative_path,
                                    line=1,
                                    func1=names[0],
                                    func2=names[1],
                                )
                            )
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

CHANGE_PREVENTER_RULES = (
    DivergentChange(),
    ShotgunSurgery(),
    DuplicatedCode(),
)
