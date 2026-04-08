# Gaudi Rule Source Registry

Every rule in Gaudi traces back to a canonical source: a published text,
a named pattern, or (where original) the project's own design principles.
This registry provides citable provenance for each rule code and serves as
a mining queue for planned rules.

The **editorial doctrine** that governs which rules enter the catalog, how
their severity and thresholds are assigned, and when they are subsumed or cut
lives in [principles.md](principles.md). Footnotes in this registry that
explain rule removals (e.g. "detection too weak", "subsumed by STAB-006")
are applications of those principles.

---

## Source Texts

| Key        | Full Title                                                    | Author(s)              | Edition |
|------------|---------------------------------------------------------------|------------------------|---------|
| **FOWLER** | *Refactoring: Improving the Design of Existing Code*          | Martin Fowler          | 2nd     |
| **NYGARD** | *Release It! Design and Deploy Production-Ready Software*     | Michael T. Nygard      | 2nd     |
| **MARTIN** | *Clean Architecture: A Craftsman's Guide to Software Structure and Design* | Robert C. Martin | 1st  |
| **ARCH90** | Architecture 90 (internal curriculum)                         | Nathan Krupa           | --      |
| **PY314**  | CPython 3.14 changelog / PEPs                                 | Python core devs       | --      |
| **FWDOCS** | Framework official documentation (Django, FastAPI, Flask, etc.)| Various                | --      |

Future source keys (not yet mined):

| Key          | Full Title                                                  | Author(s)              |
|--------------|-------------------------------------------------------------|------------------------|
| **NEWMAN**   | *Building Microservices*                                    | Sam Newman (2nd ed.)   |
| **OUSTRHOUT**| *A Philosophy of Software Design*                           | John Ousterhout        |
| **PEAA**     | *Patterns of Enterprise Application Architecture*           | Martin Fowler          |

---

## Implemented Rules

### Code Smell Rules (SMELL) -- Source: FOWLER

All 24 rules map directly to Fowler's smell catalog in *Refactoring* (2nd ed.), Chapter 3.

| Code      | Class Name           | Fowler Smell                           | Chapter/Section |
|-----------|----------------------|----------------------------------------|-----------------|
| SMELL-001 | MysteriousName       | Mysterious Name                        | Ch. 3           |
| SMELL-002 | DuplicatedCode       | Duplicated Code                        | Ch. 3           |
| SMELL-003 | LongFunction         | Long Function                          | Ch. 3           |
| SMELL-004 | LongParameterList    | Long Parameter List                    | Ch. 3           |
| SMELL-005 | GlobalData           | Global Data                            | Ch. 3           |
| SMELL-006 | MutableData          | Mutable Data                           | Ch. 3           |
| SMELL-007 | DivergentChange      | Divergent Change                       | Ch. 3           |
| SMELL-008 | ShotgunSurgery       | Shotgun Surgery                        | Ch. 3           |
| SMELL-009 | FeatureEnvy          | Feature Envy                           | Ch. 3           |
| SMELL-010 | DataClumps           | Data Clumps                            | Ch. 3           |
| SMELL-011 | PrimitiveObsession   | Primitive Obsession                    | Ch. 3           |
| SMELL-012 | RepeatedSwitches     | Repeated Switches                      | Ch. 3           |
| SMELL-013 | Loops                | Loops                                  | Ch. 3           |
| SMELL-014 | LazyElement          | Lazy Element                           | Ch. 3           |
| SMELL-015 | SpeculativeGenerality| Speculative Generality                 | Ch. 3           |
| SMELL-016 | TemporaryField       | Temporary Field                        | Ch. 3           |
| SMELL-017 | MessageChains        | Message Chains                         | Ch. 3           |
| SMELL-018 | MiddleMan            | Middle Man                             | Ch. 3           |
| SMELL-019 | InsiderTrading       | Insider Trading                        | Ch. 3           |
| SMELL-020 | LargeClass           | Large Class                            | Ch. 3           |
| SMELL-021 | AlternativeInterfaces| Alternative Classes w/ Different Interfaces | Ch. 3    |
| SMELL-022 | DataClassSmell       | Data Class                             | Ch. 3           |
| SMELL-023 | RefusedBequest       | Refused Bequest                        | Ch. 3           |
| SMELL-024 | Comments             | Comments                               | Ch. 3           |

### Architecture 90 Rules -- Source: ARCH90

| Code       | Class Name              | Principle                                   | A90 Day |
|------------|-------------------------|---------------------------------------------|---------|
| STRUCT-010 | PathHacks               | Proper packaging over sys.path hacks        | Day 1   |
| STRUCT-011 | MissingPyproject        | Modern packaging requires pyproject.toml    | Day 1   |
| STRUCT-012 | NoEntryPoint            | CLI scripts need entry points               | Day 1   |
| STRUCT-013 | NoLockFile              | Pin dependencies for reproducibility        | Day 1   |
| STRUCT-020 | MissingReturnTypes      | Type annotations on public APIs             | Day 2   |
| STRUCT-021 | MagicStrings            | Extract repeated literals to constants      | Day 2   |
| ARCH-010   | ImportDirectionViolation| Arrows point inward only                    | Day 3   |
| ARCH-011   | ConnectorLogicLeak      | Data layer has no business logic            | Day 3   |
| ARCH-013   | FatScript               | Thin entry points, fat services             | Day 3   |
| ARCH-020   | EnvLeakage              | Config injection, not direct env reads      | Day 4   |
| ARCH-022   | ScatteredConfig         | Centralize configuration                    | Day 4   |
| ERR-001    | BareExcept              | Catch specific exceptions                   | Day 5   |
| ERR-002    | BroadTryBlock           | Narrow try blocks (>10 stmts)               | Nygard  |
| ERR-003    | ErrorSwallowing         | Don't log-and-forget errors                 | Day 5   |
| ERR-004    | ExceptPass              | `except: pass` silently swallows errors     | Nygard  |
| ERR-005    | InconsistentExceptions  | Module raises 4+ unrelated exception types  | Nygard  |
| ERR-006    | ExceptionInInit         | Don't raise non-validation errors in __init__ | Nygard  |
| LOG-001    | UnstructuredLogging     | Lazy %-formatting in logger calls           | Day 5   |
| OPS-002    | MissingPrecommit        | Pre-commit hooks for quality gates          | Day 6   |

### Django/ORM Architecture Rules -- Source: FWDOCS + ARCH90

| Code       | Class Name                | Source Pattern                            |
|------------|---------------------------|-------------------------------------------|
| ARCH-001   | NoTenantIsolation         | FWDOCS: Django multi-tenancy patterns     |
| ARCH-002   | GodModel                  | FOWLER: Large Class (applied to models)   |
| ARCH-003   | NullableForeignKeySprawl  | FWDOCS: Django relationship patterns      |
| IDX-001    | MissingStringIndex        | FWDOCS: Django query optimization         |
| IDX-002    | NoIndexOnFilterableField  | FWDOCS: Django query optimization         |
| SCHEMA-001 | MissingTimestamps         | FWDOCS: Django audit trail conventions    |
| SCHEMA-002 | ColumnSprawl              | FOWLER: Large Class (applied to schema)   |
| SCHEMA-003 | NoStringLengthLimit       | FWDOCS: Django field best practices       |
| SEC-001    | NoMetaPermissions         | FWDOCS: Django auth framework             |
| STRUCT-001 | SingleFileModels          | ARCH90: One concern per module            |

### Library-Specific Rules -- Source: FWDOCS

| Code            | Class Name               | Library     | Source Pattern                          |
|-----------------|--------------------------|-------------|-----------------------------------------|
| DJ-SEC-001      | DjangoSecretKeyExposed   | Django      | FWDOCS: Django deployment checklist     |
| DJ-SEC-002      | DjangoDebugTrue          | Django      | FWDOCS: Django deployment checklist     |
| DJ-STRUCT-001   | DjangoFatView            | Django      | ARCH90: Thin entry points               |
| FAPI-ARCH-001   | FastAPINoResponseModel   | FastAPI     | FWDOCS: FastAPI response models         |
| FAPI-SCALE-001  | FastAPISyncEndpoint      | FastAPI     | FWDOCS: FastAPI async patterns          |
| SA-SCALE-001    | SQLAlchemyLazyDefault    | SQLAlchemy  | FWDOCS: SQLAlchemy N+1 prevention       |

*SA-ARCH-001 (SQLAlchemySessionLeak) removed -- consolidated into STAB-006 (UnmanagedResource).*
*HTTP-ARCH-001 (RequestsNoRetry) removed -- subsumed by STAB-003 (RetryWithoutBackoff).*
| FLASK-STRUCT-001| FlaskNoAppFactory        | Flask       | FWDOCS: Flask application factory       |
| CELERY-ARCH-001 | CeleryNoRetry            | Celery      | FWDOCS + NYGARD: retry configuration    |
| CELERY-SCALE-001| CeleryNoTimeLimit        | Celery      | FWDOCS + NYGARD: task timeouts          |
| PD-ARCH-001     | PandasInplaceAntiPattern | Pandas      | FWDOCS: Pandas deprecation guidance     |
| PD-SCALE-001    | PandasIterrows           | Pandas      | FWDOCS: Pandas vectorization            |
| HTTP-SCALE-001  | RequestsNoTimeout        | Requests    | NYGARD: Timeouts (Ch. 5)               |
| PYD-ARCH-001    | PydanticMutableDefault   | Pydantic    | FWDOCS: Pydantic validators             |
| TEST-STRUCT-001 | PytestAssertMessage      | pytest      | FWDOCS: pytest assertion introspection  |
| TEST-SCALE-001  | PytestFixtureScope       | pytest      | FWDOCS: pytest fixture optimization     |
| TEST-ARCH-001   | PytestOverMocking        | pytest      | ARCH90 anti-mock; FWDOCS pytest practice|
| TEST-ARCH-002   | PytestNoTestCoverage     | pytest      | pytest convention `tests/test_<mod>.py` |
| TEST-ARCH-003   | PytestAssertInProductionCode | (any)   | PEP 8; Python ref on `assert`           |
| TEST-STRUCT-002 | PytestFixtureDependencyDepth | pytest  | FWDOCS pytest fixture composition       |
| TEST-STRUCT-003 | PytestTestMethodTooLong  | pytest      | Beck *TDD*; pytest best practices       |
| AWS-ARCH-001    | HardcodedRegion          | boto3       | FWDOCS: AWS Well-Architected Framework  |
| AWS-ERR-001     | BareClientCall           | boto3       | FWDOCS: boto3 error handling            |
| AWS-SCALE-001   | UnpaginatedList          | boto3       | FWDOCS: boto3 pagination                |
| DRF-SEC-001     | DRFNoPermissionClass     | DRF         | FWDOCS: DRF permissions                 |
| DRF-SCALE-001   | DRFNoThrottling          | DRF         | FWDOCS: DRF throttling                  |

### Python 3.14 Compatibility -- Source: PY314

| Code       | Class Name               | PEP / Changelog Reference                |
|------------|--------------------------|------------------------------------------|
| PY314-001  | RemovedIn314Import       | CPython 3.14 What's New: Removals        |
| PY314-002  | DeprecatedIn314Import    | CPython 3.14 What's New: Deprecations    |
| PY314-003  | DeferredAnnotationAccess | PEP 649: Deferred Evaluation             |
| PY314-004  | FinallyControlFlow       | CPython 3.14: SyntaxWarning              |
| PY314-005  | NotImplementedBoolContext| CPython 3.14: TypeError change            |
| PY314-006  | TarfileNoFilter          | CPython 3.14: tarfile security            |

### Stability Rules (STAB) -- Source: NYGARD

Rules mined from *Release It!* (2nd ed.). Nygard's anti-patterns describe
detectable failure states -- exactly the grammar Gaudi needs.

| Code      | Class Name            | Nygard Pattern / Anti-Pattern               | Chapter   |
|-----------|-----------------------|----------------------------------------------|-----------|
| STAB-001  | UnboundedResultSet    | Unbounded Result Sets (anti-pattern)         | Ch. 4     |
| STAB-003  | RetryWithoutBackoff   | Retry + Timeouts (incorrect implementation)  | Ch. 5     |
| STAB-004  | UnboundedCache        | Steady State (unbounded resource growth)     | Ch. 5     |
| STAB-005  | BlockingInAsync       | Blocked Threads (anti-pattern)               | Ch. 4     |
| STAB-006  | UnmanagedResource     | Steady State (resource leak, incl. sessions) | Ch. 5     |
| STAB-007  | UnboundedThreadPool   | Unbalanced Capacities (anti-pattern)         | Ch. 4     |

*STAB-002 (NoCircuitBreaker) removed -- detection too weak (project-level heuristic). Moved to mining queue.*

### Concurrency / Async Rules (ASYNC) -- Source: NYGARD + FWDOCS

Rules covering Python's async ecosystem and thread-pool concurrency. STAB-005
(BlockingInAsync) catches the single most common mistake; this family expands
coverage to shared mutable state, missing async context managers, mixed sync/async
modules, and missing graceful shutdown.

| Code      | Class Name                       | Pattern / Anti-Pattern                          | Source                |
|-----------|----------------------------------|-------------------------------------------------|-----------------------|
| ASYNC-001 | SharedMutableStateAcrossThreads  | Module-level mutable mutated inside thread pool | NYGARD Ch. 4          |
| ASYNC-002 | MissingAsyncContextManager       | aiohttp/httpx async client without async with   | FWDOCS (aiohttp/httpx)|
| ASYNC-003 | MixedSyncAsyncModule             | Module mixes async def with sync requests calls | FWDOCS (FastAPI)      |
| ASYNC-004 | NoGracefulShutdown               | asyncio.run() with no signal handler registered | Python asyncio docs   |

### API Design Rules (API) -- Source: REST/OpenAPI/OWASP

Rules covering common API design flaws that span Django, FastAPI, and Flask.
SVC-003 (NoAPIVersioning) and FAPI-ARCH-001 (NoResponseModel) cover the
classic mistakes; this family adds pagination, return-type consistency, ID
leakage, and undocumented error responses.

| Code     | Class Name              | Pattern / Anti-Pattern                              | Source                |
|----------|-------------------------|-----------------------------------------------------|-----------------------|
| API-001  | MissingPagination       | List endpoint returns `.all()`/`.filter()` unsliced | REST best practices   |
| API-002  | InconsistentReturnType  | Endpoint mixes dict literal with Response object    | REST best practices   |
| API-003  | LeakingInternalID       | URL pattern exposes `<int:pk>` / int PK             | OWASP API (BOLA)      |
| API-004  | NoErrorResponseSchema   | FastAPI `response_model=` with no `responses=`      | OpenAPI specification |

### Dependency Graph Rules (DEP) -- Source: MARTIN

Rules mined from *Clean Architecture*. Module-level coupling metrics that
no other Python linter detects, because they require project-wide graph analysis.

| Code     | Class Name           | Martin Principle                            | Detection                          |
|----------|----------------------|----------------------------------------------|------------------------------------|
| DEP-001  | CircularImport       | Acyclic Dependencies Principle (ADP)         | DFS cycle detection on import graph|
| DEP-002  | FanOutExplosion      | Component coupling: efferent coupling (Ce)   | Internal imports per module >= 10  |
| DEP-003  | FanInConcentration   | Fragile hub detection                        | Imported by >= 80% of project      |
| DEP-004  | UnstableDependency   | Stable Dependencies Principle (SDP)          | I = Ce / (Ca + Ce) >= 0.5 with high Ca |

### Complexity Rules (CPLX) -- Source: OUSTRHOUT

Rules mined from *A Philosophy of Software Design*. Ousterhout's design quality
heuristics target module shape rather than line-level style -- territory no
existing Python linter covers.

| Code     | Class Name            | Ousterhout Principle                         | Chapter   |
|----------|-----------------------|----------------------------------------------|-----------|
| CPLX-001 | ShallowModule         | "Modules Should Be Deep"                     | Ch. 4     |
| CPLX-002 | PassThroughVariable   | "Different Layer, Different Abstraction"     | Ch. 7     |
| CPLX-003 | InformationLeakage    | "Information Hiding"                         | Ch. 5     |
| CPLX-004 | ConjoinedMethods      | "General-Purpose Modules are Deeper"         | Ch. 6     |

---

## Nygard Mining Queue (planned, not yet implemented)

| Planned Code | Nygard Pattern / Anti-Pattern             | Chapter | Detectability | Notes                                    |
|--------------|-------------------------------------------|---------|---------------|------------------------------------------|
| STAB-???     | Circuit Breaker (missing pattern)         | Ch. 5   | Low           | Needs call-site wrapping detection, not just import check |
| STAB-???     | Integration Points (no fallback)          | Ch. 4   | Medium        | External call without except/default     |
| STAB-???     | Cascading Failures (sync chain depth)     | Ch. 4   | Medium        | 3+ sequential external calls             |
| STAB-???     | Self-Denial Attacks (cache stampede)      | Ch. 4   | Low           | Cache invalidation without staggering    |
| STAB-???     | Slow Responses (no deadline propagation)  | Ch. 4   | Low           | Timeout not passed to downstream calls   |
| STAB-???     | SLA Inversion                             | Ch. 4   | Low           | Requires runtime config, hard to lint    |
| STAB-???     | Fail Fast (late validation)               | Ch. 5   | Medium        | Validation deep in call chain            |
| STAB-???     | Bulkhead (shared pool)                    | Ch. 5   | Medium        | Single pool serving multiple concerns    |
| STAB-???     | Handshaking (no health check)             | Ch. 5   | Medium        | Service without health/ready endpoint    |

---

## Future Mining Queues

### Service Boundary Rules (SVC) -- Source: NEWMAN

Rules mined from *Building Microservices* (2nd ed.). Focused on coupling
anti-patterns detectable within a single Python project.

| Code      | Class Name            | Newman Pattern                               | Chapter   |
|-----------|-----------------------|----------------------------------------------|-----------|
| SVC-001   | HardcodedServiceURL   | Service discovery (hardcoded endpoints)      | Ch. 5     |
| SVC-002   | ChattyIntegration     | Chatty service boundary (N+1 API calls)      | Ch. 4     |
| SVC-003   | NoAPIVersioning       | API versioning absence                       | Ch. 7     |

### Newman Mining Queue (planned, not yet implemented)

| Planned Code | Newman Pattern                            | Chapter | Detectability | Notes                                    |
|--------------|-------------------------------------------|---------|---------------|------------------------------------------|
| SVC-???      | Shared database across services           | Ch. 4   | Low           | Requires multi-repo or monorepo analysis |
| SVC-???      | Synchronous coupling chains               | Ch. 4   | Medium        | Service-to-service sync HTTP calls       |
| SVC-???      | Missing contract tests                    | Ch. 7   | Medium        | API routes without corresponding tests   |

### Ousterhout -- *A Philosophy of Software Design*

*Implemented as CPLX-001..004 -- see "Complexity Rules (CPLX)" above.*

### Fowler -- *Patterns of Enterprise Application Architecture*

| Code    | Name                 | Severity | Implemented | Notes                                                           |
|---------|----------------------|----------|-------------|-----------------------------------------------------------------|
| DOM-001 | AnemicDomainModel    | WARN     | Yes         | Domain class with 5+ fields and zero behavior methods           |
| DOM-002 | WrongLayerPlacement  | WARN     | Yes         | View function with a 4+ branch if/elif chain (business logic)   |
| DOM-003 | ActiveRecordMisuse   | INFO     | Yes         | Model method calls requests / send_mail / celery / boto3 / smtp |
