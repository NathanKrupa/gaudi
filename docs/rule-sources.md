# Gaudi Rule Sources

This file is a **curated, hand-edited** record of the canonical source texts
Gaudi's rules draw from, the Architecture-90 curriculum that seeded the early
catalog, the philosophy scope audit, and mining queues for planned rules.

**This is not an exhaustive rule index.** The complete list of implemented
rules lives in [gaudi-rules.md](gaudi-rules.md), which is generated from the
live registry by `gaudi cheat-sheet` and cannot drift. Use that file when you
need "every rule." Use this one when you need the *why* — the source text,
the curriculum position, or the philosophy scope — for the rules it covers.

The **editorial doctrine** that governs which rules enter the catalog, how
their severity and thresholds are assigned, and when they are subsumed or cut
lives in [principles.md](principles.md). Footnotes in this file that explain
rule removals (e.g. "detection too weak", "subsumed by STAB-006") are
applications of those principles.

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

24 rules map directly to Fowler's smell catalog in *Refactoring* (2nd ed.), Chapter 3.
SMELL-025 extends the same naming principles to identifiers via Ousterhout Ch. 14.

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
| SMELL-025 | TemporalIdentifier   | *(extended)* Temporal markers in identifiers | OUSTRHOUT Ch. 14 |

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
| LOG-002    | SensitiveDataInLog      | OWASP: never log credentials/PII            | OWASP   |
| LOG-003    | InconsistentLoggerName  | Use getLogger(__name__) for hierarchy       | FWDOCS  |
| LOG-004    | PrintInsteadOfLog       | 12-Factor: logs are event streams           | 12FACT  |
| LOG-005    | NoCorrelationID         | Stitch log lines per request                | 12FACT  |
| OPS-002    | MissingPrecommit        | Pre-commit hooks for quality gates          | Day 6   |
| OPS-006    | DockerfileAntiPattern   | --no-cache-dir; deps copy before broad copy | 12FACT  |
| OPS-007    | NoDockerignore          | .dockerignore keeps secrets out of context  | 12FACT  |
| OPS-008    | HardcodedPortOrHost     | Bind host/port from config, not literals    | 12FACT  |
| OPS-009    | MissingHealthCheck      | Orchestrators need a health probe           | NYGARD  |

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
| DJ-ARCH-001     | BusinessLogicInSerializer| DRF         | Two Scoops of Django; ARCH90            |
| DJ-ARCH-002     | BusinessLogicInSignal    | Django      | Two Scoops of Django; ARCH90            |
| DJ-ARCH-003     | ModelCallsExternalService| Django      | ARCH90: inner layer never reaches out   |
| DJ-ARCH-004     | TransactionBoundaryViolation | Django  | Django docs: atomic + network I/O       |

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
| STAB-008  | IntegrationPointNoFallback | Integration Points (no fallback)        | Ch. 4     |
| STAB-009  | FailFastLateValidation | Fail Fast (validation deep in stack)        | Ch. 5     |
| STAB-010  | SharedResourcePool    | Bulkheads (single shared pool)               | Ch. 5     |
| STAB-011  | MissingHealthEndpoint | Handshaking (no health/ready endpoint)       | Ch. 5     |

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

### Security Rules (SEC) -- Source: OWASP Top 10

General Python security rules mined from the **structural slice** of the OWASP
Top 10 (issue #142) — patterns detectable from a single file's AST without
runtime data, taint analysis, or a whole-project graph. Principle 4 (Failure
must be named) explicitly calls for this slice: hostile input deserves the
same naming as a memory leak.

| Code     | Class Name              | Pattern / Anti-Pattern                                       | OWASP Source                    |
|----------|-------------------------|--------------------------------------------------------------|---------------------------------|
| SEC-002  | RawSQLInjection         | f-string / % / concat / .format passed to execute(), raw()   | A03:2021 Injection              |
| SEC-003  | HardcodedCredential     | Credential-named variable assigned to a string literal       | A07:2021 Identification Failures|
| SEC-004  | EvalExecUsage           | Built-in `eval()` or `exec()` invoked                        | A03:2021 Injection              |
| SEC-005  | UnsafeDeserialization   | `pickle.load(s)`, `marshal.load(s)`, `yaml.load` w/o SafeLoader | A08:2021 Software & Data Integrity |
| SEC-006  | SSRFVector              | Function parameter flows into `requests`/`httpx`/`urlopen` URL unsanitized | A10:2021 SSRF          |
| SEC-007  | WeakCryptography        | `hashlib.md5/sha1`; `random` module inside token/key/secret functions | A02:2021 Cryptographic Failures (CWE-327/338) |
| SEC-008  | InsecureSSLVerification | `verify=False` on HTTP calls; `ssl.CERT_NONE`                | A02:2021 Cryptographic Failures (CWE-295) |

**Overlap with `bandit`.** SEC-005/007/008 cover territory `bandit` also flags,
but Gaudi's versions (a) carry principle citations so the reader knows *why*
it matters, (b) ship a one-sentence actionable fix, and (c) are checked in the
same pass as the architectural rules — one tool, one report. SEC-007's
`random`-inside-security-function heuristic is narrower than bandit's
`B311` (which flags every `random` call), reducing false positives for
simulations, games, and sampling code.

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
| STAB-???     | Cascading Failures (sync chain depth)     | Ch. 4   | Medium        | 3+ sequential external calls             |
| STAB-???     | Self-Denial Attacks (cache stampede)      | Ch. 4   | Low           | Cache invalidation without staggering    |
| STAB-???     | Slow Responses (no deadline propagation)  | Ch. 4   | Low           | Timeout not passed to downstream calls   |
| STAB-???     | SLA Inversion                             | Ch. 4   | Low           | Requires runtime config, hard to lint    |

---

## General Mining Queue

| Planned Code | Pattern / Anti-Pattern                   | Source               | Detectability | Notes / Blocker                                                                |
|--------------|------------------------------------------|----------------------|---------------|--------------------------------------------------------------------------------|
| SMELL-???    | Defensive validation inside trust boundaries | Hunt & Thomas *Pragmatic Programmer* T24-25; Ousterhout Ch. 10 | Low | Requires type-flow or call-graph analysis. Cheapest slice: `RedundantTypeCheck` (isinstance on non-Optional param). See NathanKrupa/gaudi#132. |

## Future Mining Queues

### Service Boundary Rules (SVC) -- Source: NEWMAN

Rules mined from *Building Microservices* (2nd ed.). Focused on coupling
anti-patterns detectable within a single Python project.

| Code      | Class Name            | Newman Pattern                               | Chapter   |
|-----------|-----------------------|----------------------------------------------|-----------|
| SVC-001   | HardcodedServiceURL   | Service discovery (hardcoded endpoints)      | Ch. 5     |
| SVC-002   | ChattyIntegration     | Chatty service boundary (N+1 API calls)      | Ch. 4     |
| SVC-003   | NoAPIVersioning       | API versioning absence                       | Ch. 7     |
| SVC-004   | SharedDatabasePattern | Shared database coupling across Django apps  | Ch. 4     |
| SVC-005   | SynchronousCouplingChain | Sync fan-out to multiple upstream services | Ch. 4     |
| SVC-006   | MissingContractTests  | HTTP client module without paired test       | Ch. 7     |

### Ousterhout -- *A Philosophy of Software Design*

*Implemented as CPLX-001..004 -- see "Complexity Rules (CPLX)" above.*

### Fowler -- *Patterns of Enterprise Application Architecture*

| Code    | Name                 | Severity | Implemented | Notes                                                           |
|---------|----------------------|----------|-------------|-----------------------------------------------------------------|
| DOM-001 | AnemicDomainModel    | WARN     | Yes         | Domain class with 5+ fields and zero behavior methods           |
| DOM-002 | WrongLayerPlacement  | WARN     | Yes         | View function with a 4+ branch if/elif chain (business logic)   |
| DOM-003 | ActiveRecordMisuse   | INFO     | Yes         | Model method calls requests / send_mail / celery / boto3 / smtp |

---

## Philosophy Scope Audit

**Status:** Phase 0b. Editorial only; no engine wiring yet.

Every implemented rule in this registry carries, in addition to its source
provenance, a **philosophy scope**: the set of architectural schools under
which the rule is defensible. The scope is either `universal` (the rule
descends from Gaudi's three pillars and holds in every school) or a
specific list of schools (the rule depends on axioms that not every school
accepts).

The eight schools are defined in [docs/philosophy/](philosophy/). Each
non-universal tag below appeals to the axiom sheet that justifies the
scope decision.

### Methodology

A rule is **universal** if and only if removing it would make at least one
of the three pillars (Truthfulness, Economy, Cost-honesty) less defensible
in *every* school. A rule is **scoped** if at least one school's prime
axiom actively contradicts it — not merely declines to emphasize it, but
would label the rule wrong when applied to an exemplary codebase of that
school.

The test is strict: tolerance is not contradiction. A Pragmatic codebase
may not care about interface segregation, but it does not consider the
rule *wrong* on a Classical codebase. That is tolerance, and the rule
remains universal. A Data-Oriented codebase actively rejects
"replace loop with pipeline" because fused manual loops are cache-coherent
and pipelines allocate — that is contradiction, and the rule is scoped
away from Data-Oriented.

### Summary

Of the ~125 currently implemented rules:

- **~102 (82%) are universal** — they descend from the three pillars and
  hold in every school.
- **~23 (19%) are scoped** — they depend on school-specific axioms.
  (Originally 22 at Phase 1; `ARCH-013 FatScript` was moved to scoped
  when the Unix exemplar surfaced it as a false positive.)

This result is load-bearing: it validates the prediction that philosophy
scoping needs only a small amount of machinery, because the catalog is
already mostly universal. The engine change (Phase 1) can be small
because the audit is small.

### Scoped Rules (the 23)

These rules have non-universal scope. Each entry names the schools under
which the rule remains defensible and cites the axiom sheet that justifies
the exclusion. Rules not listed here are universal.

| Rule | Scoped to (schools) | Excluded from | Justification |
|---|---|---|---|
| **SMELL-009** FeatureEnvy | classical, convention | functional, data-oriented, unix, event-sourced | Method-envy is an OOP smell about data ownership. Under [functional.md](philosophy/functional.md) and [data-oriented.md](philosophy/data-oriented.md), functions do not own data at all — the concept does not translate. Unix modules are namespaces, not owners. |
| **SMELL-011** PrimitiveObsession | classical, functional, convention, event-sourced | unix, data-oriented | [unix.md](philosophy/unix.md) uses plain dicts/tuples at module boundaries as a virtue; [data-oriented.md](philosophy/data-oriented.md) prefers packed primitives for cache locality. Wrapping primitives in domain types is contrary to both axioms. |
| **SMELL-013** Loops | classical, pragmatic, functional, unix, resilient, convention, event-sourced | data-oriented | Fowler's smell advocates pipeline operations; [data-oriented.md](philosophy/data-oriented.md) prefers manual fused loops because pipelines allocate intermediate collections and thrash cache. Direct contradiction of the Data-Oriented catechism. |
| **SMELL-014** LazyElement | pragmatic, unix, functional, data-oriented | classical, convention, resilient, event-sourced | Pragmatic and Unix aggressively remove pass-through abstractions; Classical and Convention often want the thin seam "for future extensibility" — exactly the speculative generality [pragmatic.md](philosophy/pragmatic.md) refuses. Resilient/Event-Sourced sometimes need the seam for supervision or aggregate boundaries. |
| **SMELL-015** SpeculativeGenerality | pragmatic, unix, functional, data-oriented | classical, convention, resilient, event-sourced | The canonical Pragmatic rule — see [pragmatic.md](philosophy/pragmatic.md) catechism #1. Classical and Convention both permit (even encourage) extensibility hooks that Pragmatic rejects until a second caller materializes. |
| **SMELL-018** MiddleMan | pragmatic, unix, functional | classical, convention, resilient, data-oriented, event-sourced | Similar to LazyElement but specifically about delegation wrappers. Classical sometimes wants the indirection for decoupling. Resilient uses wrapper layers for circuit breakers and instrumentation. Event-Sourced uses them around aggregates. |
| **SMELL-020** LargeClass | classical, pragmatic, functional, unix, resilient, data-oriented, event-sourced | convention | [convention.md](philosophy/convention.md) explicitly embraces fat models as the blessed Django/Rails pattern (see catechism #1 and the DJ-ARCH-001/002 rules enforcing the same). A "large class" in Django is a correctly-populated ActiveRecord, not a smell. |
| **SMELL-022** DataClassSmell | classical, convention | functional, data-oriented, event-sourced, unix | Fowler treats "classes that are just data" as anemic. [functional.md](philosophy/functional.md) catechism #1 makes frozen dataclasses the *primary* building block. [data-oriented.md](philosophy/data-oriented.md) treats pure data as the entire point. [event-sourced.md](philosophy/event-sourced.md) requires events to be exactly this shape. Direct axiom conflict. |
| **SMELL-023** RefusedBequest | classical, convention | functional, data-oriented, unix, event-sourced | Inheritance-specific smell. Schools that reject inheritance as a reuse mechanism have no bequest to refuse. See [functional.md](philosophy/functional.md) rejected alternative #4. |
| **LOG-004** PrintInsteadOfLog | classical, pragmatic, functional, resilient, data-oriented, convention, event-sourced | unix | [unix.md](philosophy/unix.md) catechism #2: text flowing through stdout *is* the universal interface. A Unix program that logs to stderr and emits data on stdout is correct; forcing it to use a structured logger for its data stream is the antithesis of the axiom. |
| **LOG-005** NoCorrelationID | classical, pragmatic, functional, resilient, convention, event-sourced | unix, data-oriented | Correlation IDs matter for request-serving long-lived systems. [unix.md](philosophy/unix.md) one-shot scripts and [data-oriented.md](philosophy/data-oriented.md) batch jobs are neither. Firing this rule on a `gaudi check` run is a false positive. |
| **OPS-009** MissingHealthCheck | classical, pragmatic, functional, resilient, convention, event-sourced | unix, data-oriented | Same reasoning as LOG-005: health checks are a concept for long-lived services. One-shot scripts and batch jobs do not have a meaningful "health" to check. |
| **ARCH-002** GodModel | classical, pragmatic, functional, unix, resilient, data-oriented, event-sourced | convention | Same as SMELL-020: Convention explicitly blesses fat models. |
| **SCHEMA-001** MissingTimestamps | classical, convention | functional, unix, data-oriented, event-sourced, pragmatic, resilient | Pragmatic refuses premature timestamps until a requirement demands them. [event-sourced.md](philosophy/event-sourced.md) notes that events have timestamps; current-state rows in a projection do not need them because the log already carries time. |
| **STRUCT-001** SingleFileModels | classical, pragmatic, functional, unix, resilient, data-oriented, event-sourced | convention | Convention's `models.py` is load-bearing — it is exactly where the framework expects models to live. Splitting them because the file grew large is fighting the framework, which [convention.md](philosophy/convention.md) explicitly forbids. |
| **FLASK-STRUCT-001** NoAppFactory | classical, convention | others | Framework-specific best practice. Only meaningful under Classical (testability via factory) and Convention (framework idiom). |
| **DRF-SCALE-001** NoThrottling | classical, resilient, convention | pragmatic, functional, unix, data-oriented, event-sourced | Throttling is a resilience pattern for public APIs. Pragmatic adds it when abuse materializes, not speculatively. Unix/Data-Oriented/Event-Sourced systems typically have different trust boundaries. |
| **STAB-008** IntegrationPointNoFallback | classical, resilient, convention, event-sourced | pragmatic, unix, functional, data-oriented | Fallbacks are Resilient's catechism #5. [pragmatic.md](philosophy/pragmatic.md) considers adding fallbacks before an outage materializes to be speculative generality. Unix's "worse is better" tolerates partial failure; Data-Oriented treats this as out-of-scope entirely. |
| **STAB-010** SharedResourcePool | classical, resilient, event-sourced | pragmatic, functional, unix, data-oriented, convention | Bulkheading is Nygard's canonical pattern and Resilient's catechism #4. The schools listed as excluded either do not operate at the scale where bulkheads matter or consider the pattern premature. |
| **STAB-011** MissingHealthEndpoint | classical, pragmatic, functional, resilient, convention, event-sourced | unix, data-oriented | Same as OPS-009. |
| **ASYNC-004** NoGracefulShutdown | classical, pragmatic, functional, resilient, convention, event-sourced | unix, data-oriented | Graceful shutdown matters for long-lived processes. One-shot Unix scripts and batch Data-Oriented jobs terminate by completing, not by receiving a signal. |
| **DOM-001** AnemicDomainModel | classical, convention | functional, data-oriented, event-sourced, unix, pragmatic | Fowler's DDD-era critique of data-without-behavior. Every school listed as excluded uses anemic records deliberately: [functional.md](philosophy/functional.md) catechism #1, [data-oriented.md](philosophy/data-oriented.md) catechism #7, [event-sourced.md](philosophy/event-sourced.md) catechism #1. Pragmatic considers the extraction-of-behavior-into-methods premature until a caller needs it. |
| **ARCH-013** FatScript | classical, pragmatic, functional, resilient, data-oriented, convention, event-sourced | unix | Under [unix.md](philosophy/unix.md) catechism #1, "the script IS the service." ARCH-013's premise ("extract the business logic to a service") has no application when the script is already the smallest honest unit of work — a small program that reads stdin, calls one helper function, and writes stdout. Evidence: `tests/philosophy/unix/canonical/` tripped this rule three times on `main()` functions that were pure argparse + stdin loop + atomic write plumbing. Scope was added after writing the Unix exemplar surfaced the false positive. |

### Universal Rules (the ~101)

All other implemented rules are universal. A rule is universal if it
descends directly from the three pillars and the fourteen principles of
[principles.md](principles.md) in a form every school would defend. The
universal rules include:

- **All of SMELL** except 009, 011, 013, 014, 015, 018, 020, 022, 023. The
  remaining Fowler smells (mysterious names, long functions, long
  parameter lists, global data, duplicated code, shotgun surgery, data
  clumps, repeated switches, temporary field, message chains, alternative
  interfaces, comments, temporal identifiers) appeal directly to
  Truthfulness #3 and Economy #6 and hold in every school.
- **All of STRUCT** (010–013, 020–021) except 001. Packaging, pyproject,
  entry points, lockfiles, return types, and magic strings are universal
  infrastructure concerns.
- **All of ARCH** (010, 011, 020, 022) except 002 and 013. Import direction,
  connector-logic leakage, fat scripts, env leakage, and scattered config
  are Principle #1, #5, #9, and #10 applied directly.
- **All of ERR** (001–006). Principle #4 (failure must be named) is a
  three-pillar claim; no school denies it.
- **All of LOG** (001–003) except 004 and 005. Structured logging,
  sensitive-data-in-log, and logger-naming hierarchy are Principle #13
  applied directly.
- **All of OPS** (002, 006–008) except 009. Pre-commit, Docker hygiene,
  host/port config are Principle #14 (reversibility) and Principle #5
  (state must be visible).
- **ARCH-001 NoTenantIsolation** and **ARCH-003 NullableForeignKeySprawl**.
  Multi-tenant isolation is a security concern; nullable-FK sprawl is a
  data-modeling concern that survives translation.
- **All of IDX** (001–002). Missing indexes are Principle #4 (unbounded
  result sets are a form of unnamed failure).
- **SCHEMA-002, SCHEMA-003**. Schema-level bounds concerns.
- **SEC-001**. Security is universal.
- **DJ-SEC-001**, **DJ-SEC-002**, **DJ-STRUCT-001**, **FAPI-ARCH-001**,
  **FAPI-SCALE-001**, **SA-SCALE-001**, **CELERY-ARCH-001**,
  **CELERY-SCALE-001**, **PD-ARCH-001**, **PD-SCALE-001**,
  **HTTP-SCALE-001**, **PYD-ARCH-001**. Library-specific rules that
  enforce the target library's own best practices; no school contradicts
  the library's own documentation of itself.
- **All of TEST** (STRUCT-001/002/003, SCALE-001, ARCH-001/002/003).
  Principle #12 (tests are the specification) is universal.
- **All of AWS** (ARCH-001, ERR-001, SCALE-001). Cloud infrastructure
  rules grounded in Principle #4 and #5.
- **DRF-SEC-001**. Security.
- **DJ-ARCH-001, 002, 003, 004**. Business logic in the wrong layer is a
  Principle #9 / #10 concern that every school defends.
- **All of PY314** (001–006). Language compatibility; not philosophical.
- **All of STAB** (001, 003–007, 009) except 008, 010, 011. Principle #4
  applied to resource exhaustion and retry discipline; every school
  defends the bounded loop and the owned resource.
- **ASYNC-001, 002, 003**. Shared mutable state, async context managers,
  and sync/async mixing are Principle #5 and #4.
- **All of API** (001–004). Pagination, consistent return types, ID
  leakage, and error schemas are Principle #4 and #11 (reader is user).
- **All of DEP** (001–004). Dependency direction and stability are
  Principle #9 applied to the import graph.
- **All of CPLX** (001–004). Ousterhout's module-shape heuristics are
  Principle #7 (layers must earn their existence).
- **DOM-002 WrongLayerPlacement**, **DOM-003 ActiveRecordMisuse**.
  Business logic in views and models calling external services are
  Principle #9 and #10.

### What the audit tells us

Three observations worth recording:

1. **Universality is the rule, scope is the exception.** ~82% universal
   validates the approach of treating the principles as the core and the
   schools as material expressions. If the audit had come back 50/50, the
   engine change would have been a much larger project. Because it did
   not, the engine change can be a one-field addition to `Rule`.

2. **Two schools do most of the work of scoping.** Convention and
   Data-Oriented account for the majority of the exclusions. Convention
   blesses patterns (fat models, single-file models, blessed timestamps)
   that other schools treat as smells. Data-Oriented refuses abstractions
   (pipelines, wrapped primitives, health checks on batch jobs) that
   other schools assume. These are the two schools a Gaudi engine change
   most urgently needs to respect.

3. **The hardest cases are Pragmatic-vs-Classical on extensibility.**
   SMELL-014, SMELL-015, and SMELL-018 are the places where the two
   schools genuinely disagree about whether a thin layer is a smell or
   a seam. The audit resolves them in favor of Pragmatic (the rules are
   Pragmatic-scoped), which is consistent with Gaudi's own doctrine —
   [principles.md](principles.md) Principle #6 explicitly favors "the
   best line is the one not written" over preemptive extensibility.

The audit is a snapshot, not a verdict. As the canonical-task exemplars
are written (Phase 0d+), a cross-fixture test may reveal that a rule
tagged as universal actually fires incorrectly on a faithful exemplar
of some school. When that happens, the audit updates, the engine's scope
table updates, and a new fixture goes into the test matrix to enforce
the correction. The audit is the first draft of a living specification,
not the final word.
