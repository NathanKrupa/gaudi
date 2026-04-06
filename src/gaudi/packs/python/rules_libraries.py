"""
Gaudí Python Library Rules.

Architectural rules for the top 10 Python libraries/frameworks:
Django (extended), FastAPI, SQLAlchemy, Flask, Celery,
Pandas, Requests/HTTPX, Pydantic, pytest, Django REST Framework.
"""

from __future__ import annotations

import ast
import re

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------------------
# DJANGO (extended beyond model rules)
# ---------------------------------------------------------------------------

class DjangoSecretKeyExposed(Rule):
    code = "DJ-SEC-001"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "SECRET_KEY appears hardcoded in settings at line {line}"
    recommendation_template = (
        "Load SECRET_KEY from environment variables: SECRET_KEY = os.environ['SECRET_KEY']. "
        "Hardcoded secrets in source control are a critical security vulnerability."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "settings" not in f.relative_path.lower():
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "SECRET_KEY" in line and ("'" in line or '"' in line) and "os.environ" not in line and "env(" not in line:
                    if not line.strip().startswith("#"):
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class DjangoDebugTrue(Rule):
    code = "DJ-SEC-002"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "DEBUG = True in production settings at line {line}"
    recommendation_template = "Set DEBUG = False in production. Use environment variables to control debug mode."

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "settings" not in f.relative_path.lower():
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped == "DEBUG = True" or stripped == "DEBUG=True":
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class DjangoFatView(Rule):
    code = "DJ-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "View file '{file}' is {lines} lines — extract business logic to services"
    recommendation_template = "Views should be thin. Move business logic to service functions or model methods."
    THRESHOLD = 300

    def check(self, context: PythonContext) -> list[Finding]:
        if context.framework != "django":
            return []
        findings = []
        for f in context.files:
            if "views" in f.relative_path.lower() and f.line_count > self.THRESHOLD:
                findings.append(self.finding(file=f.relative_path, lines=f.line_count))
        return findings


# ---------------------------------------------------------------------------
# FASTAPI
# ---------------------------------------------------------------------------

class FastAPINoResponseModel(Rule):
    code = "FAPI-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "FastAPI endpoint without response_model at line {line}"
    recommendation_template = (
        "Add response_model parameter to endpoints for automatic validation, "
        "serialization, and OpenAPI documentation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "fastapi" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            pattern = re.compile(r'@\w+\.(get|post|put|patch|delete)\s*\(')
            for i, line in enumerate(source.splitlines(), 1):
                if pattern.search(line) and "response_model" not in line:
                    # Check next few lines for response_model
                    block = "\n".join(source.splitlines()[i-1:i+3])
                    if "response_model" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class FastAPISyncEndpoint(Rule):
    code = "FAPI-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    message_template = "Synchronous endpoint function at line {line} — consider async for I/O"
    recommendation_template = (
        "Use async def for endpoints with I/O operations (database, HTTP calls). "
        "Sync endpoints block the event loop thread pool."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "fastapi" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lines = source.splitlines()
            for i, line in enumerate(lines, 1):
                if re.search(r'@\w+\.(get|post|put|patch|delete)', line):
                    # Check if next def is sync
                    for j in range(i, min(i + 5, len(lines))):
                        if lines[j - 1].strip().startswith("def ") and "async" not in lines[j - 1]:
                            findings.append(self.finding(file=f.relative_path, line=j))
                            break
        return findings


# ---------------------------------------------------------------------------
# SQLALCHEMY
# ---------------------------------------------------------------------------

class SQLAlchemySessionLeak(Rule):
    code = "SA-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Session created without context manager at line {line}"
    recommendation_template = (
        "Use 'with Session() as session:' or a dependency injection pattern. "
        "Leaked sessions cause connection pool exhaustion."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "sqlalchemy" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "Session()" in line and "with " not in line and "yield" not in line:
                    if "session" in line.lower() and "=" in line:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class SQLAlchemyLazyDefault(Rule):
    code = "SA-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "relationship() using default lazy loading at line {line}"
    recommendation_template = (
        "Explicitly set lazy='select', 'joined', 'subquery', or 'selectin' on relationships. "
        "Default lazy loading causes N+1 queries."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "relationship(" in line and "lazy=" not in line:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


# ---------------------------------------------------------------------------
# FLASK
# ---------------------------------------------------------------------------

class FlaskNoAppFactory(Rule):
    code = "FLASK-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Flask app created at module level — use application factory pattern"
    recommendation_template = (
        "Use create_app() factory function instead of module-level Flask(). "
        "Factories enable testing, multiple configs, and blueprint registration."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "flask" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if re.match(r'^app\s*=\s*Flask\s*\(', stripped):
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


# ---------------------------------------------------------------------------
# CELERY
# ---------------------------------------------------------------------------

class CeleryNoRetry(Rule):
    code = "CELERY-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Celery task without retry configuration at line {line}"
    recommendation_template = (
        "Add autoretry_for, max_retries, and retry_backoff to tasks that call external services. "
        "Tasks without retry config fail permanently on transient errors."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "celery" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "@" in line and (".task" in line or "shared_task" in line):
                    block = "\n".join(source.splitlines()[max(0, i-1):i+5])
                    if "retry" not in block and "max_retries" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class CeleryNoTimeLimit(Rule):
    code = "CELERY-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "Celery task without time limit at line {line}"
    recommendation_template = (
        "Add time_limit and soft_time_limit to prevent runaway tasks from consuming workers."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "celery" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "@" in line and (".task" in line or "shared_task" in line):
                    block = "\n".join(source.splitlines()[max(0, i-1):i+5])
                    if "time_limit" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


# ---------------------------------------------------------------------------
# PANDAS
# ---------------------------------------------------------------------------

class PandasInplaceAntiPattern(Rule):
    code = "PD-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "inplace=True used at line {line} — this is deprecated and error-prone"
    recommendation_template = (
        "Use df = df.method() instead of df.method(inplace=True). "
        "inplace breaks method chaining and is planned for deprecation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "pandas" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "inplace=True" in line:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class PandasIterrows(Rule):
    code = "PD-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "iterrows() at line {line} — use vectorized operations instead"
    recommendation_template = (
        "iterrows() is extremely slow. Use .apply(), vectorized operations, "
        "or .itertuples() (10-100x faster) instead."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if ".iterrows()" in line:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


# ---------------------------------------------------------------------------
# REQUESTS / HTTPX
# ---------------------------------------------------------------------------

class RequestsNoTimeout(Rule):
    code = "HTTP-SCALE-001"
    severity = Severity.ERROR
    category = Category.SCALABILITY
    message_template = "HTTP request without timeout at line {line}"
    recommendation_template = (
        "Always set a timeout on HTTP requests. Without a timeout, your application "
        "can hang indefinitely waiting for a response."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            pattern = re.compile(r'requests\.(get|post|put|patch|delete|head|options)\s*\(')
            for i, line in enumerate(source.splitlines(), 1):
                if pattern.search(line) and "timeout" not in line:
                    # Check next few lines too
                    block = "\n".join(source.splitlines()[i-1:i+3])
                    if "timeout" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class RequestsNoRetry(Rule):
    code = "HTTP-ARCH-001"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "HTTP calls without retry logic in '{file}'"
    recommendation_template = (
        "Use urllib3.util.Retry with requests.Session for automatic retries on transient failures."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "requests" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if "requests.get" in source or "requests.post" in source:
                if "Retry" not in source and "retry" not in source and "tenacity" not in source:
                    findings.append(self.finding(file=f.relative_path))
        return findings


# ---------------------------------------------------------------------------
# PYDANTIC
# ---------------------------------------------------------------------------

class PydanticMutableDefault(Rule):
    code = "PYD-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Mutable default value in Pydantic model at line {line}"
    recommendation_template = (
        "Use Field(default_factory=list) instead of Field(default=[]) in Pydantic models. "
        "Mutable defaults are shared across instances."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "pydantic" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if re.search(r'=\s*\[\s*\]|=\s*\{\s*\}', line) and "Field(" not in line:
                    if "BaseModel" in source or "BaseSettings" in source:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


# ---------------------------------------------------------------------------
# PYTEST
# ---------------------------------------------------------------------------

class PytestAssertMessage(Rule):
    code = "TEST-STRUCT-001"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "Complex assertion without message at line {line}"
    recommendation_template = (
        "Add a failure message to complex assertions: assert condition, 'description'. "
        "Messages make test failures easier to diagnose."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "test_" not in f.relative_path:
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("assert ") and "," not in stripped and len(stripped) > 40:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class PytestFixtureScope(Rule):
    code = "TEST-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    message_template = "Expensive fixture without scope at line {line}"
    recommendation_template = (
        "Add scope='session' or scope='module' to fixtures that create expensive resources "
        "(database connections, API clients) to avoid recreating them per test."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        expensive_patterns = ["connection", "engine", "client", "session", "database", "db"]
        for f in context.files:
            if "conftest" not in f.relative_path:
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "@pytest.fixture" in line and "scope=" not in line:
                    # Check fixture name
                    next_lines = source.splitlines()[i:i+3]
                    func_line = "\n".join(next_lines)
                    if any(p in func_line.lower() for p in expensive_patterns):
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


# ---------------------------------------------------------------------------
# DJANGO REST FRAMEWORK
# ---------------------------------------------------------------------------

class DRFNoPermissionClass(Rule):
    code = "DRF-SEC-001"
    severity = Severity.WARN
    category = Category.SECURITY
    message_template = "ViewSet without explicit permission_classes in '{file}'"
    recommendation_template = (
        "Set permission_classes on every ViewSet. Relying on DEFAULT_PERMISSION_CLASSES "
        "is fragile — a settings change could expose all endpoints."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "rest_framework" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if ("ViewSet" in source or "APIView" in source) and "permission_classes" not in source:
                findings.append(self.finding(file=f.relative_path))
        return findings


class DRFNoThrottling(Rule):
    code = "DRF-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    message_template = "API view without throttle_classes in '{file}'"
    recommendation_template = (
        "Add throttle_classes to prevent abuse. Public APIs without rate limiting "
        "are vulnerable to DDoS and abuse."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "rest_framework" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if ("ViewSet" in source or "APIView" in source) and "throttle_classes" not in source:
                findings.append(self.finding(file=f.relative_path))
        return findings


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

LIBRARY_RULES = [
    # Django
    DjangoSecretKeyExposed(),
    DjangoDebugTrue(),
    DjangoFatView(),
    # FastAPI
    FastAPINoResponseModel(),
    FastAPISyncEndpoint(),
    # SQLAlchemy
    SQLAlchemySessionLeak(),
    SQLAlchemyLazyDefault(),
    # Flask
    FlaskNoAppFactory(),
    # Celery
    CeleryNoRetry(),
    CeleryNoTimeLimit(),
    # Pandas
    PandasInplaceAntiPattern(),
    PandasIterrows(),
    # Requests
    RequestsNoTimeout(),
    RequestsNoRetry(),
    # Pydantic
    PydanticMutableDefault(),
    # pytest
    PytestAssertMessage(),
    PytestFixtureScope(),
    # DRF
    DRFNoPermissionClass(),
    DRFNoThrottling(),
]
