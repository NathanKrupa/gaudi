"""Gaudí Swift Language Pack. Covers iOS architecture, Core Data, and SwiftUI patterns."""
from __future__ import annotations
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack

class SwiftContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_xcodeproj: bool = False
        self.has_package_swift: bool = False

def parse_swift_project(path: Path) -> SwiftContext:
    root = path if path.is_dir() else path.parent
    ctx = SwiftContext(root)
    ctx.has_xcodeproj = any(root.glob("*.xcodeproj"))
    ctx.has_package_swift = (root / "Package.swift").exists()
    swift_files = sorted(f for f in (path.rglob("*.swift") if path.is_dir() else [path])
                         if ".build" not in f.parts)
    for f in swift_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({"path": f, "relative": str(f.relative_to(root)),
                              "source": source, "lines": source.count("\n") + 1})
        except Exception:
            pass
    return ctx

class ForceUnwrap(Rule):
    code = "SWIFT-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Force unwrap (!) at line {line} — use guard let or if let"
    recommendation_template = "Force unwraps crash on nil. Use optional binding (guard let, if let) or nil coalescing (??)."
    def check(self, context: SwiftContext) -> list[Finding]:
        findings = []
        pattern = re.compile(r'\w+!')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("//") or "IBOutlet" in line or "IBAction" in line:
                    continue
                if pattern.search(line) and "!" in line and "!=" not in line and "!!" not in line:
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

class MassiveViewController(Rule):
    code = "SWIFT-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "ViewController '{file}' is {lines} lines — extract into MVVM or coordinator"
    recommendation_template = "Use MVVM, VIPER, or Coordinator pattern. ViewControllers over 300 lines are hard to maintain."
    THRESHOLD = 300
    def check(self, context: SwiftContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "ViewController" in f["relative"] and f["lines"] > self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], lines=f["lines"]))
        return findings

class RetainCycle(Rule):
    code = "SWIFT-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "Closure captures self strongly at line {line} — potential retain cycle"
    recommendation_template = "Use [weak self] or [unowned self] in closures to prevent retain cycles and memory leaks."
    def check(self, context: SwiftContext) -> list[Finding]:
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if "{ self." in line or "{self." in line:
                    if "[weak self]" not in line and "[unowned self]" not in line:
                        if "struct " not in f["source"][:f["source"].find(line)]:
                            findings.append(self.finding(file=f["relative"], line=i))
        return findings

SWIFT_RULES = [ForceUnwrap(), MassiveViewController(), RetainCycle()]

class SwiftPack(Pack):
    name = "swift"
    description = "iOS architecture, SwiftUI, Core Data, and Swift idioms"
    extensions = [".swift"]
    def __init__(self) -> None:
        super().__init__()
        for rule in SWIFT_RULES:
            self.register_rule(rule)
    def parse(self, path: Path) -> SwiftContext:
        return parse_swift_project(path)
