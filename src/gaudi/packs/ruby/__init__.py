"""Gaudí Ruby Language Pack. Covers Rails, ActiveRecord, and general Ruby architecture."""
from __future__ import annotations
import re
from pathlib import Path
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.pack import Pack

class RubyContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: list[dict] = []
        self.has_gemfile: bool = False
        self.is_rails: bool = False

def parse_ruby_project(path: Path) -> RubyContext:
    root = path if path.is_dir() else path.parent
    ctx = RubyContext(root)
    ctx.has_gemfile = (root / "Gemfile").exists()
    ctx.is_rails = (root / "config" / "routes.rb").exists()
    rb_files = sorted(f for f in (path.rglob("*.rb") if path.is_dir() else [path])
                      if "vendor" not in f.parts)
    for f in rb_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ctx.files.append({"path": f, "relative": str(f.relative_to(root)),
                              "source": source, "lines": source.count("\n") + 1})
        except Exception:
            pass
    return ctx

class RailsNPlusOne(Rule):
    code = "RB-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "Potential N+1 query: .all or .where without .includes in '{file}'"
    recommendation_template = "Use .includes(:association) or .eager_load to prevent N+1 queries."
    def check(self, context: RubyContext) -> list[Finding]:
        if not context.is_rails:
            return []
        findings = []
        for f in context.files:
            if (".all" in f["source"] or ".where(" in f["source"]) and ".each" in f["source"]:
                if ".includes(" not in f["source"] and ".eager_load(" not in f["source"]:
                    findings.append(self.finding(file=f["relative"]))
        return findings

class FatModel(Rule):
    code = "RB-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Model '{file}' is {lines} lines — extract concerns or service objects"
    recommendation_template = "Use ActiveSupport::Concern, service objects, or form objects to slim models."
    THRESHOLD = 300
    def check(self, context: RubyContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "/models/" in f["relative"] and f["lines"] > self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], lines=f["lines"]))
        return findings

class CallbackHell(Rule):
    code = "RB-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Model '{file}' has {count} callbacks — callbacks create hidden control flow"
    recommendation_template = "Extract side effects into service objects. Callbacks make debugging and testing difficult."
    THRESHOLD = 5
    def check(self, context: RubyContext) -> list[Finding]:
        findings = []
        callbacks = ["before_save", "after_save", "before_create", "after_create", "before_update",
                      "after_update", "before_destroy", "after_destroy", "before_validation", "after_validation",
                      "after_commit", "after_rollback"]
        for f in context.files:
            count = sum(1 for cb in callbacks if cb in f["source"])
            if count >= self.THRESHOLD:
                findings.append(self.finding(file=f["relative"], count=count))
        return findings

class UnscopedFind(Rule):
    code = "RB-SEC-001"
    severity = Severity.WARN
    category = Category.SECURITY
    message_template = "Unscoped .find() at line {line} — may expose records across tenants"
    recommendation_template = "Use scoped queries (current_user.posts.find) instead of Model.find for authorization."
    def check(self, context: RubyContext) -> list[Finding]:
        if not context.is_rails:
            return []
        findings = []
        pattern = re.compile(r'\b\w+\.find\(params\[:')
        for f in context.files:
            if "/controllers/" not in f["relative"]:
                continue
            for i, line in enumerate(f["source"].splitlines(), 1):
                if pattern.search(line):
                    findings.append(self.finding(file=f["relative"], line=i))
        return findings

RB_RULES = [RailsNPlusOne(), FatModel(), CallbackHell(), UnscopedFind()]

class RubyPack(Pack):
    name = "ruby"
    description = "Rails, ActiveRecord, and general Ruby architecture"
    extensions = [".rb"]
    def __init__(self) -> None:
        super().__init__()
        for rule in RB_RULES:
            self.register_rule(rule)
    def parse(self, path: Path) -> RubyContext:
        return parse_ruby_project(path)
