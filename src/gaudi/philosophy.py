# ABOUTME: Philosophy school inference from project signals.
# ABOUTME: Analyzes dependencies, structure, and patterns to recommend a school.
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

if True:  # avoid tomllib being seen as unused when guarded by version check
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib


@dataclass
class SchoolSignal:
    """One piece of evidence pointing toward a philosophy school."""

    school: str
    reason: str
    weight: int = 1


@dataclass
class InferenceResult:
    """The output of philosophy inference — a ranked list of schools with evidence."""

    signals: list[SchoolSignal] = field(default_factory=list)

    @property
    def scores(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for s in self.signals:
            totals[s.school] = totals.get(s.school, 0) + s.weight
        return dict(sorted(totals.items(), key=lambda kv: -kv[1]))

    @property
    def recommended(self) -> str | None:
        s = self.scores
        return next(iter(s), None) if s else None


# ---------------------------------------------------------------------------
# Signal detectors
# ---------------------------------------------------------------------------

_FRAMEWORK_SIGNALS: dict[str, list[tuple[str, str]]] = {
    "django": [
        ("convention", "Django is a convention-over-configuration framework"),
    ],
    "flask": [
        ("pragmatic", "Flask is a micro-framework favoring pragmatic simplicity"),
    ],
    "fastapi": [
        ("pragmatic", "FastAPI favors pragmatic, function-based endpoints"),
    ],
    "sqlalchemy": [
        ("classical", "SQLAlchemy's ORM encourages rich domain models"),
    ],
    "pydantic": [
        ("classical", "Pydantic models are structured domain objects"),
    ],
    "numpy": [
        ("data-oriented", "NumPy signals batch/array processing patterns"),
    ],
    "pandas": [
        ("data-oriented", "Pandas signals tabular data processing"),
    ],
    "polars": [
        ("data-oriented", "Polars signals columnar batch processing"),
    ],
    "celery": [
        ("event-sourced", "Celery task queues signal event-driven architecture"),
    ],
    "kafka": [
        ("event-sourced", "Kafka signals event streaming architecture"),
    ],
    "tenacity": [
        ("resilient", "Tenacity signals retry/resilience patterns"),
    ],
    "circuitbreaker": [
        ("resilient", "Circuit breaker library signals resilience-first design"),
    ],
}


def _read_dependencies(project_path: Path) -> set[str]:
    """Extract dependency names from pyproject.toml, requirements.txt, or setup.cfg."""
    deps: set[str] = set()

    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            for dep in data.get("project", {}).get("dependencies", []):
                name = dep.split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip()
                deps.add(name.lower())
        except Exception:
            pass

    for req_file in ("requirements.txt", "requirements.in"):
        req_path = project_path / req_file
        if req_path.exists():
            try:
                for line in req_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    name = line.split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip()
                    deps.add(name.lower())
            except Exception:
                pass

    return deps


def _detect_dependency_signals(deps: set[str]) -> list[SchoolSignal]:
    signals: list[SchoolSignal] = []
    for dep_name, school_entries in _FRAMEWORK_SIGNALS.items():
        if dep_name in deps:
            for school, reason in school_entries:
                signals.append(SchoolSignal(school=school, reason=reason, weight=2))
    return signals


def _detect_structure_signals(project_path: Path) -> list[SchoolSignal]:
    """Detect philosophy signals from project structure."""
    signals: list[SchoolSignal] = []

    # Shell scripts suggest Unix philosophy
    sh_files = list(project_path.rglob("*.sh"))
    makefiles = list(project_path.glob("Makefile"))
    if sh_files or makefiles:
        signals.append(
            SchoolSignal(
                school="unix",
                reason=f"Found {len(sh_files)} shell script(s) and {len(makefiles)} Makefile(s)",
            )
        )

    # Protocol classes suggest classical OOP
    py_files = list(project_path.rglob("*.py"))
    protocol_count = 0
    for py_file in py_files[:50]:  # cap file scanning
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "Protocol" in content and "from typing" in content:
                protocol_count += 1
        except Exception:
            pass
    if protocol_count >= 2:
        signals.append(
            SchoolSignal(
                school="classical",
                reason=f"Found {protocol_count} files using typing.Protocol (interface segregation)",
            )
        )

    # models.py + admin.py suggest Django/convention
    if list(project_path.rglob("models.py")) and list(project_path.rglob("admin.py")):
        signals.append(
            SchoolSignal(
                school="convention",
                reason="Found models.py + admin.py (Django app structure)",
                weight=2,
            )
        )

    # migrations/ directory suggests convention
    if list(project_path.rglob("migrations/")):
        signals.append(
            SchoolSignal(
                school="convention",
                reason="Found migrations/ directory (framework-managed schema)",
            )
        )

    return signals


def infer_philosophy(project_path: Path) -> InferenceResult:
    """Analyze a project and return ranked philosophy school recommendations."""
    result = InferenceResult()
    deps = _read_dependencies(project_path)
    result.signals.extend(_detect_dependency_signals(deps))
    result.signals.extend(_detect_structure_signals(project_path))
    return result
