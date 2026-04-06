"""Gaudí Kotlin Language Pack. Covers Android, Spring, and Kotlin idioms."""
from __future__ import annotations
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack

class KotlinContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.is_android: bool = False
        self.has_gradle: bool = False

def parse_kotlin_project(path: Path) -> KotlinContext:
    root = path if path.is_dir() else path.parent
    ctx = KotlinContext(root)
    ctx.has_gradle = (root / "build.gradle.kts").exists() or (root / "build.gradle").exists()
    ctx.is_android = (root / "app" / "src" / "main" / "AndroidManifest.xml").exists()
    kt_files = sorted(f for f in (path.rglob("*.kt") if path.is_dir() else [path])
                      if "build" not in f.parts)
    for f in kt_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({"path": f, "relative": str(f.relative_to(root)),
                              "source": source, "lines": source.count("\n") + 1})
        except Exception:
            pass
    return ctx

class ForceNonNull(Rule):
    code = "KT-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Non-null assertion (!!) at line {line} — use safe calls or elvis operator"
    recommendation_template = "Use ?. (safe call), ?: (elvis), or let {} instead of !! to avoid NullPointerException."
    def check(self, context: KotlinContext) -> list[Finding]:
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if "!!" in line and not line.strip().startswith("//"):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

class GodActivity(Rule):
    code = "KT-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Activity/Fragment '{file}' is {lines} lines — use ViewModel and clean architecture"
    recommendation_template = "Move business logic to ViewModel, use cases, and repository layers."
    THRESHOLD = 300
    def check(self, context: KotlinContext) -> list[Finding]:
        if not context.is_android:
            return []
        findings = []
        for f in context.files:
            if ("Activity" in f["relative"] or "Fragment" in f["relative"]) and f["lines"] > self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], lines=f["lines"]))
        return findings

class MutableStateExposed(Rule):
    code = "KT-ARCH-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Mutable state exposed publicly at line {line}"
    recommendation_template = "Expose MutableLiveData/MutableStateFlow as immutable LiveData/StateFlow to prevent external mutation."
    def check(self, context: KotlinContext) -> list[Finding]:
        findings = []
        pattern = re.compile(r'val\s+\w+\s*=\s*MutableLiveData|val\s+\w+\s*=\s*MutableStateFlow')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if pattern.search(line) and "private" not in line and "_" not in line.split("=")[0]:
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

class BlockingOnMain(Rule):
    code = "KT-SCALE-001"
    severity = Severity.ERROR
    category = Category.SCALABILITY
    message_template = "runBlocking used at line {line} — blocks the current thread"
    recommendation_template = "Use coroutine scopes (viewModelScope, lifecycleScope) instead of runBlocking."
    def check(self, context: KotlinContext) -> list[Finding]:
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if "runBlocking" in line and not line.strip().startswith("//") and "test" not in f["relative"].lower():
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

KT_RULES = [ForceNonNull(), GodActivity(), MutableStateExposed(), BlockingOnMain()]

class KotlinPack(Pack):
    name = "kotlin"
    description = "Android, Spring, and Kotlin idioms"
    extensions = (".kt", ".kts")
    def __init__(self) -> None:
        super().__init__()
        for rule in KT_RULES:
            self.register_rule(rule)
    def parse(self, path: Path) -> KotlinContext:
        return parse_kotlin_project(path)
