# ABOUTME: boto3 library rules for Gaudi Python pack.
# ABOUTME: Covers hardcoded regions, bare client calls, and unpaginated list operations.
from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext

_BOTO3_CONSTRUCTORS = frozenset({"client", "resource", "Session"})

_PAGINATED_PREFIXES = ("list_", "describe_", "get_log_events", "scan")


def _is_boto3_call(node: ast.Call) -> bool:
    """Check if node is boto3.client/resource/Session(...)."""
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in _BOTO3_CONSTRUCTORS
        and isinstance(func.value, ast.Name)
        and func.value.id == "boto3"
    )


def _find_boto3_client_names(tree: ast.Module) -> set[str]:
    """Find variable names assigned from boto3.client() or boto3.resource()."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not _is_boto3_call(node.value):
            continue
        func = node.value.func
        if isinstance(func, ast.Attribute) and func.attr in ("client", "resource"):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _is_inside_try(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> bool:
    """Check if a node is inside a Try body (has exception handling)."""
    current = node
    while current in parent_map:
        parent = parent_map[current]
        if isinstance(parent, ast.Try):
            if current in parent.body:
                return True
        current = parent
    return False


def _build_parent_map(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    """Build a child-to-parent map for the AST."""
    parent_map: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_map[child] = node
    return parent_map


class HardcodedRegion(Rule):
    """Detect hardcoded AWS region_name passed to boto3 clients.

    Principles: #5 (State must be visible).
    Source: FWDOCS boto3 + AWS Well-Architected — region is configuration.
    """

    code = "AWS-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "boto3"
    message_template = "Hardcoded AWS region_name at line {line}"
    recommendation_template = (
        "Inject region via configuration or environment variable instead of "
        "hardcoding. Hardcoded regions make multi-region deployment impossible."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not _is_boto3_call(node):
                    continue
                for kw in node.keywords:
                    if kw.arg == "region_name" and isinstance(kw.value, ast.Constant):
                        findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class BareClientCall(Rule):
    """Detect boto3 API calls without ClientError handling.

    Principles: #4 (Failure must be named).
    Source: FWDOCS boto3 error handling — every external call states its failures.
    """

    code = "AWS-ERR-001"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    requires_library = "boto3"
    message_template = "boto3 API call without error handling at line {line}"
    recommendation_template = (
        "Wrap boto3 API calls in try/except for botocore.exceptions.ClientError. "
        "AWS calls fail for many reasons (permissions, throttling, network)."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            client_names = _find_boto3_client_names(tree)
            if not client_names:
                continue
            parent_map = _build_parent_map(tree)
            seen_lines: set[int] = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not self._is_client_api_call(node, client_names):
                    continue
                if node.lineno in seen_lines:
                    continue
                if not _is_inside_try(node, parent_map):
                    seen_lines.add(node.lineno)
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings

    @staticmethod
    def _is_client_api_call(node: ast.Call, client_names: set[str]) -> bool:
        """Check if node is a method call on a known boto3 client variable."""
        func = node.func
        if not isinstance(func, ast.Attribute):
            return False
        # Direct: client.put_object(...)
        if isinstance(func.value, ast.Name) and func.value.id in client_names:
            return True
        # Chained: s3.Bucket('x').download_file(...)
        # Only match the outermost call to avoid double-counting.
        if isinstance(func.value, ast.Call):
            inner_func = func.value.func
            if isinstance(inner_func, ast.Attribute) and isinstance(inner_func.value, ast.Name):
                if inner_func.value.id in client_names:
                    return True
        return False


class UnpaginatedList(Rule):
    """Detect AWS list/describe/scan calls without pagination.

    Principles: #4 (Failure must be named).
    Source: FWDOCS boto3 pagination — every result set has a bound.
    """

    code = "AWS-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    requires_library = "boto3"
    message_template = "Unpaginated AWS API call '{method}' at line {line}"
    recommendation_template = (
        "Use client.get_paginator('{method}') instead of calling {method} directly. "
        "Without pagination, results are truncated at AWS default limits."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            client_names = _find_boto3_client_names(tree)
            if not client_names:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Attribute):
                    continue
                func = node.func
                if not isinstance(func.value, ast.Name):
                    continue
                if func.value.id not in client_names:
                    continue
                method = func.attr
                if any(method.startswith(p) for p in _PAGINATED_PREFIXES):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            method=method,
                        )
                    )
        return findings


BOTO3_RULES = (HardcodedRegion(), BareClientCall(), UnpaginatedList())
