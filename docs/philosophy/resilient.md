# Resilience-First / Distributed Systems — Axiom Sheet

> *Failure is the design input, not the edge case.*

---

## 1. Prime axiom

> **Every call can fail. Every process can die. Every dependency can stop
> answering. A well-architected system treats these as the expected case
> and designs for graceful degradation before it designs for the happy path.**

The Resilience-First school starts from a simple observation: the happy path
is the exceptional state of a production system, not the normal one. Disks
fill, networks partition, memory leaks, certificates expire, DNS misbehaves,
and downstream services go down for maintenance at 3am. A system designed
around the happy path is a system designed for its best day, not its worst.
Beauty, under this axiom, is the system that keeps running honestly even
when half of its dependencies have stopped answering — and keeps telling its
operators, loudly and clearly, what is wrong.

## 2. The rejected alternative

Resilience-First architecture refuses:

- **Happy-path-only code.** A function that works when everything works is
  not finished; it is half-written.
- **Calls without timeouts.** A function that may wait forever is a function
  that, under load, *will* wait forever, and take every caller with it.
- **Unbounded retries.** A retry loop without backoff and a maximum is a
  self-directed denial-of-service attack waiting for the right failure.
- **Shared state across trust boundaries.** Two services that agree on a
  database are not two services; they are one service pretending.
- **Silent fallbacks.** A function that swallows its error and returns a
  "safe default" is a function that makes its own failures unobservable.
  Principle #13 made concrete.
- **Assuming the network is reliable.** The first of Deutsch's Fallacies;
  every system built on the assumption is building on sand.
- **Treating observability as an afterthought.** Logs, metrics, and traces
  are design inputs, not ops-team requirements handed down after launch.
- **"Works on my machine" as a release criterion.** The machine that matters
  is the one at 3am under load with half its dependencies failing.

## 3. Canonical citations

- Armstrong, Joe. "Making reliable distributed systems in the presence of
  software errors." PhD thesis, Swedish Institute of Computer Science,
  2003. — The original formal treatment of "let it crash" and supervision
  trees, derived from Erlang/OTP.
- Nygard, Michael. *Release It! Design and Deploy Production-Ready
  Software.* 2nd ed., Pragmatic Bookshelf, 2018. — The canonical catalog
  of stability patterns: circuit breakers, bulkheads, timeouts, steady
  state, fail fast, handshaking, test harnesses, decoupling middleware,
  shed load.
- Beyer, Jones, Petoff, Murphy, eds. *Site Reliability Engineering: How
  Google Runs Production Systems.* O'Reilly, 2016. — Service level
  objectives, error budgets, toil, and the operational discipline of
  running things at scale.
- Deutsch, Peter. "The Fallacies of Distributed Computing." Sun
  Microsystems, 1994. — The eight assumptions every distributed system
  eventually learns it cannot make.
- Kleppmann, Martin. *Designing Data-Intensive Applications.* O'Reilly,
  2017. — The modern reference on partition tolerance, consensus, and
  the real-world implications of the CAP theorem.
- Kreps, Jay. "The Log: What every software engineer should know about
  real-time data's unifying abstraction." LinkedIn Engineering, 2013. —
  Durable append-only logs as a building block for resilient,
  reprocessable systems.
- Hohpe, Gregor & Woolf, Bobby. *Enterprise Integration Patterns.*
  Addison-Wesley, 2003. — The vocabulary for messaging-based decoupling
  between systems.

## 4. The catechism

Seven derived commitments:

1. **Every external call has a timeout.** Indefinite waits are defects,
   not defaults. A timeout with a reasoned value is honesty; a missing
   timeout is a lie about what the function will do under pressure.
2. **Every retry has backoff and a bound.** A retry without exponential
   backoff is a failed-load amplifier. A retry without a maximum count
   is an apology waiting to be written.
3. **Supervisors own processes.** Armstrong's insight: "let it crash" is
   only a viable strategy if something is watching the crash, restarting
   the process, and bounding the blast radius. Unsupervised crashes are
   not resilient; they are silent.
4. **Bulkheads isolate failure domains.** One subsystem's saturation must
   not drown the others. Thread pools, connection pools, and message
   queues are partitioned so that a failure in the notification path
   cannot consume the pricing path's resources.
5. **Circuit breakers are default, not optional.** When a dependency is
   failing repeatedly, stop calling it for a cooldown period. Fast
   failure is almost always preferable to slow failure, because slow
   failure cascades and fast failure degrades gracefully.
6. **Idempotency by construction.** Every state-mutating operation carries
   a key that makes retries safe. "Exactly once" is unachievable under
   partitions; "at least once, with idempotency" is achievable and
   sufficient.
7. **Observability from day one.** Structured logs, correlation IDs,
   health checks, metrics, and distributed traces are inputs to the
   design. A system that cannot explain itself to its on-call engineer
   is not resilient; it is merely working, which is a much weaker claim.

## 5. Rule shape this axiom generates

- **Forbid** — external calls without timeouts, retries without backoff,
  unbounded queues, shared mutable state across services, health checks
  that test nothing (returning 200 from a function that only verifies
  the process is alive), log lines without correlation IDs, bare
  `except:` clauses in anything that touches the network.
- **Require** — timeouts on every call to anything not in memory,
  idempotency keys on every state-mutating external call, structured
  logging with correlation IDs, explicit fallback paths for every
  dependency, named constants for timeout and retry values.
- **Prefer** — async message queues for decoupling, circuit breakers for
  synchronous calls, process isolation for failure domains, explicit
  degradation modes over silent fallbacks.

A significant fraction of Gaudí's `STAB` family descends from this axiom
directly. Principle #4 ("failure must be named") is Resilience-First's
sharpest contribution to the universal core, and Principle #13 ("the
system must explain itself") is its second. Both are universal, but
both are stated most uncompromisingly in this school.

## 6. The degenerate case

Every axiom has a failure mode. For Resilience-First, the failure mode
is **distributed systems as identity**.

- Microservices as resume-driven development. A ten-user internal tool
  broken into seventeen services, each with its own database, its own
  CI pipeline, its own deployment story. The operational budget exceeds
  the problem budget by an order of magnitude, and the reliability is
  *worse* than the monolith it replaced because now there are seventeen
  things that can go wrong instead of one.
- Kubernetes for a batch job that runs once a day and finishes in four
  minutes.
- Chaos engineering in a system that does not yet have basic monitoring.
  You cannot learn from chaos you cannot observe.
- Observability dashboards nobody reads, alerting on metrics nobody
  understands, runbooks written by people who never had to follow them.
- Pattern-worship of the same kind Classical suffers from, but wearing
  a different hat: circuit breakers in code that has one dependency,
  bulkheads around a function that runs once a week, idempotency keys
  on a read-only query.
- Complexity imported "for reliability" that actually *reduces*
  reliability because the operational surface exceeds what the team can
  reason about under pressure.

The test for distributed-systems-as-identity: does the resilience
machinery match the actual failure modes the system will encounter?
A Python script that runs on cron does not need a service mesh. A
consumer-facing payment flow probably does. The machinery should be
dictated by the blast radius of failure, not by what is fashionable in
the conference talks of the year.

## 7. Exemplar temptation

When writing the Resilience-First implementation of the canonical task,
the exemplar must navigate two opposite temptations:

- **The happy-path shortcut.** It will be tempting to write the order
  pipeline as a straight-through function and hand-wave the failure
  paths. The Resilience-First exemplar must refuse — timeouts, retries,
  backoff, idempotency keys, circuit breakers, supervised subsystems,
  structured logs, and health checks must all be present, and each must
  be a real piece of the design rather than a stub with a TODO.
- **The distributed-systems parody.** It will also be tempting to split
  the exemplar into seven microservices communicating over a real
  message broker running in Docker Compose. The exemplar must refuse
  this too. Resilience is a *property*, not a deployment topology. The
  order pipeline should be a single process with clearly delineated
  subsystems, each of which could be split out later if the failure
  modes demanded it, and none of which must be split to demonstrate
  the axiom.

The faithful Resilience-First exemplar is the one where: every external
call has a timeout with a reasoned value; every retry has exponential
backoff and a maximum; every state-mutating call carries an idempotency
key; every log line is structured and carries a correlation ID that
follows the order through every stage; at least one circuit breaker
guards a dependency the exemplar explicitly treats as flaky; and the
system can produce a meaningful health report when queried.

## 8. Rubric — how to recognize a faithful Resilience-First fixture

- [ ] **Every function that touches anything beyond memory has an
      explicit timeout.** Database calls, HTTP calls, filesystem reads
      on unknown-size inputs, subprocess invocations — all timeout
      explicitly, and the timeout value is a named constant.
- [ ] **Every retry loop uses exponential backoff and a maximum attempt
      count.** The backoff is a real calculation, not a fixed sleep.
- [ ] **Every state-mutating external call carries an idempotency key.**
      The key generation is deterministic and the exemplar documents
      how.
- [ ] **Every log line is structured** (JSON or equivalent key-value
      form) and carries a correlation ID that follows an order through
      every stage of the pipeline.
- [ ] **At least one circuit breaker or bulkhead is present** guarding
      a dependency the exemplar treats as potentially flaky, and the
      exemplar documents why.
- [ ] **Timeouts, retry counts, and circuit-breaker thresholds are named
      constants or config values**, not magic numbers scattered through
      the code.
- [ ] **A health check endpoint exists** that tests actual capability
      (the database is reachable, the pricing service responds) rather
      than merely reporting that the process is alive.
- [ ] **No shared mutable state crosses a trust boundary** without a
      synchronization primitive or an explicit owner documented in a
      comment.
- [ ] **Subsystems have explicit failure modes documented in the code**
      — what happens to an order if pricing fails? If inventory fails?
      If the notification service is down? Each answer is in the code
      as a real path, not in a future TODO.
- [ ] **The system produces enough telemetry** (logs, metrics, or both)
      that an on-call engineer could diagnose a realistic failure mode
      by reading the output, without attaching a debugger.

Ten out of ten is Resilience-First. Eight or nine is a draft. Seven or
fewer is happy-path code with a monitoring afterthought.

---

## See also

- [docs/philosophy/event-sourced.md](event-sourced.md) — Event sourcing
  and resilience are natural allies: an append-only log is durable, a
  stream of events is replayable, and replay is the ultimate recovery
  primitive.
- [docs/philosophy/classical.md](classical.md) — Classical favors the
  beautifully structured monolith; Resilience-First would break that
  monolith apart along failure-domain lines even at the cost of
  structural elegance. A real conflict.
- [docs/principles.md](../principles.md) — Principles #4 (failure must
  be named) and #13 (the system must explain itself) are this school's
  direct contributions to the universal core.
