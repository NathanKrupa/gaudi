# ABOUTME: Dependency graph rules for module-level coupling analysis.
# ABOUTME: Detects circular imports, fan-out/fan-in problems, and unstable dependencies.
from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import FileInfo, PythonContext

# Minimum project size for graph metrics to be meaningful
_MIN_FILES_FOR_METRICS = 5

# DEP-002 threshold: max internal imports before warning
_FAN_OUT_THRESHOLD = 10

# DEP-003 threshold: fraction of project files that import a module
_FAN_IN_THRESHOLD = 0.8

# DEP-004 threshold: instability above which a depended-on module is flagged
# 0.5 means fan-out >= fan-in: as much outgoing as incoming coupling.
_INSTABILITY_THRESHOLD = 0.5

# DEP-004 threshold: minimum fan-in to be considered "depended on"
_MIN_FAN_IN_FOR_UNSTABLE = 3


def _register_module(rp: str, index: dict[str, str]) -> None:
    """Register a single file's possible import names in the module index."""
    if rp.endswith("__init__.py"):
        pkg = rp.rsplit("/__init__.py", 1)[0].replace("/", ".")
        if pkg:
            index[pkg] = rp
    elif rp.endswith(".py"):
        dotted = rp[:-3].replace("/", ".")
        index[dotted] = rp
        bare = rp.rsplit("/", 1)[-1][:-3]
        if bare not in index:
            index[bare] = rp


def _build_module_index(files: list[FileInfo]) -> dict[str, str]:
    """Map possible import names to relative file paths.

    For 'pkg/utils.py' registers both 'pkg.utils' and 'utils'.
    For 'pkg/__init__.py' registers 'pkg'.
    """
    index: dict[str, str] = {}
    for fi in files:
        rp = fi.relative_path.replace("\\", "/")
        _register_module(rp, index)
    return index


def _resolve_import(imp: str, module_index: dict[str, str]) -> str | None:
    """Resolve an import string to a project-internal relative path.

    Tries exact match first, then prefix matches for sub-imports.
    Returns None for external/stdlib imports.
    """
    if imp in module_index:
        return module_index[imp]
    # Try prefix: 'pkg.mod.Class' might match 'pkg.mod'
    parts = imp.split(".")
    for i in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:i])
        if prefix in module_index:
            return module_index[prefix]
    return None


def _extract_full_imports(fi: FileInfo) -> list[str]:
    """Extract all import targets from a file's AST.

    For 'import foo.bar' -> ['foo.bar']
    For 'from foo import bar' -> ['foo.bar', 'foo']
    For 'from foo.bar import baz' -> ['foo.bar.baz', 'foo.bar']

    Returns both the full dotted path and the base module so resolution
    can match either the submodule or the package.
    """
    tree = fi.ast_tree
    if tree is None:
        return []
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
            for alias in node.names:
                targets.append(f"{node.module}.{alias.name}")
    return targets


def _build_internal_graph(
    files: list[FileInfo], module_index: dict[str, str]
) -> dict[str, set[str]]:
    """Build directed graph: file_path -> set of internal file_paths it imports."""
    graph: dict[str, set[str]] = {}
    for fi in files:
        rp = fi.relative_path.replace("\\", "/")
        deps: set[str] = set()
        for imp in _extract_full_imports(fi):
            target = _resolve_import(imp, module_index)
            if target and target != rp:  # No self-edges
                deps.add(target)
        graph[rp] = deps
    return graph


def _normalize_cycle(cycle: list[str]) -> list[str]:
    """Rotate a cycle to start at its lexicographically smallest node."""
    # cycle ends with a repeat of its start; strip it for rotation logic
    body = cycle[:-1]
    min_idx = body.index(min(body))
    rotated = body[min_idx:] + body[:min_idx]
    return rotated + [rotated[0]]


class _CycleSearch:
    """DFS state for finding elementary cycles in a directed graph."""

    def __init__(self, graph: dict[str, set[str]]) -> None:
        self.graph = graph
        self.cycles: list[list[str]] = []
        self.seen: set[tuple[str, ...]] = set()
        self.visited: set[str] = set()
        self.path: list[str] = []
        self.path_set: set[str] = set()

    def dfs(self, node: str) -> None:
        if node in self.path_set:
            self._record_cycle(node)
            return
        if node in self.visited:
            return
        self.visited.add(node)
        self.path.append(node)
        self.path_set.add(node)
        for neighbor in sorted(self.graph.get(node, set())):
            self.dfs(neighbor)
        self.path.pop()
        self.path_set.discard(node)

    def _record_cycle(self, node: str) -> None:
        cycle_start = self.path.index(node)
        normalized = _normalize_cycle(self.path[cycle_start:] + [node])
        key = tuple(normalized)
        if key not in self.seen:
            self.seen.add(key)
            self.cycles.append(normalized)


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find all elementary cycles in the graph using DFS."""
    search = _CycleSearch(graph)
    for start in sorted(graph):
        search.visited.clear()
        search.dfs(start)
    return search.cycles


def _compute_fan_in(graph: dict[str, set[str]]) -> dict[str, int]:
    """Count how many modules import each module."""
    fan_in: dict[str, int] = {}
    for deps in graph.values():
        for dep in deps:
            fan_in[dep] = fan_in.get(dep, 0) + 1
    return fan_in


def _compute_fan_out(graph: dict[str, set[str]]) -> dict[str, int]:
    """Count how many internal modules each module imports."""
    return {node: len(deps) for node, deps in graph.items()}


# ---------------------------------------------------------------
# DEP-001  CircularImport
# Martin, Clean Architecture: Acyclic Dependencies Principle
# ---------------------------------------------------------------


class CircularImport(Rule):
    code = "DEP-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Circular import cycle: {cycle}"
    recommendation_template = (
        "Break the cycle by extracting shared code into a separate module,"
        " using dependency inversion, or deferring imports."
        " Circular imports cause ImportError at runtime in Python."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        module_index = _build_module_index(context.files)
        graph = _build_internal_graph(context.files, module_index)
        cycles = _find_cycles(graph)

        findings: list[Finding] = []
        for cycle in cycles:
            cycle_str = " -> ".join(cycle)
            findings.append(
                self.finding(
                    file=cycle[0],
                    cycle=cycle_str,
                )
            )
        return findings


# ---------------------------------------------------------------
# DEP-002  FanOutExplosion
# Martin, Clean Architecture: component coupling metrics
# ---------------------------------------------------------------


class FanOutExplosion(Rule):
    code = "DEP-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Module '{file}' imports {count} internal modules (threshold: {threshold})"
    recommendation_template = (
        "Split this module into smaller, focused modules."
        " High fan-out means a module has too many responsibilities"
        " and is fragile to changes in any dependency."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        module_index = _build_module_index(context.files)
        graph = _build_internal_graph(context.files, module_index)
        fan_out = _compute_fan_out(graph)

        findings: list[Finding] = []
        for node, count in sorted(fan_out.items()):
            if count >= _FAN_OUT_THRESHOLD:
                findings.append(
                    self.finding(
                        file=node,
                        count=count,
                        threshold=_FAN_OUT_THRESHOLD,
                    )
                )
        return findings


# ---------------------------------------------------------------
# DEP-003  FanInConcentration
# Martin, Clean Architecture: fragile hub detection
# ---------------------------------------------------------------


class FanInConcentration(Rule):
    code = "DEP-003"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = (
        "Module '{file}' is imported by {count}/{total} project modules"
        " ({pct}% — threshold: {threshold}%)"
    )
    recommendation_template = (
        "Consider whether this module is doing too much."
        " A module imported everywhere becomes a fragile hub —"
        " any change risks breaking the entire project."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        files = context.files
        total = len(files)
        if total < _MIN_FILES_FOR_METRICS:
            return []

        module_index = _build_module_index(files)
        graph = _build_internal_graph(files, module_index)
        fan_in = _compute_fan_in(graph)

        findings: list[Finding] = []
        for node, count in sorted(fan_in.items()):
            ratio = count / total
            if ratio >= _FAN_IN_THRESHOLD:
                findings.append(
                    self.finding(
                        file=node,
                        count=count,
                        total=total,
                        pct=int(ratio * 100),
                        threshold=int(_FAN_IN_THRESHOLD * 100),
                    )
                )
        return findings


# ---------------------------------------------------------------
# DEP-004  UnstableDependency
# Martin, Clean Architecture: Stable Dependencies Principle
# Instability I = fan_out / (fan_in + fan_out)
# Flag: high instability AND high fan-in (depended on but volatile)
# ---------------------------------------------------------------


class UnstableDependency(Rule):
    code = "DEP-004"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "Module '{file}' is unstable (I={instability:.2f}) but depended on by {fan_in} modules"
    )
    recommendation_template = (
        "Stabilize this module by reducing its outgoing dependencies,"
        " or depend on an abstraction instead."
        " Per the Stable Dependencies Principle, modules that others depend on"
        " should be stable (low instability)."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        if len(context.files) < _MIN_FILES_FOR_METRICS:
            return []

        module_index = _build_module_index(context.files)
        graph = _build_internal_graph(context.files, module_index)
        fan_in = _compute_fan_in(graph)
        fan_out = _compute_fan_out(graph)

        findings: list[Finding] = []
        for node in sorted(graph):
            fi = fan_in.get(node, 0)
            fo = fan_out.get(node, 0)
            if fi + fo == 0:
                continue
            instability = fo / (fi + fo)
            if instability >= _INSTABILITY_THRESHOLD and fi >= _MIN_FAN_IN_FOR_UNSTABLE:
                findings.append(
                    self.finding(
                        file=node,
                        instability=instability,
                        fan_in=fi,
                    )
                )
        return findings


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

DEPENDENCY_RULES = (
    CircularImport(),
    FanOutExplosion(),
    FanInConcentration(),
    UnstableDependency(),
)
