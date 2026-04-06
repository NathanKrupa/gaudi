"""
Gaudí Java Language Pack.

Covers Spring Boot, Hibernate/JPA, JDBC patterns, and general Java architecture.
"""

from __future__ import annotations
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack


class JavaContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_pom: bool = False
        self.has_gradle: bool = False
        self.framework: str = "unknown"


def parse_java_project(path: Path) -> JavaContext:
    root = path if path.is_dir() else path.parent
    ctx = JavaContext(root)
    ctx.has_pom = (root / "pom.xml").exists()
    ctx.has_gradle = (root / "build.gradle").exists() or (root / "build.gradle.kts").exists()

    java_files = sorted(f for f in (path.rglob("*.java") if path.is_dir() else [path])
                        if "target" not in f.parts and "build" not in f.parts)

    for f in java_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({"path": f, "relative": str(f.relative_to(root)),
                              "source": source, "lines": source.count("\n") + 1})
            if "@SpringBootApplication" in source or "@RestController" in source:
                ctx.framework = "spring"
        except Exception:
            pass
    return ctx


class CatchGenericException(Rule):
    code = "JAVA-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Catching generic Exception at line {line} — catch specific exceptions"
    recommendation_template = "Catch specific exception types. Generic catch blocks hide bugs and make error handling ambiguous."

    def check(self, context: JavaContext) -> list[Finding]:
        findings = []
        pattern = re.compile(r'catch\s*\(\s*Exception\s+')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if pattern.search(line) and not line.strip().startswith("//"):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings


class GodClass(Rule):
    code = "JAVA-ARCH-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Class in '{file}' is {lines} lines — likely violates Single Responsibility"
    recommendation_template = "Split into focused classes. Classes over 500 lines typically handle multiple concerns."
    THRESHOLD = 500

    def check(self, context: JavaContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if f["lines"] > self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], lines=f["lines"]))
        return findings


class FieldInjection(Rule):
    code = "JAVA-ARCH-003"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "@Autowired field injection at line {line} — use constructor injection"
    recommendation_template = ("Use constructor injection instead of @Autowired on fields. "
                               "Field injection makes dependencies invisible, prevents immutability, and complicates testing.")

    def check(self, context: JavaContext) -> list[Finding]:
        if context.framework != "spring":
            return []
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if "@Autowired" in line and "private" in f["source"].splitlines()[i] if i < f["lines"] else False:
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings


class MissingTransactional(Rule):
    code = "JAVA-ARCH-004"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "Service class '{file}' has no @Transactional annotations"
    recommendation_template = "Spring service classes with repository calls should use @Transactional for data consistency."

    def check(self, context: JavaContext) -> list[Finding]:
        if context.framework != "spring":
            return []
        findings = []
        for f in context.files:
            if "@Service" in f["source"] and "@Transactional" not in f["source"]:
                if "Repository" in f["source"] or "repository" in f["source"]:
                    findings.append(self.finding(file=f["relative"]))
        return findings


class NPlusOneQuery(Rule):
    code = "JAVA-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "Potential N+1 query: FetchType.LAZY with loop access in '{file}'"
    recommendation_template = "Use JOIN FETCH, @EntityGraph, or batch fetching to avoid N+1 queries."

    def check(self, context: JavaContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "FetchType.LAZY" in f["source"] and ("for (" in f["source"] or "forEach" in f["source"]):
                if ".get" in f["source"] and ("List<" in f["source"] or "Set<" in f["source"]):
                    findings.append(self.finding(file=f["relative"]))
        return findings


JAVA_RULES = [CatchGenericException(), GodClass(), FieldInjection(), MissingTransactional(), NPlusOneQuery()]


class JavaPack(Pack):
    name = "java"
    description = "Spring Boot, Hibernate/JPA, and general Java architecture"
    extensions = (".java",)

    def __init__(self) -> None:
        super().__init__()
        for rule in JAVA_RULES:
            self.register_rule(rule)

    def parse(self, path: Path) -> JavaContext:
        return parse_java_project(path)
