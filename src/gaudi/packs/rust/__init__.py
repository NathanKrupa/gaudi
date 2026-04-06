"""
Gaudí Rust Language Pack.

Covers module organization, error handling, trait design,
unsafe usage, and common Rust architectural anti-patterns.
"""

from __future__ import annotations

import re
from pathlib import Path

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack


class RustContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_cargo_toml: bool = False
        self.is_workspace: bool = False


def parse_rust_project(path: Path) -> RustContext:
    root = path if path.is_dir() else path.parent
    ctx = RustContext(root)

    cargo = root / "Cargo.toml"
    if cargo.exists():
        ctx.has_cargo_toml = True
        try:
            content = cargo.read_text()
            ctx.is_workspace = "[workspace]" in content
        except Exception:
            pass

    if path.is_file():
        rs_files = [path]
    else:
        rs_files = sorted(
            f for f in path.rglob("*.rs")
            if "target" not in f.parts
        )

    for f in rs_files:
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


class UnsafeWithoutComment(Rule):
    code = "RS-SEC-001"
    severity = Severity.WARN
    category = Category.SECURITY
    message_template = "unsafe block at line {line} without a SAFETY comment"
    recommendation_template = (
        "Add a // SAFETY: comment above every unsafe block explaining why "
        "the invariants are upheld. This is a Rust community convention."
    )

    def check(self, context: RustContext) -> list[Finding]:
        findings = []
        for f in context.files:
            lines = f["source"].splitlines()
            for i, line in enumerate(lines):
                if re.search(r'\bunsafe\s*\{', line):
                    # Check previous line for SAFETY comment
                    prev = lines[i - 1].strip() if i > 0 else ""
                    if "SAFETY" not in prev and "safety" not in prev:
                        findings.append(self.finding(file=f["relative"], line=i + 1))
        return findings


class UnwrapInLibrary(Rule):
    code = "RS-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = ".unwrap() call in library code at line {line}"
    recommendation_template = (
        "Use the ? operator or .expect() with a meaningful message instead of .unwrap(). "
        "unwrap() panics on None/Err and should be avoided in library code."
    )

    def check(self, context: RustContext) -> list[Finding]:
        findings = []
        for f in context.files:
            # Skip test modules and main.rs
            if f["relative"].endswith("main.rs") or "#[cfg(test)]" in f["source"]:
                continue
            for i, line in enumerate(f["source"].splitlines(), 1):
                if ".unwrap()" in line and not line.strip().startswith("//"):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings


class CloneOveruse(Rule):
    code = "RS-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    message_template = "File '{file}' has {count} .clone() calls — review ownership patterns"
    recommendation_template = (
        "Excessive .clone() calls may indicate ownership design issues. "
        "Consider using references, Rc/Arc, or restructuring data flow."
    )

    THRESHOLD = 10

    def check(self, context: RustContext) -> list[Finding]:
        findings = []
        for f in context.files:
            count = f["source"].count(".clone()")
            if count >= self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], count=count))
        return findings


class StringErrorType(Rule):
    code = "RS-ARCH-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Result<_, String> used as error type at line {line}"
    recommendation_template = (
        "Define a proper error enum or use thiserror/anyhow instead of String errors. "
        "String errors lose type information and can't be matched on."
    )

    def check(self, context: RustContext) -> list[Finding]:
        findings = []
        pattern = re.compile(r'Result\s*<[^>]*,\s*String\s*>')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if pattern.search(line) and not line.strip().startswith("//"):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings


class GodModule(Rule):
    code = "RS-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "File '{file}' is {lines} lines long — consider splitting into submodules"
    recommendation_template = (
        "Files over 500 lines often contain multiple concerns. "
        "Split into a module directory with focused submodules."
    )

    THRESHOLD = 500

    def check(self, context: RustContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if f["lines"] > self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], lines=f["lines"]))
        return findings


RS_RULES = [UnsafeWithoutComment(), UnwrapInLibrary(), CloneOveruse(), StringErrorType(), GodModule()]


class RustPack(Pack):
    name = "rust"
    description = "Module organization, error handling, unsafe usage, and Rust idioms"
    extensions = [".rs"]

    def __init__(self) -> None:
        super().__init__()
        for rule in RS_RULES:
            self.register_rule(rule)

    def parse(self, path: Path) -> RustContext:
        return parse_rust_project(path)
