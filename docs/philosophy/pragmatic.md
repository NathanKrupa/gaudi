# Pragmatic / Evolutionary — Axiom Sheet

> *Design is discovered, not declared. Refactor toward the shape the problem is asking for.*

---

## 1. Prime axiom

> **Software design is an empirical discovery, not a deductive declaration.
> The right shape is found by writing the smallest honest code, running it,
> and reshaping it when the next real requirement arrives — never before.**

Upfront design is a prediction, and predictions about code are usually wrong.
The Pragmatic school treats every speculative decision as a loan taken out
against an imagined future, a loan whose interest compounds in exactly the
cases where the imagination turned out to be wrong. The cheapest design is
the one the code does not yet contain.

## 2. The rejected alternative

Pragmatic architecture is defined by what it refuses to build early:

- **Upfront abstraction for callers that do not yet exist.** A class extracted
  "for flexibility" is a commitment to a shape nobody has measured.
- **Configuration knobs for scenarios nobody has seen.** Every flag is a
  branch, every branch is a test matrix, every test matrix is debt.
- **Design documents as substitute for code.** The whiteboard is a sketch;
  the code is the thing. If the code is wrong, the whiteboard was optimistic.
- **"We'll need it eventually" as justification.** Eventually is not evidence.
  Build the thing you need now; revisit when the second requirement is a fact.
- **Patterns applied because they are named.** A pattern is only an asset when
  it solves a real problem at hand, not when it matches a diagram.
- **Refactoring as a separate "cleanup phase."** Refactoring is a continuous
  activity done under a green test suite, not a budget line to be deferred.
- **Premature extraction of shared libraries.** The Rule of Three exists
  because two occurrences are not yet a pattern; they are a coincidence.

## 3. Canonical citations

- Beck, Kent. *Extreme Programming Explained: Embrace Change.* Addison-Wesley,
  2000. — Small releases, continuous refactoring, test-first as the rhythm of
  design.
- Beck, Kent. *Test-Driven Development: By Example.* Addison-Wesley, 2003. —
  Red-green-refactor as the engine of emergent design.
- Fowler, Martin. *Refactoring: Improving the Design of Existing Code.*
  2nd ed., Addison-Wesley, 2018. — The catalog of safe transformations under a
  green test suite.
- Hunt, Andrew & Thomas, David. *The Pragmatic Programmer.* 20th Anniversary
  ed., Addison-Wesley, 2019. — DRY, orthogonality, tracer bullets, and the
  broken window theory of codebases.
- Cunningham, Ward. "The WyCash Portfolio Management System." OOPSLA 1992. —
  The original technical debt metaphor.
- Feathers, Michael. *Working Effectively with Legacy Code.* Prentice Hall,
  2004. — Characterization tests and the discipline of refactoring under
  incomplete knowledge.
- Jeffries, Ron. "We tried baseball and it didn't work." ronjeffries.com. —
  The clearest rejection of the upfront-design substitute.

## 4. The catechism

Seven derived commitments. A Pragmatic implementation practices all seven as a
single discipline, because the discipline only works as a whole — the tests
enable the refactoring, which enables the small commits, which enable the
emergent design.

1. **YAGNI is sacred.** Do not build for callers that do not yet exist. The
   cheapest abstraction is the one the code still lacks.
2. **Rule of Three.** Duplicate once, duplicate twice, extract on the third
   occurrence. Two shapes are a coincidence; three are a pattern.
3. **Red-green-refactor.** Write the failing test first. Write the smallest
   code that makes it pass. Refactor with the test green. No step may be
   skipped, because the refactoring step is where the design actually appears.
4. **Small commits that always compile.** The repository is a chain of
   working states, not a plan of future perfection. Every commit must pass
   its tests. Every commit must be safe to revert.
5. **Refactoring is continuous, not phased.** A "refactor sprint" is an
   admission that refactoring stopped happening during feature work. Under
   the Pragmatic axiom, feature work *is* refactor-and-extend work.
6. **Tests are the safety net for discovery.** Without tests, refactoring is
   Russian roulette. Without refactoring, the design cannot respond to what
   is learned. Without the tests enabling the refactoring, the Pragmatic loop
   collapses into cowboy coding.
7. **Debt is named and repaid.** Technical debt that is tracked is manageable
   debt; debt that is hidden is the kind that bankrupts projects. Every
   knowing compromise is labeled where the code will see it and scheduled
   where the team will see it.

## 5. Rule shape this axiom generates

- **Forbid** — speculative generality, interfaces with one implementation,
  configuration flags that are never toggled in tests, dead parameters, dead
  code paths, "future use" extension points, TODO comments older than
  N months without a linked issue, refactoring hidden inside feature commits.
- **Require** — a failing test before the implementation, small commits,
  green builds as the default state, named debt when debt is taken.
- **Prefer** — three lines of duplication over one premature abstraction,
  concrete types until a second caller appears, inlined helpers until a third
  does, a deleted line over a cleverer one.

Most of Gaudí's `SMELL-015 SpeculativeGenerality`, `SMELL-014 LazyElement`,
and `SMELL-018 MiddleMan` descend directly from this axiom. So does the
project's own doctrine under Principle #6 ("the best line is the one not
written") and Principle #8 ("smallest reasonable change"). Where Classical
architecture builds the cathedral up front, Pragmatic architecture asks
whether a chapel would serve — and whether even the chapel is overkill for
a congregation of two.

## 6. The degenerate case

Every axiom has a failure mode that looks like extreme faithfulness but is
its opposite. For Pragmatic, that failure mode is **emergence as excuse**.

- Codebases where "the design will emerge" is the standing defense against
  ever stopping to think.
- Technical debt that is always "tracked" in a spreadsheet nobody revisits,
  because tracking is easier than repaying.
- Test suites so detailed and so coupled to implementation that they prevent
  refactoring instead of enabling it — the tests calcify the bad design and
  Pragmatic's engine seizes.
- "Refactoring" used as a synonym for "never finishing." The second caller
  arrives, the Rule of Three fires, and the extraction is never done because
  it would take an afternoon.
- YAGNI applied with such dogmatism that the team cannot respond when the
  anticipated requirement does arrive, because the code has zero seams.
- Continuous cowboy coding justified as "being pragmatic" — the word doing
  work that the discipline is supposed to do.

The test for emergence-as-excuse: look for the refactoring commits. A
faithful Pragmatic repository has them; they are small, they are frequent,
and they are labeled. A repository with zero refactoring commits has either
achieved perfection (unlikely) or confused "shipping features" with
"evolving the design" (likely).

## 7. Exemplar temptation

When writing the Pragmatic implementation of the canonical task, the exemplar
must navigate two opposite temptations:

- **The Classical temptation.** It will be tempting to extract an
  `OrderValidator` interface, a `PricingStrategy` class, and an
  `InventoryReservationService` — because that is what "good design" looks
  like in the Classical textbook. The Pragmatic exemplar must refuse all of
  this until the *second* validator, the *second* pricing rule, or the
  *second* reservation backend is a concrete requirement. Until then, the
  code is a straight-through function with tests around it.
- **The cowboy temptation.** It will also be tempting to use YAGNI as a
  license for sloppiness — skip tests, skip naming, skip the small commits,
  skip the refactoring. The Pragmatic exemplar must refuse this too. The
  discipline that enables YAGNI is exactly what makes YAGNI safe. Without
  the discipline, what is left is not Pragmatism — it is neglect.

The faithful Pragmatic exemplar is the one where: every function has a test
written first; the git log shows small commits that always compile; at least
one place visibly contains duplication because the third occurrence has not
yet arrived; and the code is the simplest honest thing that solves today's
problem, no more and no less.

## 8. Rubric — how to recognize a faithful Pragmatic fixture

A fixture exemplifies Pragmatic architecture if and only if *all* of the
following are true.

- [ ] **At least one honest duplication exists.** Two similar pieces of
      logic have not yet been extracted because the third occurrence has
      not arrived, and the exemplar documents this (a comment, a TODO, or
      a note in the accompanying README).
- [ ] **Every function has a test written before it.** The git history
      (or a commentary file) shows the test-first rhythm, not tests bolted
      on after implementation.
- [ ] **No interfaces exist for single implementations.** No abstract base
      class, Protocol, or generic that has exactly one concrete inhabitant.
- [ ] **No configuration flag is unused in tests.** If the code reads a
      config knob, at least two values for that knob are exercised.
- [ ] **Commits are small and each leaves the suite green.** If the
      exemplar ships with a suggested commit sequence or changelog, the
      sequence shows the red-green-refactor cadence.
- [ ] **Refactoring commits are visible as distinct from feature commits.**
      Feature work and design evolution are not conflated into a single
      sprawling patch.
- [ ] **Type hints are present on the public API but not speculative.**
      No `Generic[T]` or `Protocol` introduced "for future flexibility."
- [ ] **No framework scaffolding exists beyond what is actually used.**
      Every file in the tree earns its place in the current behavior.
- [ ] **Technical debt is named where it lives.** Any known compromise is
      labeled with a one-sentence TODO that names the condition under which
      it should be repaid.
- [ ] **A new team member can read the code top-to-bottom without needing
      to understand named patterns.** The pedagogy is the code itself, not
      a prerequisite vocabulary.

A fixture that passes all ten is Pragmatic. A fixture that passes eight or
nine is a draft. A fixture that passes seven or fewer is probably not
Pragmatic — it is either Classical in disguise or cowboy coding wearing a
Pragmatic badge.

---

## See also

- [docs/philosophy/classical.md](classical.md) — The school Pragmatic most
  directly critiques, and from which many Pragmatic rules are defined as
  negations.
- [docs/principles.md](../principles.md) — Principles #6 (best line is the
  one not written), #8 (smallest reasonable change), and #12 (tests are the
  specification) are Pragmatic's direct contributions to the universal core.
- [docs/rule-sources.md](../rule-sources.md) — `SMELL-014`, `SMELL-015`,
  and `SMELL-018` are the catalog's current expressions of Pragmatic scope.
