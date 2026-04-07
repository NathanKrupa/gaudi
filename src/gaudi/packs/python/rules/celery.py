# ABOUTME: Celery-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing retry configuration and time limits on tasks via AST.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_TASK_DECORATORS = frozenset({"task", "shared_task"})


def _has_task_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function has a @task or @shared_task decorator."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id in _TASK_DECORATORS:
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name) and func.id in _TASK_DECORATORS:
                return True
            if isinstance(func, ast.Attribute) and func.attr in _TASK_DECORATORS:
                return True
        if isinstance(dec, ast.Attribute) and dec.attr in _TASK_DECORATORS:
            return True
    return False


def _decorator_has_kwarg(node: ast.FunctionDef | ast.AsyncFunctionDef, *kwarg_names: str) -> bool:
    """Check if any task decorator includes specific keyword arguments."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call):
            if any(kw.arg in kwarg_names for kw in dec.keywords):
                return True
    return False


class CeleryNoRetry(Rule):
    """Detect Celery tasks without retry configuration.

    Principles: #4 (Failure must be named).
    Source: FWDOCS Celery + NYGARD Ch. 5 — retries are how an external call states its failure mode.
    """

    code = "CELERY-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "celery"
    message_template = "Celery task without retry configuration at line {line}"
    recommendation_template = (
        "Add autoretry_for, max_retries, and retry_backoff to tasks that call external services. "
        "Tasks without retry config fail permanently on transient errors."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("celery"):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not _has_task_decorator(node):
                    continue
                if not _decorator_has_kwarg(
                    node, "autoretry_for", "max_retries", "retry", "retry_backoff"
                ):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class CeleryNoTimeLimit(Rule):
    """Detect Celery tasks without time_limit/soft_time_limit.

    Principles: #4 (Failure must be named).
    Source: FWDOCS Celery + NYGARD Ch. 5 — every loop and call has a bound.
    """

    code = "CELERY-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    requires_library = "celery"
    message_template = "Celery task without time limit at line {line}"
    recommendation_template = (
        "Add time_limit and soft_time_limit to prevent runaway tasks from consuming workers."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("celery"):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not _has_task_decorator(node):
                    continue
                if not _decorator_has_kwarg(node, "time_limit", "soft_time_limit"):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


CELERY_RULES = (CeleryNoRetry(), CeleryNoTimeLimit())
