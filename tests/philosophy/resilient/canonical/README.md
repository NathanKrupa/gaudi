# Resilience-First / Distributed Systems — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/resilient.md](../../../../docs/philosophy/resilient.md)
**Rubric score:** 10/10

The sixth reference implementation of the canonical task, and the
first written under an axiom whose prime concern is *operational*
rather than structural. Classical organizes code. Pragmatic refuses
premature abstraction. Functional banishes mutation. Unix composes
independent programs. Convention follows the framework idiom.
**Resilient starts from the observation that every call can fail, every
process can die, every dependency can stop answering — and designs
around that fact before it designs for the happy path.**

Every trust-boundary call in this pipeline passes through explicit
timeouts, bounded retries with exponential backoff, a Nygard-style
three-state circuit breaker, and idempotency-keyed state mutation.
Every log line is structured JSON with a correlation ID that
propagates into ThreadPoolExecutor workers via
`contextvars.copy_context()`. A health check tests actual capability
— a real pricing lookup and a real inventory read — rather than
reporting that the process is alive.

The exemplar uses **stdlib only** (no `tenacity`, `circuitbreaker`,
`backoff`, or `structlog`). The reliability primitives are written
out in [reliability.py](reliability.py) because the rubric requires
the machinery to be a real piece of the design, not a stub with a
TODO or a `pip install` away.

---

## Running it

```bash
conda run -n ai-assistants pytest tests/philosophy/resilient/ -v
```

Twenty tests, split into two groups:

1. **Acceptance** — every row of `seed_data.TEST_ORDERS` plus two
   cross-order persistence tests. These prove the reliability
   machinery does not break the business logic underneath.
2. **Rubric-enforcing** — each clause of the
   [resilient.md §8 rubric](../../../../docs/philosophy/resilient.md)
   is pinned by at least one test. If a future refactor removes a
   timeout, shortens a retry bound, or silently drops a circuit
   breaker, the test fails loudly.

| Rubric clause | Pinning test |
|---|---|
| #1 Explicit timeouts on every dependency call | `test_every_dependency_call_has_explicit_timeout` + `test_pricing_timeout_triggers_retry_then_reject` |
| #2 Bounded retries with exponential backoff | `test_retry_respects_max_attempts` + `test_retry_backoff_is_exponential` |
| #3 Idempotency keys on state-mutating calls | `test_idempotency_key_is_deterministic_and_replays_safely` |
| #4 Structured logs + correlation IDs | `test_structured_log_tags_every_stage_with_correlation_id` |
| #5 Circuit breaker guards a flaky dependency | `test_notification_breaker_opens_after_threshold` |
| #6 Named constants, not magic numbers | `test_every_dependency_call_has_explicit_timeout` |
| #7 Real-capability health check | `test_healthcheck_reports_real_capability` |
| #8 Subsystem failure modes as explicit paths | `test_notification_failure_does_not_fail_the_order` |

---

## Directory shape

```
canonical/
├── README.md       # this file
├── config.py       # named constants: timeouts, retries, thresholds
├── telemetry.py    # structured logging + correlation-ID context manager
├── reliability.py  # timeout, retry/backoff, circuit breaker, idempotency key
├── dependencies.py # in-process stand-ins for external systems
└── pipeline.py     # process_order + healthcheck, wrapping everything above
```

Five code files. Stdlib only. Zero non-standard imports.

Compared to the five already-landed exemplars:

| Property | Classical | Pragmatic | Functional | Unix | Convention | Resilient |
|---|---|---|---|---|---|---|
| Files | 8 | 1 | 3 | 4 | 8 (Django) | 5 |
| Impl lines | ~450 | ~180 | ~220 | ~280 | ~400 | ~550 |
| Classes | 12 | 0 | 10 records | 0 | 6 models + 2 mgrs | 2 |
| Non-stdlib deps | 0 | 0 | 0 | 0 | django | **0** |
| Most distinctive claim | layered OOP tree | straight-through function | pure composition | stdio pipeline | manager method composition root | **real reliability machinery, not stubs** |

The Resilient column's distinctive claim is **that every reliability
primitive is implemented for real and exercised by at least one
test.** The rubric rejects an exemplar where circuit breakers and
retries are declared in a comment and hand-waved in the code; this
exemplar has a Nygard-style three-state breaker with a proper
cooldown timer, a retry loop that records actual sleep durations,
and a health check whose probe outcome is observable by tests.

---

## Rubric score against [resilient.md](../../../../docs/philosophy/resilient.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | Every external call has an explicit timeout with a reasoned value | ✓ | `config.PRICING_TIMEOUT_SECONDS`, `INVENTORY_TIMEOUT_SECONDS`, `NOTIFICATION_TIMEOUT_SECONDS`. Every call goes through `reliability.call_with_timeout()` with an explicit label and duration. |
| 2 | Retries are bounded and use exponential backoff | ✓ | `reliability.retry_with_backoff(max_attempts=3, initial_backoff=0.05, multiplier=2.0)`. `test_retry_backoff_is_exponential` asserts the observed sleep sequence is [0.01, 0.02, 0.04] under a test override. |
| 3 | State-mutating calls carry an idempotency key | ✓ | `reliability.idempotency_key(order)` derives a SHA-256 digest from the canonical JSON of order_id + customer_id + sorted line_items + promo_code. `dependencies.reserve_inventory` persists the key in a side table and suppresses replays. |
| 4 | Every log line is structured and correlation-tagged | ✓ | `telemetry.log()` emits JSON with `ts`, `level`, `event`, `correlation_id`, plus caller-supplied fields. Correlation ID lives in a `ContextVar` and propagates into ThreadPoolExecutor workers via `contextvars.copy_context()`. `test_structured_log_tags_every_stage_with_correlation_id` pins this end-to-end. |
| 5 | At least one circuit breaker guards a flaky dependency | ✓ | `reliability.CircuitBreaker` is a proper CLOSED/HALF_OPEN/OPEN state machine. `pipeline.NOTIFICATION_BREAKER` wraps every notification publish. `test_notification_breaker_opens_after_threshold` forces the broker to fail `CIRCUIT_BREAKER_FAILURE_THRESHOLD` times and asserts the breaker transitions to OPEN and refuses the next call. |
| 6 | Timeouts, retries, breaker thresholds are named constants | ✓ | All seven knobs live in [config.py](config.py), each with a comment explaining the reasoned value. No magic numbers in the pipeline. |
| 7 | Health check tests actual capability | ✓ | `pipeline.healthcheck()` performs a real pricing lookup, a real inventory read, and reports the notification breaker state. `test_healthcheck_reports_real_capability` asserts the happy case returns `ok` and a synthetic pricing failure returns `degraded` with a specific failure reason naming the subsystem. |
| 8 | No shared mutable state crosses a trust boundary without an owner | ✓ | The `world` dict is owned by the pipeline process. The `dependencies.reserve_inventory` function is the sole writer (atomic under the GIL for single-threaded mutation); other dependency functions read-only. Comments at the top of `dependencies.py` document the trust boundary. |
| 9 | Subsystem failure modes are documented in the code as real paths | ✓ | The docstring of `pipeline.process_order` enumerates every failure mode: pricing fail → retry → reject; inventory read fail → retry → reject; inventory reserve fail → do not retry; notification fail → swallow, log at WARN, order still confirmed; circuit open on notification → same treatment. Each path is a real `except` block, not a future TODO. |
| 10 | System produces enough telemetry to diagnose a realistic failure | ✓ | Every stage emits a structured log line, every retry attempt is recorded with the attempt number, every circuit state transition is logged, and every notification degradation names the exception type. `test_structured_log_tags_every_stage_with_correlation_id` proves the telemetry is machine-queryable via the in-process sink. |

**10/10.**

---

## The findings on this exemplar — and what they teach

Running `gaudi check` on this exemplar produces 6 distinct Python-pack
rule codes plus 6 project-level OpsPack findings. **All 6 Python-pack
findings are universal — not one scoped rule fires.** That is the
surprising and valuable result.

| Rule | Count | Disposition |
|---|---|---|
| `SMELL-003 LongFunction` | 6 | `call_with_timeout` 35 lines, `retry_with_backoff` 36, `_run_stages` 39, `_reserve_and_confirm` 34, `_notify` 29, `reserve_inventory` 35. The reliability primitives and pipeline stages cannot be shorter without hiding the machinery the rubric demands. Universal and honest. |
| `SMELL-008 ShotgunSurgery` | 1 | `NOTIFICATION_BREAKER` is referenced in `_notify`, `reset_notification_breaker`, `healthcheck`, and at module scope. A module-level singleton is the correct shape for a single-process circuit breaker; consolidation into a class would not help because the breaker *is* already a class — the shotgun is in the module-level handle to it. Universal, accepted. |
| `SMELL-010 DataClumps` | 2 | `(order, world, now)` and `(correlation_id, idem_key, order)` appear together in multiple stage functions. Genuine data-clump smell, but wrapping them in a context object would add a layer that reads worse than the tuple threading. INFO, accepted. |
| `STRUCT-021 MagicStrings` | 14 | Repeated dict keys in the plain-data wire format (`sku`, `order_id`, `status`, `customer_id`, `HALF_OPEN`, `WARN`). Same trade-off every plain-data exemplar makes — Unix, Pragmatic, Functional, and Convention all accept this as the honest cost of not typing the wire format. Universal. |
| `CPLX-002 PassThroughVariable` | 1 | `world` is threaded through 9 functions in `pipeline.py`. The pipeline genuinely does need the world dict at every stage; extracting it to a class attribute would be a micro-optimization that hid the data flow. Universal, accepted. |
| `CPLX-003 TooManyParameters` | 1 | `process_order(order, world, now)` plus its helpers grow the parameter count. The alternative is a class whose only method is `process_order`, which under pragmatic/functional/unix would immediately trip SMELL-014 LazyElement. The tuple is the lesser cost. Universal, accepted. |

**No STAB-* rule fires.** This is worth naming because it is the
first thing you might expect from a Resilient exemplar — the STAB
family *should* be stress-tested by the exemplar most aligned with
its axiom. The reason none fire is structural: STAB-008
`IntegrationPointNoFallback` pattern-matches on `requests.get` /
`httpx.get` / `urllib3` calls, STAB-001 `UnboundedResultSet` matches
on SQLAlchemy / Django ORM chains, STAB-007 `UnboundedThreadPool`
matches on bare `ThreadPoolExecutor()` without `max_workers`, and
STAB-011 `MissingHealthEndpoint` is a project-level rule that
checks for an endpoint file rather than a function. This exemplar's
in-process dependencies and `max_workers=1` executor usage sidestep
every one of those pattern matchers cleanly — which is itself the
useful signal: **the STAB family is detector-limited to
third-party library integration patterns and does not yet detect
stdlib-level reliability primitives.** That is a known limitation of
the audit, not a bug in this exemplar.

### Why no audit revision this PR

Unlike Unix (which forced ARCH-013 → scoped away from unix) and
Convention (which surfaced six detector precision issues), the
Resilient exemplar produces zero scoped-rule misfires and zero new
rule-shape evidence. Every finding is universal; every finding is
correct; every finding applies identically to the five exemplars
already landed under the same rules.

The contribution of this PR to the audit is therefore **negative
evidence**: the existing audit handles a faithful Resilient
implementation cleanly with no new tag revisions needed. That is a
useful property in a rule system — not every school should force
audit revisions, and the ones that don't are control conditions for
the ones that do.

---

## Matrix contribution

The Resilient exemplar joins Pragmatic and Functional as a
**scope-invariant control condition.** Running `gaudi check` under
every one of the eight schools produces the identical finding set:

```
{CPLX-002, CPLX-003, SMELL-003, SMELL-008, SMELL-010, STRUCT-021}
```

plus the project-level OpsPack findings (`OPS-002..005`,
`STRUCT-011`, `STRUCT-013`) that fire on any directory without a
repository-level `pyproject.toml`, `README`, `CODEOWNERS`, etc. The
Python-pack finding set is byte-identical across all eight schools.

This is pinned by `test_scope_invariant_exemplar_is_stable_across_schools`,
which is parametrized over `SCOPE_INVARIANT_EXEMPLARS` and now runs
against three exemplars instead of two. The three exemplars span
the widest structural range of any group in the matrix:

| Exemplar | Files | Impl lines | Classes | Shape |
|---|---|---|---|---|
| Pragmatic | 1 | ~180 | 0 | one straight-through function |
| Functional | 3 | ~220 | 10 (records) | pure composition of frozen records |
| Resilient | 5 | ~550 | 2 | concurrent pipeline with reliability primitives |

All three produce finding sets that are scope-invariant. If a future
PR accidentally scopes a supposedly-universal rule to only some
schools, at least one of these three exemplars will diverge and
break the test loudly.

### The Resilient exemplar's load-bearing matrix row

Added to `test_philosophy_matrix.py`:

- 8 rows in `EXEMPLAR_EXPECTATIONS` (one per school), each asserting
  `RESILIENT_REQUIRES_EVERYWHERE` fires and `RESILIENT_FORBIDS_EVERYWHERE`
  stays silent.
- `test_resilient_exemplar_covered_by_every_school` — drift catcher.
- `test_scope_invariant_exemplar_is_stable_across_schools` now
  parametrizes over three exemplars, so the Resilient finding set
  must match every other school's Resilient finding set.

---

## See also

- [docs/philosophy/resilient.md](../../../../docs/philosophy/resilient.md) — The axiom sheet.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [docs/rule-registry.md](../../../../docs/rule-registry.md) — The rule audit, unchanged by this PR.
- [tests/philosophy/classical/canonical/README.md](../../classical/canonical/README.md) — Classical exemplar (layered OOP).
- [tests/philosophy/pragmatic/canonical/README.md](../../pragmatic/canonical/README.md) — Pragmatic exemplar (one function).
- [tests/philosophy/functional/canonical/README.md](../../functional/canonical/README.md) — Functional exemplar (pure records).
- [tests/philosophy/unix/canonical/README.md](../../unix/canonical/README.md) — Unix exemplar (stdio pipeline).
- [tests/philosophy/convention/canonical/README.md](../../convention/canonical/README.md) — Convention exemplar (Django).
