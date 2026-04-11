# Convention-Over-Configuration — Axiom Sheet

> *The framework is the architecture. Conformance requires no justification;
> deviation requires explicit defense.*

---

## 1. Prime axiom

> **A well-chosen framework encodes thousands of hours of design work by
> people who thought about these problems longer than any individual team
> will. Adopting the framework's conventions wholesale is the single
> highest-leverage architectural decision a project can make — and fighting
> them is the single most expensive mistake.**

The Convention school treats framework conformance as a structural asset.
Every decision the framework has already made is a decision the team does
not have to make, defend, document, test, or maintain. The cost of "just
our way" is paid not only in the initial implementation but in every new
hire's onboarding, every library that assumes the framework's conventions,
every Stack Overflow answer that works out of the box, and every debugging
session that does not require reading custom code. A team that conforms
inherits a vast, invisible infrastructure of shared assumptions; a team
that deviates pays to rebuild it, usually badly.

## 2. The rejected alternative

Convention architecture refuses:

- **Bespoke solutions for problems the framework already solves.** If
  Django ships a form validator, writing your own is a choice that must
  be defended in blood, not in preference.
- **Non-standard project layouts.** The default directory tree is
  load-bearing — every book, tutorial, generator, and third-party
  library assumes it. Moving files to match personal taste breaks the
  invisible contract with the ecosystem.
- **Custom abstractions layered on top of framework abstractions.** A
  "service layer" that wraps ActiveRecord or Django's ORM without adding
  real behavior loses the framework's benefits (admin integration,
  migrations, querysets) and adds none of its own.
- **"Not invented here" pride.** The framework has solved authentication,
  routing, templating, migrations, admin panels, and form handling. Each
  reimplementation is a vote of no confidence in engineers with more
  context than the current team.
- **Fighting the framework.** When a problem requires going against the
  framework's grain, the right answer is usually "pick a different
  framework" or "this is not a framework problem" — rarely "patch
  around the framework's assumptions."
- **Framework upgrades treated as operational work.** Upgrading Django
  from 4.x to 5.x is architectural work. It is how you get the next
  thousand hours of thought, free.
- **Convention followed without understanding.** The failure mode of
  this school is cargo cult; the remedy is understanding *why* the
  convention exists, not refusing the convention because others don't.

## 3. Canonical citations

- Heinemeier Hansson, David. "The Rails Doctrine." rubyonrails.org, 2016.
  — The explicit articulation of convention over configuration,
  omakase, and the other pillars of the Rails philosophy. The clearest
  single-source statement of the school.
- Django Software Foundation. "Design philosophies." Django
  documentation. — The Django project's own statement of its
  assumptions and why they take the shape they do.
- Thomas, Dave & Heinemeier Hansson, David. *Agile Web Development with
  Rails.* Pragmatic Bookshelf, first published 2005, many editions. —
  The canonical tutorial that encodes "the Rails Way" as a teachable
  discipline.
- Pivotal. *Spring Boot Reference Documentation*, auto-configuration
  chapters. — The Java ecosystem's mature implementation of the same
  ideas: sensible defaults, opinionated starter poms, minimal
  configuration for common cases.
- Stenberg, Daniel. *The Laravel Philosophy.* laravel.com documentation.
  — The PHP ecosystem's version, showing that the idea generalizes
  across language traditions.
- Fowler, Martin. "InversionOfControl" and "DependencyInjection."
  martinfowler.com, 2004. — The theory behind container-driven design
  and why frameworks can be called "opinionated" in a technical rather
  than aesthetic sense.

## 4. The catechism

Seven derived commitments:

1. **Follow the framework's prescribed patterns.** The framework authors
   have thought about this problem longer than you have. Start from the
   blessed path; deviate only under pressure.
2. **Default layouts are load-bearing.** The location of a file is part
   of its contract with the rest of the ecosystem. `models.py` belongs
   where Django put it. `app/controllers` belongs where Rails put it.
3. **Convention eliminates decisions.** A decision not made is a decision
   that cannot go wrong. The shared vocabulary the convention provides
   is the team's most valuable architectural asset.
4. **Generators and scaffolds are the blessed starting point.** They
   encode the framework's intended way. Begin from them, then customize;
   do not begin from empty files and fight your way toward the
   convention by accident.
5. **Deviate explicitly.** Every deviation from convention earns a
   comment naming the specific pressure that required it, so the next
   reader knows this was a decision and not an accident.
6. **Integrate, do not wrap.** Use the framework's facilities directly.
   A wrapper around the ORM that hides the ORM loses the ORM's
   ecosystem (admin, migrations, third-party extensions) and gains only
   the wrapper's maintenance cost.
7. **The framework version is the architecture version.** Upgrading the
   framework is how the project inherits the next iteration of
   architectural thought. Treat upgrades as first-class work.

## 5. Rule shape this axiom generates

- **Forbid** — custom implementations of framework-provided features,
  non-standard directory layouts, shadow ORMs layered over the
  framework's ORM, service-layer wrappers that hide models without
  adding behavior, bypassing framework middleware with ad-hoc request
  handling, hand-rolled authentication when the framework ships it,
  direct SQL where an ORM method would serve.
- **Require** — framework-idiomatic file locations, framework-provided
  facilities for routing, authentication, templating, migrations, and
  form validation; migration files for every schema change; standard
  test helpers.
- **Prefer** — generated scaffolding as the starting point, framework
  signals/hooks for cross-cutting concerns, framework admin for
  operational tooling, framework-native test fixtures.

Under Gaudí's rule catalog, this axiom is the native home of the `DJ-*`
(Django) family. The Convention school is the one for which Gaudí must
be *gentlest* about non-framework patterns, because what looks like a
"God object" or an "over-eager model" in Classical eyes is the blessed
ActiveRecord pattern here — not a defect, but the framework working as
designed.

## 6. The degenerate case

Every axiom has a failure mode. For Convention, the failure mode is
**cargo cult**.

- Convention followed without understanding, producing N+1 query
  disasters that Django's ORM makes easy to write and hard to notice.
  The developer did what the tutorial did; the tutorial did not show
  the `select_related` call because it was a tutorial, not a
  production system.
- Fat models, fat controllers, or fat serializers — places where the
  convention ran out and nobody extended the pattern, so the code kept
  piling into the last file that still had room.
- Framework lock-in so deep that a framework bug becomes an existential
  business problem, because the team built no abstraction layer
  anywhere and now cannot even isolate the bug from the rest of the
  system.
- Treating the framework as infallible. Every framework has genuine
  mistakes; Convention faithfulness is not "never question the
  framework," it is "question with humility, and understand *why*
  before you deviate."
- Tutorials and Stack Overflow as architecture. The convention
  encourages reaching for prior art, but prior art is not always
  relevant, and the team that copies without checking inherits the
  original's mistakes.
- A codebase that cannot answer "why do we do it this way?" with
  anything more than "it's the Rails Way." The correct answer is
  "because the Rails Way is optimizing for X, which is what we need
  here too." If the team cannot give that answer, they are not
  following Convention — they are obeying it.

The test for cargo cult: ask a developer to explain why a convention
exists. A faithful Convention practitioner can name the problem the
convention was solving. A cargo-cultist can only name the convention.

## 7. Exemplar temptation

When writing the Convention implementation of the canonical task, the
exemplar must navigate two opposite temptations:

- **The clean-architecture temptation.** It will be tempting to extract
  an "OrderService" layer between the view and the model, "for
  testability" or "to keep the model thin." The Convention exemplar
  must refuse — Django's model layer is *supposed* to hold this logic,
  the model's manager methods are *supposed* to encapsulate queries,
  and the blessed pattern is fat-model, skinny-view. Extracting the
  service layer means abandoning the convention without a concrete
  reason, and abandoning the convention is the single mistake this
  school most wants to avoid.
- **The tutorial-grade parody.** It will also be tempting to write
  tutorial code — unparameterized querysets, no `select_related`, no
  pagination, no admin registration, no migration paths for schema
  changes. The Convention exemplar must refuse this too. Faithful
  Convention is the framework at its production best: admin wired,
  migrations clean, querysets prefetched, signals used only where
  appropriate, and the whole thing comprehensible to any Django
  developer at a glance.

The faithful Convention exemplar is the one where: the directory tree
is immediately recognizable as a Django app; `Order` is a Django model
with manager methods encapsulating queries; views use generic CBVs or
DRF viewsets where appropriate; admin is registered; migrations exist
and are reversible; no raw SQL is written where an ORM method would
serve; authentication uses `django.contrib.auth`; and every deviation
from convention is labeled with a one-sentence explanation.

## 8. Rubric — how to recognize a faithful Convention fixture

- [ ] **The project layout is immediately recognizable as Django** (or
      Rails / Laravel / Spring Boot) by any practitioner of that
      framework. The directory tree needs no explanation.
- [ ] **All models inherit from the framework's base model class** and
      live in the conventional location (`models.py` or `models/`).
- [ ] **All routes are declared through the framework's routing system**
      (`urls.py` patterns, Django router, etc.), not through a custom
      dispatch layer.
- [ ] **Migrations exist for every schema change** and are reversible
      (forward and backward migration operations are specified).
- [ ] **No custom middleware replaces a framework-provided facility.**
      Where custom middleware exists, it adds a new concern rather than
      substituting for a standard one.
- [ ] **No hand-rolled ORM, serializer, or form validation.** Django
      Forms, DRF Serializers, or equivalent framework machinery carry
      all input handling.
- [ ] **Admin (or equivalent dashboard) is wired** where the framework
      provides it, demonstrating that ops tooling uses the blessed path.
- [ ] **Deviations from convention are explicitly labeled.** Any place
      the exemplar leaves the blessed path has a one-sentence comment
      naming the pressure that required the deviation.
- [ ] **The test suite uses the framework's own test helpers** (Django
      `TestCase`, `pytest-django`, equivalent) rather than a hand-rolled
      fixture system.
- [ ] **A first-time reader who knows the framework can predict what
      each file contains** from the filename alone, without opening it.

Ten out of ten is Convention. Eight or nine is a draft. Seven or fewer
is a custom application that happens to import a framework.

---

## See also

- [docs/philosophy/unix.md](unix.md) — Convention's structural opposite.
  A Django app and a Unix pipeline are built on irreconcilable
  assumptions about where complexity should live and what a "program"
  even is.
- [docs/philosophy/classical.md](classical.md) — Classical says the
  framework is a detail that should be swappable; Convention says the
  framework *is* the architecture. These axioms cannot be reconciled;
  a project must pick one.
- [docs/principles.md](../principles.md) — Convention's contribution to
  the universal core is mostly negative: it is the school that most
  strongly limits how aggressively other schools' rules can fire on
  framework-blessed patterns without producing false positives.
