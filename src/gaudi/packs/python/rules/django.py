# ABOUTME: Django-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers SECRET_KEY exposure and DEBUG mode via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_TEST_PLACEHOLDER_PREFIXES = ("test-", "test_", "test.", "dummy-", "dummy_", "fake-", "fake_")
_TEST_PLACEHOLDER_SUBSTRINGS = ("example", "placeholder", "not-used", "not_used")
_DEV_SETTINGS_MARKERS = ("local", "dev", "development", "testing")


def _is_test_placeholder(value: str) -> bool:
    """Detect SECRET_KEY values that are clearly test placeholders."""
    lowered = value.lower()
    if any(lowered.startswith(prefix) for prefix in _TEST_PLACEHOLDER_PREFIXES):
        return True
    return any(marker in lowered for marker in _TEST_PLACEHOLDER_SUBSTRINGS)


class DjangoSecretKeyExposed(Rule):
    """Detect Django SECRET_KEY hardcoded in settings.

    Principles: #5 (State must be visible), #4 (Failure must be named).
    Source: FWDOCS Django deployment checklist — secrets are configuration, not code.
    """

    code = "DJ-SEC-001"
    severity = Severity.ERROR
    category = Category.SECURITY
    requires_library = "django"
    message_template = "SECRET_KEY appears hardcoded in settings at line {line}"
    recommendation_template = (
        "Load SECRET_KEY from environment variables: SECRET_KEY = os.environ['SECRET_KEY']. "
        "Hardcoded secrets in source control are a critical security vulnerability."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "settings" not in f.relative_path.lower():
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SECRET_KEY":
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            if _is_test_placeholder(node.value.value):
                                continue
                            findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class DjangoDebugTrue(Rule):
    """Detect DEBUG=True in Django settings.

    Principles: #5 (State must be visible), #4 (Failure must be named).
    Source: FWDOCS Django deployment checklist — DEBUG=True is a hostile-input failure mode.
    """

    code = "DJ-SEC-002"
    severity = Severity.ERROR
    category = Category.SECURITY
    requires_library = "django"
    message_template = "DEBUG = True in production settings at line {line}"
    recommendation_template = (
        "Set DEBUG = False in production. Use environment variables to control debug mode."
    )

    @staticmethod
    def _is_dev_settings(path: str) -> bool:
        """Settings files for local/dev/testing are expected to have DEBUG=True."""
        lowered = path.replace("\\", "/").lower()
        return any(marker in lowered for marker in _DEV_SETTINGS_MARKERS)

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "settings" not in f.relative_path.lower():
                continue
            if self._is_dev_settings(f.relative_path):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "DEBUG":
                        if isinstance(node.value, ast.Constant) and node.value.value is True:
                            findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


DJANGO_LIB_RULES = (DjangoSecretKeyExposed(), DjangoDebugTrue())
