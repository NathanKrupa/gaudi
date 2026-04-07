# Gaudi Principles

> *Not just structurally sound. Beautiful.*

These are the first principles that govern Gaudi — both as a linter (which rules
we accept, how we tune them, when we cut them) and as a portable design doctrine
that any project can adopt. They are the **positive** complement to the rule
catalog. The catalog says *what* we forbid; this document says *why*, and from
that *why* every borderline judgment should be derivable.

---

## The Method: Hanging Chains

Antoni Gaudi designed La Sagrada Familia by hanging weighted chains from a
ceiling and letting gravity reveal the curves a load-bearing arch would need.
Inverted, the chain became the column. The structure was discovered by physics,
not invented by taste.

These principles are derived the same way. They were not chosen from a textbook.
They were extracted from evidence already present in this project:

- Rules we **kept** (what survived contact with real code).
- Rules we **removed** (`STAB-002`, `SA-ARCH-001`, `HTTP-ARCH-001` — what
  collapsed under its own weight).
- Rules we **deferred to the mining queue** (what we wanted but could not yet
  detect honestly).
- Issues we **filed** (#68, #67 — where pain showed us a missing principle).
- The **shape of the data model** (`Finding` requires `recommendation`;
  `Severity` is three-tiered; `Category` is closed) — design decisions that
  encoded beliefs the documentation never stated.

When a new design question arises — in Gaudi or in any other project — name
the principle that decides it. If no principle decides it, the principle is
either missing or in conflict, and the question is escalated, not coin-flipped.

---

## The Three Pillars

Beautiful software rests on three load-bearing claims. Every numbered principle
below is a consequence of one of them.

| Pillar | Claim | Failure Mode |
|---|---|---|
| **I. Truthfulness** | The code must not lie about itself or its domain. | The reader (human or AI) is misled and the system rots invisibly. |
| **II. Economy** | The least code that does the work is the right code. | Every excess line is a future tax — to read, to test, to update. |
| **III. Cost-honesty** | Every line is a forever debt. Design with full awareness of long-term consequences. | Today's convenience becomes tomorrow's six-month refactor. |

Beauty is what remains when all three are honored at once. It is not added.
It is the residue of removing whatever does not earn its place.

---

## Pillar I — Truthfulness

### 1. The structure tells the story

> *The shape of a system — file layout, module boundaries, dependency graph,
> naming — must reveal what the system actually does.*

A project where you cannot guess from the directory tree what each part is for
is a project whose structure is lying. The reader has to trace imports to find
the truth, which means the truth was hidden by accident. Layout is documentation
that cannot drift, because the compiler reads it too.

- **In projects:** Three layers, arrows inward only. OUTER (entry points)
  imports MIDDLE (services) imports INNER (connectors and models). Never
  reverse. A `scripts/` file longer than 20 lines of non-CLI logic is a fat
  script and the logic belongs in a service.
- **In Gaudi:** `ARCH-010 ImportDirectionViolation`, `ARCH-013 FatScript`,
  `STRUCT-001 SingleFileModels`, `DEP-001 CircularImport`.

### 2. One concept, one home

> *Every concept lives in exactly one location and is reachable by name.*

Duplication is a lie about which copy is canonical. Scatter is a lie about who
owns the concept. Both force the next reader (or the next bug) to ask "which
version is real?" — a question good design refuses to allow.

- **In projects:** The same logic in two files is a missing service. Extract
  immediately, do not copy. The same constant in two files is a missing
  configuration entry. The same SQL fragment in two files is a missing query
  builder.
- **In Gaudi:** `SMELL-002 DuplicatedCode`, `ARCH-022 ScatteredConfig`,
  `STRUCT-021 MagicStrings`.

### 3. Names are contracts

> *A name commits to what a thing is — and what it is not.*

A misleading name is the most expensive lie a codebase can tell, because the
reader trusts it and acts on it. A vague name is a refusal to commit. Names
should describe *what*, never *how* (`ZodValidator`), *when* (`NewAPI`), or
*who-used-to-be-here* (`LegacyClient`).

- **In projects:** Rename whenever the meaning drifts from the name. Cost of
  the rename is one PR; cost of leaving it is every future reader. Comments
  must not contain "improved", "new", "old", "legacy", or "refactored from".
  Files start with `ABOUTME:` so they are greppable.
- **In Gaudi:** `SMELL-001 MysteriousName`, `SMELL-024 Comments`.

### 4. Failure must be named

> *Silence about failure is a lie. Every external call has a timeout, every
> loop has a bound, every resource has an owner.*

Code that does not state how it fails has not been designed; it has been
wished into existence. The wish holds until production load arrives.

- **In projects:** Every HTTP call has a timeout. Every retry has backoff.
  Every database query has a result-set bound. Every file handle, lock, and
  session is closed by `with`. Bare `except:` is forbidden; catch the
  exception you actually expect.
- **In Gaudi:** `STAB-001 UnboundedResultSet`, `STAB-003 RetryWithoutBackoff`,
  `STAB-004 UnboundedCache`, `STAB-006 UnmanagedResource`,
  `STAB-007 UnboundedThreadPool`, `HTTP-SCALE-001 RequestsNoTimeout`,
  `ERR-001 BareExcept`, `ERR-003 ErrorSwallowing`.

### 5. State must be visible

> *Hidden mutable state is a lie about what a function does.*

A function that reads a global, mutates a singleton, or pulls config from
`os.getenv()` cannot be tested without staging the world. It has dependencies
it refuses to declare. Make them parameters.

- **In projects:** Classes take dependencies as `__init__` parameters. Only
  factory functions or composition roots read environment variables. Pure
  functions are the most beautiful code; when state is necessary, it is
  explicit, owned, and observable.
- **In Gaudi:** `ARCH-020 EnvLeakage`, `SMELL-005 GlobalData`,
  `SMELL-006 MutableData`, `PYD-ARCH-001 PydanticMutableDefault`.

---

## Pillar II — Economy

### 6. The best line is the one not written

> *YAGNI before extensibility. The cheapest code is the code that does not
> exist.*

Speculative generality (the trait, the registry, the configuration knob "in
case we need it") is a debt taken on for a benefit that may never arrive. If
the second use case shows up, the abstraction can be extracted then — at which
point it will fit, because it has two real shapes to fit, not one imagined one.

- **In projects:** Three similar lines of code is better than a premature
  abstraction. Two implementations is when you start considering the third
  could share. Never design for a hypothetical caller.
- **In Gaudi:** `SMELL-015 SpeculativeGenerality`, `SMELL-014 LazyElement`,
  `SMELL-018 MiddleMan`.

### 7. Layers must earn their existence

> *Every layer of abstraction must pay for itself in clarity. Pass-through
> layers are decoration pretending to be design.*

Ousterhout's "deep modules" principle: a module is good when it hides a lot
behind a small interface. A module that exposes a large interface concealing
little adds cost without paying for itself. The same applies to wrappers,
adapters, and any class whose only job is to forward calls.

- **In projects:** Before adding a layer, name what it hides. If you cannot
  state the hidden complexity in one sentence, the layer is decoration. A
  wrapper that adds no behavior should be deleted and the underlying call
  used directly.
- **In Gaudi:** `CPLX-001 ShallowModule`, `CPLX-002 PassThroughVariable`,
  `CPLX-004 ConjoinedMethods`, `SMELL-018 MiddleMan`.

### 8. Smallest reasonable change

> *Match the scope of the work. Do not improve unrelated code.*

A bug fix does not need surrounding cleanup. A simple feature does not need
extra configurability. Drive-by improvements expand the diff, hide the real
change from review, and bundle decisions that should have been separate
conversations.

- **In projects:** One PR, one logical change. If the implementation outgrows
  the description, stop and split. Note unrelated improvements in a journal
  or follow-up issue, do not silently include them.
- **In Gaudi:** Enforced by the PR template, not a rule. The principle still
  governs how rules are designed: a rule that fires on five things is five
  rules in disguise.

---

## Pillar III — Cost-Honesty

### 9. Dependencies flow toward stability

> *Volatile code depends on stable code. Never the reverse.*

Robert Martin's Stable Dependencies Principle. If a stable module depends on
a volatile one, every change in the volatile module ripples through the stable
one — and the stable module was supposed to be the foundation. The kernel of
the system is the slowest-changing, most-depended-upon code.

- **In projects:** Domain models depend on nothing. Services depend on models.
  Connectors depend on services and models. Entry points depend on everything.
  When you find an arrow pointing the wrong way, that is a structural defect,
  not a style issue.
- **In Gaudi:** `DEP-001 CircularImport`, `DEP-004 UnstableDependency`,
  `DEP-002 FanOutExplosion`, `DEP-003 FanInConcentration`,
  `ARCH-010 ImportDirectionViolation`.

### 10. Boundaries are real or fictional

> *A boundary is enforced or it is removed. Half-enforced is the worst case.*

A connector that is also a service is a lie about both. A "private" attribute
that the rest of the codebase reads anyway is a fiction. A microservice
boundary that shares a database with the next service is decoration. Pick one:
make the boundary load-bearing, or delete it.

- **In projects:** A connector talks to ONE external system. A service makes
  decisions; a connector translates. If a connector imports from a service,
  the boundary has already collapsed. Document the boundary or remove it.
- **In Gaudi:** `ARCH-011 ConnectorLogicLeak`, `SMELL-019 InsiderTrading`,
  `CPLX-003 InformationLeakage`.

### 11. The reader is the user

> *Every line of code will be read more times than it is written. Optimize for
> the future reader who has none of your context.*

The author understands the code by definition. The reader does not. Cleverness
that saves the author five minutes costs every reader thereafter their
comprehension budget. The future reader is also the AI agent that will modify
this code without you in the room.

- **In projects:** Match surrounding style even when it differs from your
  preference. Write comments that explain *why*, not *what*. Use names that
  read aloud as English. Recommendations attached to errors must name the
  fix, not the diagnosis.
- **In Gaudi:** `Finding.recommendation` is a required field — no rule may
  ship without telling the reader what to do. `SMELL-001 MysteriousName`,
  `SMELL-024 Comments`, `STRUCT-020 MissingReturnTypes`.

### 12. Tests are the specification

> *Behavior that is not tested is wished into existence. If you cannot write
> the test, you do not understand the requirement.*

A test is the only place a requirement is written in a language the machine
will check. Documentation drifts; tests fail loudly. The test is therefore
the specification, and the implementation is what makes the specification
true.

- **In projects:** Write the failing test first. Confirm it fails. Write the
  smallest code that makes it pass. Refactor with the test green. Never delete
  a failing test to make a build pass — escalate it.
- **In Gaudi:** Fixture-first TDD is mandatory for every rule (see
  [docs/testing-fixtures.md](testing-fixtures.md)). The fixture is the
  specification; the rule is the implementation. Boundary fixtures are
  required for any rule with a numeric threshold.

---

## How These Cash Out in Gaudi

The principles are not advisory inside Gaudi itself. They are the editorial
constitution every rule decision must answer to.

### The Rule Acceptance Test

Before a new rule enters the catalog, it must answer five questions in order.
Any "no" sends the rule to the mining queue or to rejection.

```
1. Is the source published and citable?            (Truthfulness #3, Provenance)
   └── No → reject. We do not encode opinion as architecture.

2. Can you write the failing fixture?              (Truthfulness #4, Tests as spec)
   └── No → mining queue. The detection is not concrete enough.

3. Does an existing general rule already cover it? (Economy #6, Subsumption)
   └── Yes → reject as duplicate, or strengthen the general rule.

4. Does it require runtime, network, or graph
   data we cannot statically obtain?               (Cost-honesty #11, Reader)
   └── Yes, and we don't have it → mining queue.

5. Can the recommendation name the fix in one
   sentence the reader can act on without
   additional context?                              (Cost-honesty #11, Reader)
   └── No → fix the recommendation or reject the rule.
```

This is the hanging chain. A rule that hangs from these five wires can bear
load. A rule that does not is dropped.

### The Severity Grammar

Severity is currently assigned ad hoc. Under these principles, the assignment
is doctrinal:

| Severity | When | Examples |
|---|---|---|
| **ERROR** | The violation will cause user-facing failure, data corruption, or a security breach. The system is wrong. | `ARCH-001 NoTenantIsolation`, `DJ-SEC-001 SecretKeyExposed`, `DJ-SEC-002 DebugTrue` |
| **WARN** | The violation will cause production pain — memory growth, scaling collapse, retry storms, maintenance debt. The system works today and will not work later. | `STAB-001 UnboundedResultSet`, `STAB-003 RetryWithoutBackoff`, `IDX-001 MissingStringIndex` |
| **INFO** | The violation is a design-quality observation. The system works and will keep working, but it is not as deep, clear, or maintainable as it could be. | `CPLX-001 ShallowModule`, `SMELL-014 LazyElement`, `STRUCT-021 MagicStrings` |

The test for severity assignment: name the day the code breaks. ERROR breaks
on day one with the wrong input. WARN breaks on the day load arrives. INFO
breaks the next reader's morning. If you cannot name the day, the severity
is wrong.

### Subsumption (the consolidation principle)

When a library-specific rule and a general rule detect the same failure mode,
the library rule is subsumed unless it adds detection power the general rule
lacks. This is the principle behind the removal of `SA-ARCH-001` (folded into
`STAB-006 UnmanagedResource`) and `HTTP-ARCH-001` (folded into
`STAB-003 RetryWithoutBackoff`). The catalog stays small; the detection stays
sharp.

A library rule earns its independence only when it knows something the general
rule cannot — Django's `DEBUG=True` is a Django-specific failure mode with no
general analog, so `DJ-SEC-002` stands alone.

---

## How These Cash Out Across Projects

The principles are not Gaudi-specific. They are intended to be portable. Any
project can adopt them as the doctrine its design decisions appeal to. The
mapping below is concrete:

| Principle | Concrete project practice |
|---|---|
| 1. Structure tells the story | Three-layer architecture; OUTER → MIDDLE → INNER; thin entry points; one connector per external system. |
| 2. One concept, one home | Extract on second occurrence. No copy-paste between scripts. Constants in one place. |
| 3. Names are contracts | Rename when meaning drifts. `ABOUTME:` headers. No "new", "old", "legacy", "v2" in identifiers. |
| 4. Failure must be named | Timeouts on every external call. Bounds on every loop. `with` for every resource. No bare `except`. |
| 5. State must be visible | Config injection via `__init__`. Only composition roots read env. Pure functions where possible. |
| 6. Best line is one not written | YAGNI. Three similar lines is better than one premature abstraction. |
| 7. Layers must earn existence | Every wrapper must hide complexity that can be named in one sentence. |
| 8. Smallest reasonable change | One PR, one logical change. No drive-by improvements. |
| 9. Dependencies flow toward stability | Domain depends on nothing; services on domain; connectors on services; entry points on everything. |
| 10. Boundaries are real or fictional | A connector talks to one system. Half-enforced boundaries are deleted, not patched. |
| 11. The reader is the user | Recommendations name the fix, not the diagnosis. Comments explain *why*. |
| 12. Tests are the specification | Failing test first. The test is the requirement; the code is the implementation. |

When a design question arises in any project — *should this be a service or a
connector? should this rule have a higher threshold? should this PR include
the cleanup?* — name the principle that decides it. If two principles point
opposite directions, the question is genuinely hard and warrants discussion.
If no principle applies, the doctrine has a gap that should be closed.

---

## What Beauty Means Here

Antoni Gaudi's chains revealed which curves a real arch would need to bear
its load. Beautiful arches were the ones that did exactly that work, no more
and no less. The decoration of La Sagrada Familia is structural — every
ornament is a column, every column is a load path, every load path is the
shape gravity demanded.

Beautiful code is the same. It is the residue of removing what does not bear
load. Truthfulness removes lies. Economy removes excess. Cost-honesty removes
shortcuts that mortgage the future. What remains — the code that names what
it is, says only what is needed, and pays its full cost upfront — is
beautiful by the only definition that matters.

Gaudi the linter exists to make this kind of beauty detectable. Gaudi the
doctrine exists to make it derivable from first principles in any project.

---

## See Also

- [README.md](../README.md) — User-facing introduction.
- [docs/rule-registry.md](rule-registry.md) — Source provenance for every rule.
- [docs/testing-fixtures.md](testing-fixtures.md) — The fixture-first TDD rubric.
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Contributor workflow.
