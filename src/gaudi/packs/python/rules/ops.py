# ABOUTME: Operational scaffolding rules for project governance files.
# ABOUTME: Checks for pre-commit config, PR template, CODEOWNERS, and contributing guide.
from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# OPS-002  MissingPrecommit
# ---------------------------------------------------------------


class MissingPrecommit(Rule):
    code = "OPS-002"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no .pre-commit-config.yaml"
    recommendation_template = (
        "Add pre-commit hooks for automated code quality checks before each commit."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        path = context.root / ".pre-commit-config.yaml"
        if not path.exists():
            return [self.finding()]
        return []


# ---------------------------------------------------------------
# OPS-003  MissingPRTemplate
# ---------------------------------------------------------------


class MissingPRTemplate(Rule):
    code = "OPS-003"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no pull request template"
    recommendation_template = (
        "Add .github/PULL_REQUEST_TEMPLATE.md to enforce"
        " consistent PR descriptions with summary, motivation,"
        " and test plan sections."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / ".github" / "PULL_REQUEST_TEMPLATE.md",
            context.root / ".github" / "pull_request_template.md",
            context.root / "PULL_REQUEST_TEMPLATE.md",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-004  MissingCodeowners
# ---------------------------------------------------------------


class MissingCodeowners(Rule):
    code = "OPS-004"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no CODEOWNERS file"
    recommendation_template = (
        "Add .github/CODEOWNERS to assign review responsibility."
        " Without it, PRs have no automatic reviewer assignment."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / ".github" / "CODEOWNERS",
            context.root / "CODEOWNERS",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-005  MissingContribGuide
# ---------------------------------------------------------------


class MissingContribGuide(Rule):
    code = "OPS-005"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no CONTRIBUTING.md"
    recommendation_template = (
        "Add CONTRIBUTING.md documenting the PR workflow, branch naming, and review process."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / "CONTRIBUTING.md",
            context.root / "contributing.md",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

OPS_RULES = (
    MissingPrecommit(),
    MissingPRTemplate(),
    MissingCodeowners(),
    MissingContribGuide(),
)
