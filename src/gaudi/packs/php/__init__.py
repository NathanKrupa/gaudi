"""Gaudí PHP Language Pack. Covers Laravel, Eloquent, and general PHP architecture."""
from __future__ import annotations
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack

class PHPContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_composer: bool = False
        self.framework: str = "unknown"

def parse_php_project(path: Path) -> PHPContext:
    root = path if path.is_dir() else path.parent
    ctx = PHPContext(root)
    ctx.has_composer = (root / "composer.json").exists()
    if (root / "artisan").exists():
        ctx.framework = "laravel"
    php_files = sorted(f for f in (path.rglob("*.php") if path.is_dir() else [path])
                       if "vendor" not in f.parts)
    for f in php_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({"path": f, "relative": str(f.relative_to(root)),
                              "source": source, "lines": source.count("\n") + 1})
        except Exception:
            pass
    return ctx

class SQLInjection(Rule):
    code = "PHP-SEC-001"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "Possible SQL injection: raw variable in query at line {line}"
    recommendation_template = "Use parameterized queries, prepared statements, or Eloquent query builder."
    def check(self, context: PHPContext) -> list[Finding]:
        findings = []
        patterns = [re.compile(r'query\s*\(\s*["\'].*\$'), re.compile(r'DB::raw\s*\(\s*["\'].*\$'),
                    re.compile(r'whereRaw\s*\(\s*["\'].*\$')]
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                for p in patterns:
                    if p.search(line):
                        findings.append(self.finding(file=f["relative"], line=i))
                        break
        return findings

class EloquentNPlusOne(Rule):
    code = "PHP-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "Potential N+1 query: accessing relationship in loop without eager loading in '{file}'"
    recommendation_template = "Use ::with('relationship') for eager loading to prevent N+1 queries."
    def check(self, context: PHPContext) -> list[Finding]:
        if context.framework != "laravel":
            return []
        findings = []
        for f in context.files:
            if "::all()" in f["source"] or "->get()" in f["source"]:
                if "foreach" in f["source"] and "->" in f["source"]:
                    if "::with(" not in f["source"] and "->load(" not in f["source"]:
                        findings.append(self.finding(file=f["relative"]))
        return findings

class GodController(Rule):
    code = "PHP-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Controller '{file}' is {lines} lines — move business logic to services"
    recommendation_template = "Controllers should be thin. Extract business logic into Service or Action classes."
    THRESHOLD = 300
    def check(self, context: PHPContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "Controller" in f["relative"] and f["lines"] > self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], lines=f["lines"]))
        return findings

class EnvInCode(Rule):
    code = "PHP-SEC-002"
    severity = Severity.WARN
    category = Category.SECURITY
    message_template = "env() called outside config files at line {line}"
    recommendation_template = "Only use env() in config files. Use config() helper everywhere else for caching support."
    def check(self, context: PHPContext) -> list[Finding]:
        if context.framework != "laravel":
            return []
        findings = []
        for f in context.files:
            if "/config/" in f["relative"]:
                continue
            for i, line in enumerate(f["source"].splitlines(), 1):
                if "env(" in line and not line.strip().startswith("//"):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

PHP_RULES = [SQLInjection(), EloquentNPlusOne(), GodController(), EnvInCode()]

class PHPPack(Pack):
    name = "php"
    description = "Laravel, Eloquent, and general PHP architecture"
    extensions = [".php"]
    def __init__(self) -> None:
        super().__init__()
        for rule in PHP_RULES:
            self.register_rule(rule)
    def parse(self, path: Path) -> PHPContext:
        return parse_php_project(path)
