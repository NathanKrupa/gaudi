"""Gaudí C# Language Pack. Covers .NET, Entity Framework, ASP.NET patterns."""
from __future__ import annotations
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack

class CSharpContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_csproj: bool = False
        self.has_ef: bool = False

def parse_csharp_project(path: Path) -> CSharpContext:
    root = path if path.is_dir() else path.parent
    ctx = CSharpContext(root)
    ctx.has_csproj = any(root.rglob("*.csproj"))
    cs_files = sorted(f for f in (path.rglob("*.cs") if path.is_dir() else [path])
                      if "bin" not in f.parts and "obj" not in f.parts)
    for f in cs_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({"path": f, "relative": str(f.relative_to(root)),
                              "source": source, "lines": source.count("\n") + 1})
            if "DbContext" in source or "EntityFramework" in source:
                ctx.has_ef = True
        except Exception:
            pass
    return ctx

class AsyncVoidMethod(Rule):
    code = "CS-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "async void method at line {line} — exceptions cannot be caught"
    recommendation_template = "Use async Task instead of async void. async void is only for event handlers."
    def check(self, context: CSharpContext) -> list[Finding]:
        findings = []
        pattern = re.compile(r'\basync\s+void\s+\w+')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if pattern.search(line) and "EventHandler" not in line and not line.strip().startswith("//"):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

class DisposableNotDisposed(Rule):
    code = "CS-ARCH-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "IDisposable created without using statement at line {line}"
    recommendation_template = "Wrap IDisposable objects in 'using' statements or implement IAsyncDisposable pattern."
    def check(self, context: CSharpContext) -> list[Finding]:
        findings = []
        new_pattern = re.compile(r'=\s*new\s+(HttpClient|SqlConnection|StreamReader|StreamWriter|FileStream)\s*\(')
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if new_pattern.search(line) and "using" not in line:
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

class EFNoAsNoTracking(Rule):
    code = "CS-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    message_template = "EF query without AsNoTracking in read-only context at line {line}"
    recommendation_template = "Use .AsNoTracking() for read-only queries to reduce memory and improve performance."
    def check(self, context: CSharpContext) -> list[Finding]:
        if not context.has_ef:
            return []
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if ".ToList()" in line or ".ToListAsync()" in line:
                    if "AsNoTracking" not in f["source"][max(0, f["source"].rfind("\n", 0, f["source"].find(line)) - 200):f["source"].find(line) + len(line)]:
                        if "Get" in f["relative"] or "Read" in f["relative"] or "List" in f["relative"]:
                            findings.append(self.finding(file=f["relative"], line=i))
        return findings

class CatchExceptionRethrow(Rule):
    code = "CS-ARCH-003"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "'throw ex' at line {line} resets stack trace — use 'throw' instead"
    recommendation_template = "Use 'throw;' to preserve the original stack trace, not 'throw ex;'."
    def check(self, context: CSharpContext) -> list[Finding]:
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                if re.search(r'\bthrow\s+\w+\s*;', line) and "new " not in line:
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

class MagicStrings(Rule):
    code = "CS-STRUCT-001"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "Connection string or config value hardcoded at line {line}"
    recommendation_template = "Use IConfiguration, appsettings.json, or environment variables for configuration values."
    def check(self, context: CSharpContext) -> list[Finding]:
        findings = []
        patterns = [re.compile(r'"Server='), re.compile(r'"Data Source='), re.compile(r'"mongodb://'), re.compile(r'"redis://')]
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                for p in patterns:
                    if p.search(line):
                        findings.append(self.finding(file=f["relative"], line=i))
                        break
        return findings

CS_RULES = [AsyncVoidMethod(), DisposableNotDisposed(), EFNoAsNoTracking(), CatchExceptionRethrow(), MagicStrings()]

class CSharpPack(Pack):
    name = "csharp"
    description = ".NET, Entity Framework, ASP.NET architecture"
    extensions = [".cs"]
    def __init__(self) -> None:
        super().__init__()
        for rule in CS_RULES:
            self.register_rule(rule)
    def parse(self, path: Path) -> CSharpContext:
        return parse_csharp_project(path)
