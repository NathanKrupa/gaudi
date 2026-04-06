"""Gaudí C/C++ Language Pack. Covers memory management, header structure, and safety patterns."""
from __future__ import annotations
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack

class CppContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_cmake: bool = False

def parse_cpp_project(path: Path) -> CppContext:
    root = path if path.is_dir() else path.parent
    ctx = CppContext(root)
    ctx.has_cmake = (root / "CMakeLists.txt").exists()
    exts = {".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx"}
    cpp_files = sorted(f for f in (path.rglob("*") if path.is_dir() else [path])
                       if f.suffix in exts and "build" not in f.parts and "third_party" not in f.parts)
    for f in cpp_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({"path": f, "relative": str(f.relative_to(root)),
                              "source": source, "lines": source.count("\n") + 1})
        except Exception:
            pass
    return ctx

class RawNewDelete(Rule):
    code = "CPP-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Raw new/delete at line {line} — use smart pointers"
    recommendation_template = "Use std::unique_ptr or std::shared_ptr instead of raw new/delete to prevent memory leaks."
    def check(self, context: CppContext) -> list[Finding]:
        findings = []
        pattern = re.compile(r'\bnew\s+\w+|delete\s+\w+|delete\[\]')
        for f in context.files:
            if f["path"].suffix not in {".cpp", ".cc", ".cxx", ".c"}:
                continue
            for i, line in enumerate(f["source"].splitlines(), 1):
                if pattern.search(line) and not line.strip().startswith("//"):
                    if "unique_ptr" not in line and "shared_ptr" not in line and "make_unique" not in line:
                        findings.append(self.finding(file=f["relative"], line=i))
        return findings

class MissingHeaderGuard(Rule):
    code = "CPP-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Header '{file}' has no include guard or #pragma once"
    recommendation_template = "Add #pragma once or #ifndef/#define/#endif include guard to prevent multiple inclusion."
    def check(self, context: CppContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if f["path"].suffix not in {".h", ".hpp", ".hxx"}:
                continue
            has_pragma = "#pragma once" in f["source"]
            has_ifndef = "#ifndef" in f["source"] and "#define" in f["source"]
            if not has_pragma and not has_ifndef:
                findings.append(self.finding(file=f["relative"]))
        return findings

class UnsafeFunctions(Rule):
    code = "CPP-SEC-001"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "Unsafe function '{func}' at line {line} — use safe alternative"
    recommendation_template = "Replace {func} with its safe alternative: {safe}"
    UNSAFE = {"strcpy": "strncpy or std::string", "strcat": "strncat or std::string",
              "sprintf": "snprintf", "gets": "fgets", "scanf": "fgets+sscanf",
              "vsprintf": "vsnprintf", "strcmp": "strncmp (with length check)"}
    def check(self, context: CppContext) -> list[Finding]:
        findings = []
        for f in context.files:
            for i, line in enumerate(f["source"].splitlines(), 1):
                for func, safe in self.UNSAFE.items():
                    if re.search(rf'\b{func}\s*\(', line) and not line.strip().startswith("//"):
                        findings.append(self.finding(file=f["relative"], line=i, func=func, safe=safe))
                        break
        return findings

class GodFile(Rule):
    code = "CPP-STRUCT-002"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "File '{file}' is {lines} lines — split into focused translation units"
    recommendation_template = "Files over 1000 lines should be split. Each .cpp/.h pair should cover one cohesive concept."
    THRESHOLD = 1000
    def check(self, context: CppContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if f["lines"] > self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], lines=f["lines"]))
        return findings

class GlobalMutableState(Rule):
    code = "CPP-ARCH-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Global mutable variable at line {line} — avoid shared mutable state"
    recommendation_template = "Use function-local statics, dependency injection, or const globals instead of mutable globals."
    def check(self, context: CppContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if f["path"].suffix not in {".cpp", ".cc", ".cxx", ".c"}:
                continue
            in_function = False
            for i, line in enumerate(f["source"].splitlines(), 1):
                if re.match(r'^\w+.*\{', line) and "(" in line:
                    in_function = True
                if line.strip() == "}" and in_function:
                    in_function = False
                if not in_function and not line.strip().startswith("//") and not line.strip().startswith("#"):
                    if re.match(r'^(static\s+)?(?!const\s)(int|float|double|char|std::string|bool|auto)\s+\w+', line.strip()):
                        findings.append(self.finding(file=f["relative"], line=i))
        return findings

CPP_RULES = [RawNewDelete(), MissingHeaderGuard(), UnsafeFunctions(), GodFile(), GlobalMutableState()]

class CppPack(Pack):
    name = "cpp"
    description = "Memory management, header structure, safety patterns, and C/C++ idioms"
    extensions = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")
    def __init__(self) -> None:
        super().__init__()
        for rule in CPP_RULES:
            self.register_rule(rule)
    def parse(self, path: Path) -> CppContext:
        return parse_cpp_project(path)
