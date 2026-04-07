# ABOUTME: Logging hygiene rules for structured log output.
# ABOUTME: Detects f-string usage in logger calls where %-formatting is preferred.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# LOG-001  UnstructuredLogging
# ---------------------------------------------------------------

_LOG_METHODS = frozenset(
    {
        "info",
        "warning",
        "debug",
        "error",
    }
)


class UnstructuredLogging(Rule):
    code = "LOG-001"
    severity = Severity.INFO
    category = Category.LOGGING
    message_template = "f-string in logger call at line {line} — use %-formatting"
    recommendation_template = (
        "Use logger.info('message %s', var) instead of"
        " logger.info(f'message {{var}}'). Lazy formatting"
        " avoids string construction when log level"
        " is disabled."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in _LOG_METHODS:
                    continue
                if not node.args:
                    continue
                if isinstance(node.args[0], ast.JoinedStr):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

LOGGING_RULES = (UnstructuredLogging(),)
