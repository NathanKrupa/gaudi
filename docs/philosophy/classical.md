# Classical / Structural — Axiom Sheet

> *Order is the precondition for beauty. Structure reveals intent.*

**Status:** Draft template (the first of eight). Sheet format is under review — if
this shape is accepted, the remaining seven schools will be written against it.

---

## 1. Prime axiom

> **Software is beautiful when its structure reveals its intent, and that
> structure is the product of disciplined, intentional decomposition.**

Order is not decoration layered on top of working code. Order *is* the code's
honesty about what it does. A system whose layout tells you nothing about its
behavior is a system that has refused to be understood, and that refusal is a
lie about the work being done.

## 2. The rejected alternative

Classical architecture is defined as much by what it refuses as by what it
builds. It refuses:

- **Emergent chaos as a virtue.** "The design will appear if we keep writing"
  is, to a Classical architect, an abdication of design.
- **Duplication-as-humility.** The Pragmatic school treats early duplication as
  epistemic honesty ("we don't know the shape yet"). Classical treats persistent
  duplication as a structural defect — the shape was always there, we just
  refused to see it.
- **Implicit contracts.** If a module can be called with any type, it has
  promised nothing. A promise that cannot be broken cannot be trusted.
- **God objects and reach-through coupling.** A class that knows everything
  about everything has boundaries of convenience, not of meaning.
- **Service locators and global registries.** Dependencies that are fetched
  rather than declared are dependencies that hide. See Principle #5.
- **Framework-as-architecture.** The framework is a detail that should be
  swappable; the domain is the kernel that persists. (This is the hard-line
  conflict with the Convention school.)

## 3. Canonical citations

- Martin, Robert C. *Clean Architecture: A Craftsman's Guide to Software
  Structure and Design.* Prentice Hall, 2017. — The dependency rule, component
  cohesion principles (REP/CCP/CRP), component coupling principles (ADP/SDP/SAP).
- Martin, Robert C. *Agile Software Development: Principles, Patterns, and
  Practices.* Prentice Hall, 2002. — The original SOLID formulation.
- Evans, Eric. *Domain-Driven Design: Tackling Complexity in the Heart of
  Software.* Addison-Wesley, 2003. — Bounded contexts, ubiquitous language,
  aggregates, the domain as kernel.
- Gamma, Helm, Johnson, Vlissides. *Design Patterns: Elements of Reusable
  Object-Oriented Software.* Addison-Wesley, 1994. — Named patterns as shared
  architectural vocabulary.
- Fowler, Martin. *Patterns of Enterprise Application Architecture.*
  Addison-Wesley, 2002. — Repository, Unit of Work, Service Layer, Data Mapper.
- Aquinas, Thomas. *Summa Theologica* I, q. 39, a. 8. — *Integritas, proportio,
  claritas* as the constitution of beauty in a composed thing. Gaudí's own
  foundational text.

## 4. The catechism

Seven derived commitments. A Classical implementation demonstrates all seven,
or it is not Classical — it is pastiche.

1. **Dependencies flow inward, always.** Stable, abstract code is the core;
   volatile, concrete detail is the rim. Infrastructure depends on the domain,
   never the reverse. (Principle #9.)
2. **Every boundary is named and typed.** A layer has a face (its interface)
   and a back (its implementation). Crossing a boundary means calling through
   the face. (Principle #10.)
3. **Single responsibility at every scale.** A function does one thing. A class
   owns one concept. A module serves one concern. A service provides one
   capability. The scale changes; the rule does not.
4. **Composition is explicit.** Objects receive their collaborators via their
   constructor. No service locators, no ambient context, no framework magic
   reaching into private state. (Principle #5.)
5. **Named patterns are vocabulary, not decoration.** A "Repository" means the
   same thing to every reader on the team. Patterns earn their names by hiding
   nameable complexity (Principle #7), not by matching a diagram in a book.
6. **The domain is the kernel, and it has no dependencies.** The pure domain
   model knows nothing about HTTP, SQL, queues, or files. It is the part of
   the system that would survive a total infrastructure rewrite.
7. **Structure is documentation that cannot drift.** Reading the top-level
   package layout tells you what the system does. The compiler reads the same
   layout you do, so the layout cannot quietly lie. (Principle #1.)

## 5. Rule shape this axiom generates

This axiom produces rules of three kinds:

- **Forbid** — circular imports, God objects, domain-imports-infrastructure,
  reach-through coupling, layer-skipping, global mutable state, service
  locators, bare `except`, hidden dependencies on the environment.
- **Require** — explicit interfaces at named boundaries, constructor injection,
  single-responsibility units, typed public APIs, bounded contexts when the
  domain has distinct meanings.
- **Prefer** — named patterns over ad-hoc structure, composition over
  inheritance, immutable value objects for domain concepts, small focused
  classes over large flexible ones.

Most of Gaudí's current `ARCH`, `DEP`, and `STRUCT` rules derive from this
axiom. A classification check: if removing the rule would make it harder to
state the dependency rule, the layering rule, or the single-responsibility
rule with a straight face, the rule descends from this axiom and belongs —
at minimum — in Classical's scope.

## 6. The degenerate case

Every axiom has a failure mode that looks like extreme faithfulness but is
actually its opposite. For Classical, that failure mode is **pattern worship**.

- Seventeen classes for a CSV parser because a book once drew a pipeline.
- Factories that build factories that build the thing that was going to be
  instantiated in one line.
- Interfaces extracted for types that have exactly one implementation and
  will never have a second.
- Ports-and-adapters scaffolding around a 40-line script that reads one file
  and prints a number.
- A `DomainEventPublisherFactoryProviderStrategy`.

The test for pattern worship is Principle #7: *every layer must earn its
existence in clarity gained.* A layer that hides nothing you can name in a
sentence is decoration. Classical architecture, practiced faithfully,
contains *fewer* classes than its caricature suggests, not more. The
discipline is in what structure you refuse to add, not only in what structure
you demand.

The Cathedral of Abstractions is the opposite of a cathedral — it is a
scaffold that forgot it was supposed to be taken down once the arch could
bear its own weight.

## 7. Exemplar temptation

When writing the Classical implementation of the canonical task, the exemplar
must navigate two opposite temptations:

- **The procedural shortcut.** At some point in the order-processing pipeline,
  it will be *shorter* to write one 40-line function that validates, prices,
  reserves inventory, and sends the notification inline. The Classical
  exemplar must refuse this shortcut — and the refusal is the *point*, not
  a bug. The exemplar demonstrates that separation of concerns is worth the
  line count in exchange for the reader knowing where each responsibility lives.
- **The pattern-worship shortcut.** It will also be *more impressive* to
  introduce a `PricingStrategyFactory`, a `NotificationDispatcherRegistry`,
  and an `InventoryReservationPolicyProvider`. The Classical exemplar must
  refuse this temptation too, because pattern worship is the degenerate case
  of the axiom, and an exemplar that surrenders to the degenerate case
  teaches the wrong thing.

The faithful Classical exemplar is the one that adds a class or an interface
if and only if the reader would be *less* confused after its introduction
than before. Every abstraction earns a sentence in its name. Every name
survives the Principle #3 test.

## 8. Rubric — how to recognize a faithful Classical fixture

A fixture exemplifies Classical architecture if and only if *all* of the
following are true. Any unchecked box means the fixture is not yet
Classical-exemplary and must be revised before it is used as a reference
implementation or a rule-scope test.

- [ ] **Dependency direction is diagrammable and strictly inward.** You can
      draw the module graph on a whiteboard and every arrow points toward the
      domain kernel. No arrow points outward.
- [ ] **At least one boundary is crossed via an interface**, and the interface
      hides complexity that can be stated in one sentence.
- [ ] **At least one named pattern is used meaningfully** — Repository, Factory,
      Strategy, Service Layer, Unit of Work, etc. — and the pattern is used
      because the reader benefits from the shared vocabulary, not because the
      exemplar wanted to showcase it.
- [ ] **The domain model has zero infrastructure imports.** No HTTP, SQL, ORM,
      logging framework, or environment access inside the domain package.
- [ ] **Dependencies are passed, not fetched.** Constructors receive
      collaborators; no service locator, no module-level singleton, no
      `os.getenv()` anywhere outside a composition root.
- [ ] **Every class has a responsibility statable in one sentence** without the
      word "and." If the sentence needs "and," the responsibility is two.
- [ ] **The top-level package layout readably describes the system.** A
      first-time reader, shown only the directory tree, can state the system's
      purpose and roughly identify where each concern lives.
- [ ] **It refuses the procedural shortcut** in at least one place where the
      shortcut would have saved lines but lost clarity.
- [ ] **It refuses the pattern-worship shortcut** in at least one place where
      a plausible pattern would have been available but was deliberately
      omitted because it would hide nothing.
- [ ] **All public APIs are type-annotated.** The contract is readable from
      signatures alone.

A fixture that passes all ten checks is a faithful Classical exemplar. A
fixture that passes eight or nine is a draft. A fixture that passes seven or
fewer is pastiche and should be rewritten, not patched.

---

## See also

- [docs/principles.md](../principles.md) — Gaudí's editorial constitution. The
  Classical axiom is the school closest to these principles, but not identical
  to them; the principles are the universal core, Classical is one material
  expression of the core.
- [docs/rule-sources.md](../rule-sources.md) — The rule catalog and its
  provenance column (to be extended with a `philosophy_scope` column during
  Phase 0b).
- `docs/philosophy/README.md` — Index of all eight axiom sheets (to be written
  once the template is accepted).
