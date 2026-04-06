"""
Gaudí Go Language Pack.

Covers error handling patterns, interface design, package structure,
and common Go architectural anti-patterns.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack


class GoContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_go_mod: bool = False
        self.module_name: str = ""


def parse_go_project(path: Path) -> GoContext:
    root = path if path.is_dir() else path.parent
    ctx = GoContext(root)

    go_mod = root / "go.mod"
    if go_mod.exists():
        ctx.has_go_mod = True
        try:
            content = go_mod.read_text()
            match = re.search(r'^module\s+(.+)$', content, re.MULTILINE)
            if match:
                ctx.module_name = match.group(1).strip()
        except Exception:
            pass

    if path.is_file():
        go_files = [path]
    else:
        go_files = sorted(
            f for f in path.rglob("*.go")
            if "vendor" not in f.parts and "testdata" not in f.parts
        )

    for f in go_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({
                "path": f,
                "relative": str(f.relative_to(root)),
                "source": source,
                "lines": source.count("\n") + 1,
            })
        except Exception:
            pass

    return ctx


class IgnoredError(Rule):
    """GO-ARCH-001: Error return value ignored."""

    code = "GO-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Error return value likely ignored at line {line}"
    recommendation_template = (
        "Always check error return values. Use 'if err != nil' pattern. "
        "Ignored errors cause silent failures that are extremely hard to debug."
    )

    def check(self, context: GoContext) -> list[Finding]:
        findings = []
        # Pattern: assignment with _ for error position
        ignore_pattern = re.compile(r'^\s*\w+\s*,\s*_\s*:?=\s*\w+')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if ignore_pattern.match(line) and "_" in line.split(":=")[0].split("=")[0]:
                    # Check it's not a legitimate blank identifier use (like range)
                    if "range" not in line:
                        findings.append(self.finding(file=f["relative"], line=i))
        return findings


class PanicInLibrary(Rule):
    """GO-ARCH-002: panic() used outside of main package."""

    code = "GO-ARCH-002"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "panic() call in library code at line {line}"
    recommendation_template = (
        "Return errors instead of panicking in library code. "
        "panic() should only be used for truly unrecoverable situations in main."
    )

    def check(self, context: GoContext) -> list[Finding]:
        findings = []
        for f in context.files:
            # Skip main package files and test files
            if "_test.go" in f["relative"]:
                continue

            is_main = False
            for line in f["source"].splitlines()[:5]:
                if line.strip().startswith("package main"):
                    is_main = True
                    break

            if is_main:
                continue

            for i, line in enumerate(f["source"].splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("panic(") or "\tpanic(" in line or " panic(" in line:
                    if not stripped.startswith("//"):
                        findings.append(self.finding(file=f["relative"], line=i))
        return findings


class InitFunctionAbuse(Rule):
    """GO-STRUCT-001: init() function with side effects."""

    code = "GO-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "init() function found in {file} — init functions make testing and dependency management harder"
    recommendation_template = (
        "Prefer explicit initialization over init(). init() functions run implicitly "
        "on import, making code harder to test and reason about."
    )

    def check(self, context: GoContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if re.search(r'^func\s+init\s*\(\s*\)', f["source"], re.MULTILINE):
                findings.append(self.finding(file=f["relative"]))
        return findings


class GodStruct(Rule):
    """GO-ARCH-003: Struct with too many fields."""

    code = "GO-ARCH-003"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Struct '{name}' has {count} fields — consider splitting"
    recommendation_template = (
        "Structs with more than 10 fields often contain multiple concerns. "
        "Consider embedding smaller structs or using composition."
    )

    THRESHOLD = 10

    def check(self, context: GoContext) -> list[Finding]:
        findings = []
        struct_pattern = re.compile(r'type\s+(\w+)\s+struct\s*\{([^}]+)\}', re.DOTALL)
        for f in context.files:
            for match in struct_pattern.finditer(f["source"]):
                name = match.group(1)
                body = match.group(2)
                field_count = sum(
                    1 for line in body.splitlines()
                    if line.strip() and not line.strip().startswith("//")
                )
                if field_count > self.THRESHOLD:
                    line = f["source"][:match.start()].count("\n") + 1
                    findings.append(self.finding(
                        file=f["relative"], line=line, name=name, count=field_count,
                    ))
        return findings


class ContextNotFirstParam(Rule):
    """GO-ARCH-004: Context should be the first parameter of functions."""

    code = "GO-ARCH-004"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "Function '{func}' takes context.Context but not as the first parameter"
    recommendation_template = (
        "By Go convention, context.Context should always be the first parameter "
        "and named 'ctx'. See https://go.dev/blog/context"
    )

    def check(self, context: GoContext) -> list[Finding]:
        findings = []
        func_pattern = re.compile(r'func\s+(?:\([^)]+\)\s+)?(\w+)\(([^)]+)\)')
        for f in context.files:
            for match in func_pattern.finditer(f["source"]):
                func_name = match.group(1)
                params = match.group(2)
                param_list = [p.strip() for p in params.split(",")]
                # Check if any non-first param is context.Context
                for i, param in enumerate(param_list):
                    if i > 0 and ("context.Context" in param or "ctx " in param.split()[0] if param.split() else False):
                        line = f["source"][:match.start()].count("\n") + 1
                        findings.append(self.finding(
                            file=f["relative"], line=line, func=func_name,
                        ))
        return findings


GO_RULES = [IgnoredError(), PanicInLibrary(), InitFunctionAbuse(), GodStruct(), ContextNotFirstParam()]


class GoPack(Pack):
    name = "go"
    description = "Error handling, interface design, package structure, and Go idioms"
    extensions = [".go"]

    def __init__(self) -> None:
        super().__init__()
        for rule in GO_RULES:
            self.register_rule(rule)

    def parse(self, path: Path) -> GoContext:
        return parse_go_project(path)
