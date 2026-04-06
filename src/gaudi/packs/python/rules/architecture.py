"""
Architectural rules for Python projects.

Each rule has a unique code, severity, and recommendation designed
to be machine-readable by AI coding agents.
"""

from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext, ModelInfo


# ---------------------------------------------------------------------------
# ARCH — Architecture rules
# ---------------------------------------------------------------------------


class NoTenantIsolation(Rule):
    """
    ARCH-001: Multi-model project with no tenant isolation strategy.

    If a project has 3+ models with relationships between them but no
    model has a tenant/organization/account foreign key, the project
    likely needs a tenant isolation strategy.
    """

    code = "ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "Project has {model_count} related models but no tenant isolation column detected"
    )
    recommendation_template = (
        "Consider adding a tenant_id, organization_id, or account_id ForeignKey "
        "to models that store user data. Enforce filtering in all queries."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        if len(context.models) < 3:
            return []

        # Check if any model has a tenant-like column
        tenant_patterns = {"tenant", "organization", "account", "company", "client", "workspace"}
        has_tenant = False
        for model in context.models:
            for col in model.columns:
                if col.is_foreign_key and any(p in col.name.lower() for p in tenant_patterns):
                    has_tenant = True
                    break

        if has_tenant:
            return []

        # Check if models have relationships (suggesting multi-table app)
        has_relationships = any(m.foreign_keys for m in context.models)
        if not has_relationships:
            return []

        return [self.finding(model_count=len(context.models))]


class GodModel(Rule):
    """
    ARCH-002: Model with too many fields suggests it should be split.
    """

    code = "ARCH-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Model '{model}' has {count} fields — consider splitting into related models"
    recommendation_template = (
        "Models with more than {threshold} fields often contain distinct concerns. "
        "Consider extracting related fields into separate models with OneToOneField relationships."
    )

    THRESHOLD = 15

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for model in context.models:
            if len(model.columns) > self.THRESHOLD:
                findings.append(
                    self.finding(
                        file=model.source_file,
                        line=model.source_line,
                        model=model.name,
                        count=len(model.columns),
                        threshold=self.THRESHOLD,
                    )
                )
        return findings


class NullableForeignKeySprawl(Rule):
    """
    ARCH-003: Multiple nullable ForeignKeys suggest missing join table or polymorphism.
    """

    code = "ARCH-003"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = (
        "Model '{model}' has {count} nullable ForeignKeys — "
        "this may indicate an optional relationship better modeled as a join table"
    )
    recommendation_template = (
        "Review whether nullable ForeignKeys represent truly optional relationships "
        "or if the model is trying to handle multiple relationship types. "
        "Consider a join table or polymorphic pattern."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for model in context.models:
            nullable_fks = model.nullable_foreign_keys
            if len(nullable_fks) >= 2:
                findings.append(
                    self.finding(
                        file=model.source_file,
                        line=model.source_line,
                        model=model.name,
                        count=len(nullable_fks),
                    )
                )
        return findings


# ---------------------------------------------------------------------------
# IDX — Indexing rules
# ---------------------------------------------------------------------------


class MissingStringIndex(Rule):
    """
    IDX-001: CharField used for lookups without an index.

    CharField fields with common lookup names (email, slug, username, code, etc.)
    should have db_index=True.
    """

    code = "IDX-001"
    severity = Severity.WARN
    category = Category.INDEXING
    message_template = "Column '{column}' on '{model}' looks like a lookup field but has no index"
    recommendation_template = "Add db_index=True to '{column}' or include it in a composite index."

    LOOKUP_PATTERNS = {
        "email",
        "slug",
        "username",
        "code",
        "sku",
        "reference",
        "external_id",
        "api_key",
        "token",
        "uuid",
        "status",
    }

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for model in context.models:
            for col in model.columns:
                if (
                    col.field_type in {"CharField", "SlugField", "EmailField"}
                    and not col.has_index
                    and not col.has_unique
                    and any(p in col.name.lower() for p in self.LOOKUP_PATTERNS)
                ):
                    findings.append(
                        self.finding(
                            file=model.source_file,
                            line=col.source_line,
                            column=col.name,
                            model=model.name,
                        )
                    )
        return findings


class NoIndexOnFilterableField(Rule):
    """
    IDX-002: DateTimeField without an index — common filter/sort target.
    """

    code = "IDX-002"
    severity = Severity.INFO
    category = Category.INDEXING
    message_template = (
        "DateTimeField '{column}' on '{model}' has no index — these are commonly filtered/sorted"
    )
    recommendation_template = (
        "If you query or sort by '{column}', add db_index=True. "
        "Date fields are among the most commonly filtered columns."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for model in context.models:
            for col in model.columns:
                if (
                    col.field_type in {"DateTimeField", "DateField"}
                    and not col.has_index
                    and col.name not in {"created_at", "updated_at", "modified_at"}  # auto fields
                ):
                    findings.append(
                        self.finding(
                            file=model.source_file,
                            line=col.source_line,
                            column=col.name,
                            model=model.name,
                        )
                    )
        return findings


# ---------------------------------------------------------------------------
# SCHEMA — Schema design rules
# ---------------------------------------------------------------------------


class MissingTimestamps(Rule):
    """
    SCHEMA-001: Model without created_at/updated_at timestamps.
    """

    code = "SCHEMA-001"
    severity = Severity.INFO
    category = Category.SCHEMA
    message_template = "Model '{model}' has no timestamp fields (created_at, updated_at)"
    recommendation_template = (
        "Add created_at and updated_at DateTimeField columns with auto_now_add and auto_now. "
        "These are essential for debugging, auditing, and data management."
    )

    TIMESTAMP_PATTERNS = {
        "created_at",
        "created",
        "date_created",
        "created_date",
        "updated_at",
        "updated",
        "modified_at",
        "date_modified",
        "modified_date",
        "timestamp",
    }

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for model in context.models:
            # Skip abstract models and through tables
            if len(model.columns) < 2:
                continue

            has_timestamps = any(
                col.name.lower() in self.TIMESTAMP_PATTERNS for col in model.columns
            )

            if not has_timestamps:
                findings.append(
                    self.finding(
                        file=model.source_file,
                        line=model.source_line,
                        model=model.name,
                    )
                )
        return findings


class ColumnSprawl(Rule):
    """
    SCHEMA-002: Too many nullable columns suggest the table is trying to do too much.
    """

    code = "SCHEMA-002"
    severity = Severity.WARN
    category = Category.SCHEMA
    message_template = (
        "Model '{model}' has {nullable_count} nullable columns out of {total_count} — "
        "high nullable ratio suggests the table covers multiple concerns"
    )
    recommendation_template = (
        "Review nullable columns. If groups of nullable fields are only populated together, "
        "they likely belong in a separate related model."
    )

    NULLABLE_RATIO_THRESHOLD = 0.5
    MIN_COLUMNS = 6

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for model in context.models:
            if len(model.columns) < self.MIN_COLUMNS:
                continue

            nullable_count = sum(1 for c in model.columns if c.nullable)
            ratio = nullable_count / len(model.columns) if model.columns else 0

            if ratio >= self.NULLABLE_RATIO_THRESHOLD and nullable_count >= 4:
                findings.append(
                    self.finding(
                        file=model.source_file,
                        line=model.source_line,
                        model=model.name,
                        nullable_count=nullable_count,
                        total_count=len(model.columns),
                    )
                )
        return findings


class NoStringLengthLimit(Rule):
    """
    SCHEMA-003: TextField used where CharField with max_length might be appropriate.
    """

    code = "SCHEMA-003"
    severity = Severity.INFO
    category = Category.SCHEMA
    message_template = "Column '{column}' on '{model}' uses TextField — consider if a max_length constraint applies"
    recommendation_template = (
        "TextField has no length limit in the database. If this field has a natural "
        "maximum length (names, titles, codes), use CharField with max_length instead."
    )

    SHORT_NAME_PATTERNS = {"name", "title", "label", "code", "sku", "reference", "type", "status"}

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for model in context.models:
            for col in model.columns:
                if col.field_type == "TextField" and any(
                    p in col.name.lower() for p in self.SHORT_NAME_PATTERNS
                ):
                    findings.append(
                        self.finding(
                            file=model.source_file,
                            line=col.source_line,
                            column=col.name,
                            model=model.name,
                        )
                    )
        return findings


# ---------------------------------------------------------------------------
# SEC — Security rules
# ---------------------------------------------------------------------------


class NoMetaPermissions(Rule):
    """
    SEC-001: Django model without explicit permissions in Meta.
    """

    code = "SEC-001"
    severity = Severity.INFO
    category = Category.SECURITY
    message_template = "Model '{model}' has no explicit Meta permissions defined"
    recommendation_template = (
        "Define explicit permissions in Meta.permissions for fine-grained access control. "
        "Django's default add/change/delete/view may not match your authorization needs."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        if context.framework != "django":
            return []

        findings = []
        for model in context.models:
            if model.has_meta and "permissions" not in model.meta_options:
                findings.append(
                    self.finding(
                        file=model.source_file,
                        line=model.source_line,
                        model=model.name,
                    )
                )
        return findings


# ---------------------------------------------------------------------------
# STRUCT — Project structure rules
# ---------------------------------------------------------------------------


class SingleFileModels(Rule):
    """
    STRUCT-001: All models in a single file that's getting too long.
    """

    code = "STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = (
        "File '{file}' contains {count} models and is {lines} lines long — "
        "consider splitting into a models package"
    )
    recommendation_template = (
        "Convert models.py into a models/ package with separate files per domain. "
        "Create models/__init__.py that imports all models for Django compatibility."
    )

    MAX_MODELS_PER_FILE = 8
    MAX_LINES = 500

    def check(self, context: PythonContext) -> list[Finding]:
        # Group models by file
        models_by_file: dict[str, list[ModelInfo]] = {}
        for model in context.models:
            models_by_file.setdefault(model.source_file, []).append(model)

        findings = []
        for filepath, models in models_by_file.items():
            file_info = next((f for f in context.files if f.relative_path == filepath), None)
            lines = file_info.line_count if file_info else 0

            if len(models) >= self.MAX_MODELS_PER_FILE or lines >= self.MAX_LINES:
                findings.append(
                    self.finding(
                        file=filepath,
                        count=len(models),
                        lines=lines,
                    )
                )
        return findings


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

ALL_RULES = [
    NoTenantIsolation(),
    GodModel(),
    NullableForeignKeySprawl(),
    MissingStringIndex(),
    NoIndexOnFilterableField(),
    MissingTimestamps(),
    ColumnSprawl(),
    NoStringLengthLimit(),
    NoMetaPermissions(),
    SingleFileModels(),
]
