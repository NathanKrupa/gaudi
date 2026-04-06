"""
Gaudí JavaScript/TypeScript Language Pack.

Covers Express, Next.js, Prisma, and general JS/TS project architecture.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class JSContext:
    """Structural context for a JavaScript/TypeScript project."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.package_json: dict = {}
        self.has_tsconfig: bool = False
        self.has_prisma: bool = False
        self.has_next_config: bool = False
        self.framework: str = "unknown"  # express, next, react, vue, etc.


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_js_project(path: Path) -> JSContext:
    """Parse a JS/TS project using file scanning and regex (no AST dependency)."""
    root = path if path.is_dir() else path.parent
    ctx = JSContext(root)

    if path.is_file():
        js_files = [path]
    else:
        js_files = sorted(
            f for f in path.rglob("*")
            if f.suffix in {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
            and "node_modules" not in f.parts
            and ".next" not in f.parts
            and "dist" not in f.parts
        )

    # Package.json
    pkg_path = root / "package.json"
    if pkg_path.exists():
        try:
            ctx.package_json = json.loads(pkg_path.read_text())
        except Exception:
            pass

    ctx.has_tsconfig = (root / "tsconfig.json").exists()
    ctx.has_prisma = (root / "prisma").is_dir()
    ctx.has_next_config = any(
        (root / f"next.config.{ext}").exists() for ext in ["js", "mjs", "ts"]
    )

    # Detect framework
    deps = {
        **ctx.package_json.get("dependencies", {}),
        **ctx.package_json.get("devDependencies", {}),
    }
    if "next" in deps:
        ctx.framework = "next"
    elif "express" in deps:
        ctx.framework = "express"
    elif "react" in deps:
        ctx.framework = "react"
    elif "vue" in deps:
        ctx.framework = "vue"

    for f in js_files:
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


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class NoEnvValidation(Rule):
    """JS-SEC-001: Environment variables used without validation."""

    code = "JS-SEC-001"
    severity = Severity.WARN
    category = Category.SECURITY
    message_template = "process.env.{var} used without validation at line {line}"
    recommendation_template = (
        "Validate environment variables at startup using a library like envalid, zod, or "
        "a manual check. Unvalidated env vars cause hard-to-debug runtime failures."
    )

    def check(self, context: JSContext) -> list[Finding]:
        findings = []
        env_pattern = re.compile(r'process\.env\.(\w+)')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                for match in env_pattern.finditer(line):
                    # Skip if it's inside a validation block (rough heuristic)
                    if "||" not in line and "??" not in line and "throw" not in line:
                        findings.append(self.finding(
                            file=f["relative"], line=i, var=match.group(1),
                        ))
        return findings


class ConsoleLogInProd(Rule):
    """JS-STRUCT-001: console.log statements left in source."""

    code = "JS-STRUCT-001"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "console.log found at line {line} — use a structured logger in production"
    recommendation_template = (
        "Replace console.log with a structured logger (winston, pino, bunyan). "
        "Console output is lost in production and lacks log levels."
    )

    def check(self, context: JSContext) -> list[Finding]:
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("console.log(") or stripped.startswith("console.log ("):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings


class NoErrorMiddleware(Rule):
    """JS-ARCH-001: Express app without centralized error handling middleware."""

    code = "JS-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Express app has no centralized error handling middleware"
    recommendation_template = (
        "Add an error handling middleware with (err, req, res, next) signature. "
        "Without it, unhandled errors crash the process or leak stack traces to clients."
    )

    def check(self, context: JSContext) -> list[Finding]:
        if context.framework != "express":
            return []

        has_error_handler = False
        for f in context.files:
            # Look for (err, req, res, next) pattern
            if re.search(r'\(\s*err\s*,\s*req\s*,\s*res\s*,\s*next\s*\)', f["source"]):
                has_error_handler = True
                break

        if not has_error_handler:
            return [self.finding()]
        return []


class PrismaNoIndex(Rule):
    """JS-IDX-001: Prisma model field used in queries without @index."""

    code = "JS-IDX-001"
    severity = Severity.WARN
    category = Category.INDEXING
    message_template = "Prisma model '{model}' has field '{field}' that likely needs an @@index"
    recommendation_template = (
        "Add @@index([{field}]) to the model. Fields named email, slug, status, "
        "or code are commonly queried and should be indexed."
    )

    LOOKUP_FIELDS = {"email", "slug", "status", "code", "username", "sku", "externalId"}

    def check(self, context: JSContext) -> list[Finding]:
        if not context.has_prisma:
            return []

        findings = []
        schema_path = context.root / "prisma" / "schema.prisma"
        if not schema_path.exists():
            return []

        try:
            schema = schema_path.read_text()
        except Exception:
            return []

        # Parse prisma schema for models and indexes
        model_pattern = re.compile(r'model\s+(\w+)\s*\{([^}]+)\}', re.DOTALL)
        for match in model_pattern.finditer(schema):
            model_name = match.group(1)
            body = match.group(2)

            # Find fields
            has_index_for = set()
            if "@@index" in body:
                idx_matches = re.findall(r'@@index\(\[([^\]]+)\]', body)
                for idx in idx_matches:
                    has_index_for.update(f.strip().strip('"') for f in idx.split(","))

            for line in body.splitlines():
                line = line.strip()
                if not line or line.startswith("//") or line.startswith("@@"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    field_name = parts[0]
                    if (
                        field_name.lower() in {f.lower() for f in self.LOOKUP_FIELDS}
                        and field_name not in has_index_for
                        and "@unique" not in line
                        and "@id" not in line
                    ):
                        findings.append(self.finding(model=model_name, field=field_name))

        return findings


class MissingTypeScript(Rule):
    """JS-ARCH-002: JavaScript project without TypeScript."""

    code = "JS-ARCH-002"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "Project uses JavaScript without TypeScript"
    recommendation_template = (
        "Consider migrating to TypeScript. Type safety catches architectural "
        "errors at compile time and improves AI agent code generation accuracy."
    )

    def check(self, context: JSContext) -> list[Finding]:
        if context.has_tsconfig:
            return []

        js_count = sum(1 for f in context.files if f["path"].suffix in {".js", ".jsx", ".mjs"})
        if js_count >= 5:
            return [self.finding()]
        return []


class CatchAllErrorSilencing(Rule):
    """JS-SEC-002: Empty catch blocks silently swallow errors."""

    code = "JS-SEC-002"
    severity = Severity.WARN
    category = Category.SECURITY
    message_template = "Empty catch block at line {line} silently swallows errors"
    recommendation_template = (
        "Log the error, re-throw it, or handle it explicitly. "
        "Silent catch blocks hide bugs and make debugging impossible."
    )

    def check(self, context: JSContext) -> list[Finding]:
        findings = []
        empty_catch = re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}')
        for f in context.files:
            for match in empty_catch.finditer(f["source"]):
                line = f["source"][:match.start()].count("\n") + 1
                findings.append(self.finding(file=f["relative"], line=line))
        return findings


# ---------------------------------------------------------------------------
# Pack
# ---------------------------------------------------------------------------

JS_RULES = [
    NoEnvValidation(),
    ConsoleLogInProd(),
    NoErrorMiddleware(),
    PrismaNoIndex(),
    MissingTypeScript(),
    CatchAllErrorSilencing(),
]


class JavaScriptPack(Pack):
    name = "javascript"
    description = "Express, Next.js, Prisma, React, and general JS/TS architecture"
    extensions = (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")

    def __init__(self) -> None:
        super().__init__()
        for rule in JS_RULES:
            self.register_rule(rule)

    def parse(self, path: Path) -> JSContext:
        return parse_js_project(path)
