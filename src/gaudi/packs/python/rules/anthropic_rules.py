# ABOUTME: Anthropic SDK library rules for Gaudí Python pack.
# ABOUTME: Detects hardcoded models, bare API calls, and missing token counting via AST.
from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext

_LIBRARY = "anthropic"

# Methods on the anthropic client that make API calls
_API_METHODS = frozenset({"create", "stream"})

# Token-counting indicators in source code
_TOKEN_KEYWORDS = frozenset(
    {"count_tokens", "num_tokens", "token_count", "tiktoken", "token_len", "n_tokens"}
)


def _is_anthropic_api_call(node: ast.Call) -> bool:
    """Check if node is client.messages.create() or similar anthropic API call.

    Matches patterns like:
      client.messages.create(...)
      client.completions.create(...)
      self.client.messages.create(...)
    """
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in _API_METHODS:
        return False
    # Must be chained: *.messages.create or *.completions.create
    parent = func.value
    if isinstance(parent, ast.Attribute) and parent.attr in {"messages", "completions"}:
        return True
    return False


def _node_inside_try(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> bool:
    """Walk up from node to see if it sits inside a try body."""
    current = node
    while current in parent_map:
        current = parent_map[current]
        if isinstance(current, ast.Try):
            return True
    return False


def _build_parent_map(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    """Build a child→parent map for the entire AST."""
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


class HardcodedModel(Rule):
    """Detect hardcoded Anthropic model names instead of config injection.

    Principles: #5 (State must be visible), #2 (One concept, one home).
    Source: FWDOCS Anthropic SDK — model selection is configuration, not code.
    """

    code = "LLM-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = _LIBRARY
    message_template = "Hardcoded model name in API call at line {line}"
    recommendation_template = (
        "Extract model names to a configuration constant or environment variable. "
        "Hardcoded model strings make it difficult to update models across the codebase."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import(_LIBRARY):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not _is_anthropic_api_call(node):
                    continue
                for kw in node.keywords:
                    if kw.arg == "model" and isinstance(kw.value, ast.Constant):
                        if isinstance(kw.value.value, str):
                            findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class BareAPICall(Rule):
    """Detect Anthropic API calls without error handling for transient failures.

    Principles: #4 (Failure must be named).
    Source: FWDOCS Anthropic SDK + NYGARD Ch. 5 — every external call states its failures.
    """

    code = "LLM-ERR-001"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    requires_library = _LIBRARY
    message_template = "Anthropic API call without error handling at line {line}"
    recommendation_template = (
        "Wrap anthropic API calls in try/except to handle APIError, RateLimitError, "
        "and APIConnectionError. Bare calls will crash on transient failures."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import(_LIBRARY):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            parent_map = _build_parent_map(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not _is_anthropic_api_call(node):
                    continue
                if not _node_inside_try(node, parent_map):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class NoTokenCounting(Rule):
    """Detect Anthropic API calls without token counting safeguards.

    Principles: #4 (Failure must be named).
    Source: FWDOCS Anthropic SDK — token budgets are explicit failure modes.
    """

    code = "LLM-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    requires_library = _LIBRARY
    message_template = "Anthropic API call without token counting in {file}"
    recommendation_template = (
        "Check prompt token length before making API calls. Without token counting, "
        "oversized prompts will be rejected by the API and waste latency."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import(_LIBRARY):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            has_api_call = False
            api_call_line = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and _is_anthropic_api_call(node):
                    has_api_call = True
                    api_call_line = node.lineno
                    break
            if not has_api_call:
                continue
            # Heuristic: check if source mentions any token-counting pattern
            source_lower = f.source.lower()
            if any(kw in source_lower for kw in _TOKEN_KEYWORDS):
                continue
            findings.append(self.finding(file=f.relative_path, line=api_call_line))
        return findings


ANTHROPIC_RULES = (HardcodedModel(), BareAPICall(), NoTokenCounting())
