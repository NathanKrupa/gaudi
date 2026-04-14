# Architectural Philosophies

> *Beauty is not philosophy-neutral. A Gothic cathedral and a Japanese tea
> house both possess integritas, proportio, and claritas — but a rule that
> says "beauty requires flying buttresses" would fail to recognize the tea
> house. The transcendentals are universal; their material expression is not.*

---

## Purpose

Gaudí's editorial constitution — [docs/principles.md](../principles.md) — is
built around three pillars (Truthfulness, Economy, Cost-honesty) that every
rule must appeal to. Those pillars are deliberately school-agnostic: they
describe beauty in code without committing to a particular style of
beautiful code.

But most architectural rules are not school-agnostic. A rule that says
"extract an interface for any class with more than one caller" is beautiful
under Classical assumptions and heretical under Pragmatic ones. A rule that
says "prefer composition over inheritance" is trivially true for Functional
programmers and an active anti-pattern under Data-Oriented layouts where
inheritance would scatter related fields across the heap.

The axiom sheets in this directory name the philosophies under which
Gaudí's rules make sense. Each sheet is a falsifiable description of one
school — its prime axiom, what it rejects, its canonical sources, its
catechism, the shape of rules it generates, its degenerate case, the
temptations an exemplar must refuse, and a ten-item rubric for recognizing
a faithful fixture of that school.

These sheets are the scaffolding for three downstream pieces of work:

1. **The rule audit** — every rule in [docs/rule-sources.md](../rule-sources.md)
   gets tagged with a philosophy scope (`universal` or a specific school),
   appealing to the axiom sheet that makes the tag defensible.
2. **The canonical task** — a single domain problem (order processing
   pipeline) implemented eight ways, once per school, each implementation
   scored against the rubric in its school's axiom sheet.
3. **The engine change** (deferred) — the `Rule.philosophy_scope` field
   and `[philosophy].school` config key, which together let Gaudí filter
   its catalog to the rules that are honest under the project's declared
   school.

---

## The Eight Schools

| School | Prime axiom | Axiom sheet |
|---|---|---|
| **Classical / Structural** | Order is the precondition for beauty. Structure reveals intent. | [classical.md](classical.md) |
| **Pragmatic / Evolutionary** | Design is discovered, not declared. Refactor toward the shape the problem is asking for. | [pragmatic.md](pragmatic.md) |
| **Functional / Algebraic** | Computation is transformation. Values flow; state does not hide. | [functional.md](functional.md) |
| **Unix / Minimalist** | Do one thing well. Compose via text. | [unix.md](unix.md) |
| **Resilience-First / Distributed Systems** | Failure is the design input, not the edge case. | [resilient.md](resilient.md) |
| **Data-Oriented** | The data layout is the architecture. Cache lines are the unit of decision. | [data-oriented.md](data-oriented.md) |
| **Convention-Over-Configuration** | The framework is the architecture. | [convention.md](convention.md) |
| **Event-Sourced / CQRS** | The log of events is the state. Current state is a projection, not a source. | [event-sourced.md](event-sourced.md) |

---

## Why Eight, and Not Seven or Nine

The RFC that opened this work proposed seven schools. Event-Sourced was
added after a second-pass review because it meets the only test that
matters for admitting a new school to this catalog:

> **A school earns its place when it generates rules that contradict
> rules from existing schools.** If a candidate only *adds* rules that
> stack with any existing school without contradicting any of them, it
> is a cross-cutting concern, not a school.

Event-Sourced contradicts Classical DDD's default of in-place aggregate
mutation, Pragmatic's YAGNI treatment of event-type extraction, and
CRUD-as-default under any school — while being genuinely distinct from
Functional (which forbids mutation everywhere, not just on aggregates)
and Resilient (which cares about recovery, not about intent preservation).
It passes the test.

Candidates that were considered and rejected as full schools:

- **Type-Driven / Proof-Carrying** (Idris, Agda, heavy Haskell). The
  rules it generates — `no Any`, `no partial functions`, "make illegal
  states unrepresentable" — mostly *stack* with Functional without
  contradicting it. Treated as a sub-scope of Functional, not a separate
  school.
- **Actor / Message-Passing** (Erlang, Akka). Already subsumed by
  Resilience-First, whose catechism leans heavily on Armstrong's thesis.
- **Literate Programming** (Knuth). A cross-cutting concern that stacks
  with every school without contradicting any. Captured in Principle #11
  of the universal core, not in a dedicated sheet.
- **Live / Image-Based** (Smalltalk, Lisp REPL-driven). A real distinct
  axiom, but too niche for a Python linter to serve honestly at this
  stage.

If a future contributor argues that a ninth school deserves inclusion,
the argument must pass the contradiction test: name at least one rule
the school would enforce that no existing school's rule catalog already
contains, and explain why that rule is correct under the new school's
axiom and incorrect under every existing one's.

---

## The Sheet Format

Every axiom sheet follows the same eight-section structure:

1. **Prime axiom** — one sentence. The single claim from which everything
   else descends.
2. **The rejected alternative** — what the school refuses. A school is
   defined as much by its refusals as by its endorsements.
3. **Canonical citations** — published, citable sources that ground the
   school. Required by [Rule Acceptance Test #1](../principles.md).
4. **The catechism** — five to seven derived commitments in plain English.
5. **Rule shape** — the *kinds* of rules this axiom generates: forbid,
   require, prefer.
6. **The degenerate case** — the failure mode that looks like extreme
   faithfulness but is actually the axiom's inversion.
7. **Exemplar temptation** — the shortcuts a reference implementation
   must refuse to stay faithful, and the opposite shortcuts it must also
   refuse to avoid parody.
8. **Rubric** — a ten-item checklist for scoring whether a given fixture
   is actually an exemplar of the school.

The rubric at the end of each sheet is the operational piece. It lets a
reviewer say "this exemplar fails check #4" instead of "this feels off,"
and it lets the later canonical-task exemplars be scored against a
defensible standard rather than against taste.

---

## Relationship to `docs/principles.md`

The fourteen principles in [docs/principles.md](../principles.md) are the
universal core — the claims beautiful code must satisfy under *any*
philosophy. The eight schools are the material expressions — the specific,
contradictory, school-bound ways that beauty shows up in real codebases.

The relationship is Thomistic by design:

- The Three Pillars (Truthfulness, Economy, Cost-honesty) are the
  transcendentals.
- The fourteen principles are the universal derived commitments.
- The eight schools are the material expressions.
- A rule is *universal* if it descends directly from the principles.
- A rule is *school-bound* if it descends from the axioms of one school
  and cannot be defended against the axioms of another.

When Phase 0b (the rule audit) lands, every rule in
[docs/rule-sources.md](../rule-sources.md) will be tagged with its
philosophy scope. Most rules will come back `universal` — they descend
from the pillars and hold in every school. A smaller number will come
back tagged with one or more specific schools, because they depend on
axioms that not every school accepts.

---

## What Is Not Here Yet

- **The rule audit column** — Phase 0b. Every rule gets tagged; the
  column lives in [docs/rule-sources.md](../rule-sources.md).
- **The canonical task statement** — Phase 0c. The order-processing
  problem, acceptance criteria, and interface for the eight
  implementations.
- **The reference exemplars** — Phase 0d and beyond. Eight working
  implementations of the canonical task, one per school, each scoring
  ten-out-of-ten on its school's rubric.
- **The engine change** — deferred until the audit's outcome tells us
  how much machinery the catalog actually needs.

---

## See also

- [docs/principles.md](../principles.md) — The editorial constitution
  and universal core.
- [docs/rule-sources.md](../rule-sources.md) — The rule catalog,
  which will gain a philosophy-scope column during Phase 0b.
- [docs/testing-fixtures.md](../testing-fixtures.md) — The fixture-first
  TDD rubric; the philosophy exemplars extend this discipline to the
  meta-level.
