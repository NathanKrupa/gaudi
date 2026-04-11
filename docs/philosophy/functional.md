# Functional / Algebraic — Axiom Sheet

> *Computation is transformation. Values flow; state does not hide.*

---

## 1. Prime axiom

> **A program is a composition of pure transformations over immutable values.
> Side effects exist only at the edges, where the program meets the world —
> and they are named, typed, and visible when they do.**

Mutation is the root cause of the class of bugs where a function's behavior
depends on what some other function did to shared memory between calls.
Purity is not an aesthetic preference; it is the price of being able to
reason about a piece of code by reading only that piece of code. The
Functional school buys that reasoning ability by refusing the shortcut of
hidden state.

## 2. The rejected alternative

Functional architecture refuses:

- **Mutation on shared references.** A value that can change out from under
  its reader is a lie about what that reader is looking at.
- **Hidden side effects in business logic.** A pricing function that writes
  to a log, queries a cache, and updates a metrics counter is three functions
  pretending to be one.
- **Classes with mutable private state.** Encapsulation hides the mutation;
  the mutation is still there, and it still defeats local reasoning.
- **Inheritance as a mechanism for reuse.** A subclass that changes behavior
  by overriding methods is a back-door mutation of its superclass's meaning.
- **Exceptions as control flow.** A function that may or may not return
  depending on runtime state is a function with two hidden return paths and
  no type that describes them.
- **`None` / `null` as a legitimate value.** A type that silently admits
  absence is a type whose contract is a lie. If absence is meaningful, it
  deserves its own name (`Option`, `Maybe`, `Result`).
- **Ambient I/O.** A function that reads from the environment, the clock,
  or the filesystem without declaring it in its signature is a function
  whose dependencies cannot be tested without staging the world.

## 3. Canonical citations

- Hickey, Rich. "Simple Made Easy." Strange Loop, 2011. — The distinction
  between *simple* (disentangled) and *easy* (familiar), and why mutation
  is never simple.
- Okasaki, Chris. *Purely Functional Data Structures.* Cambridge University
  Press, 1998. — Persistent data structures as the demonstration that
  immutability is practical, not ideological.
- Hutton, Graham. *Programming in Haskell.* 2nd ed., Cambridge University
  Press, 2016. — The canonical introduction to pure functional programming
  in the typed tradition.
- Wadler, Philip. "The Essence of Functional Programming." POPL, 1992. —
  Monads as the principled treatment of effects.
- Czaplicki, Evan. *The Elm Architecture.* elm-lang.org. — Model, Update,
  View as a practical discipline for building UIs without mutation.
- Pierce, Benjamin. *Types and Programming Languages.* MIT Press, 2002. —
  The formal foundation for treating types as proofs.
- Bird, Richard & Wadler, Philip. *Introduction to Functional Programming.*
  Prentice Hall, 1988. — The origin text for much of the discipline.
- Backus, John. "Can Programming Be Liberated from the von Neumann Style?"
  Turing Award lecture, 1977. — The foundational argument that mutation
  and variables are historical accidents, not necessities.

## 4. The catechism

Seven derived commitments:

1. **Immutable by default.** Values are not mutated; they are replaced. A
   "change" is a new value that differs from the old in some respect.
2. **Pure functions compose.** Given the same input, a pure function always
   produces the same output and has no observable effect on anything else.
   The composition of pure functions is itself pure, which is why pipelines
   scale in complexity without scaling in difficulty.
3. **Side effects are pushed to the edges.** The core of the program is
   pure; I/O, network, database, and clock live in a thin shell that wraps
   the pure core. This is the "functional core, imperative shell" pattern.
4. **Types are the proof.** If the type checker accepts a program, that
   program is at least as correct as its types demand. Rich types catch
   more bugs at compile time; weak types catch them at 3am in production.
5. **Composition over inheritance.** A program is assembled from functions
   combined with `map`, `filter`, `fold`, `compose`, and their kin — not
   from classes arranged in hierarchies.
6. **Totality over exceptions.** A function that might fail returns a value
   describing the failure (`Result`, `Either`, `Option`) — it does not
   raise an exception and it does not return `None`. Errors become data,
   and data is checkable.
7. **Referential transparency.** Any expression may be replaced by its
   value without changing the meaning of the surrounding program. This is
   the property that makes the rest of the catechism tractable.

## 5. Rule shape this axiom generates

- **Forbid** — mutation of arguments, shared mutable globals, classes with
  mutable state, side effects in the domain core, `None` as a legitimate
  return value, exceptions as flow control, inheritance chains beyond
  protocol/interface definitions, primitive obsession, functions whose
  behavior depends on the clock or the filesystem without declaring it.
- **Require** — a pure core, effect types (or clearly named edge modules)
  at boundaries, total functions on all declared inputs, explicit error
  values, type annotations dense enough to be used as documentation.
- **Prefer** — frozen dataclasses over mutable classes, comprehensions over
  accumulator loops, function composition over class hierarchies, named
  result types over sentinel values.

This axiom's direct contribution to Gaudí's universal core is Principle #5
("state must be visible") and Principle #4 ("failure must be named") — both
of which survive translation into every school, but which Functional states
most strictly. Where Classical says "state should be owned by a class,"
Functional says "state should, where possible, not exist at all."

## 6. The degenerate case

Every axiom has a failure mode. For Functional, the failure mode is
**abstraction astronautics**.

- Monad transformer stacks nobody can read — five layers of wrapping to do
  the work that a try/except and a logging call would have done honestly.
- Type-level programming that uses up the team's entire comprehension
  budget to prove a property the tests would have caught anyway.
- The word "just" in answers: "just lift it into the Reader monad," "just
  use the Church encoding," "just applicative functors." When "just" is
  the bridge between the question and the answer, the abstraction has
  stopped earning its weight.
- Purity dogma applied to tasks that are fundamentally about effects —
  reading a config file turned into a three-file type-level choreography
  because the word "impure" was not allowed to appear.
- Treating every newcomer's mutable loop as a moral failing rather than a
  teaching opportunity. Purity is a property of programs, not of
  programmers.
- Using Haskell-style names (`fmap`, `>>=`, `pure`, `traverse`) in a
  language whose community calls them something else, so that the code
  is readable only to those who have already been initiated.

The test for abstraction astronautics: show the code to a competent
programmer who is fluent in the language but not in the school. If they
cannot state what the code does within one minute, the abstraction has
failed its own axiom — referential transparency is supposed to make the
code *easier* to reason about, not harder.

## 7. Exemplar temptation

When writing the Functional implementation of the canonical task, the
exemplar must navigate two opposite temptations:

- **The mutable shortcut.** It will be tempting, at some point in the
  pricing or inventory logic, to use a mutable accumulator or a mutable
  dictionary because "it is just local state." The Functional exemplar
  must refuse — even local mutation defeats referential transparency
  for the enclosing function, and the whole discipline is about keeping
  that transparency available everywhere.
- **The Haskell-in-Python parody.** It will also be tempting to build a
  `Reader[Env, Result[OrderError, Order]]` monad transformer stack,
  import `returns` or `expression`, and write Python that looks like
  someone wanted Haskell but had to settle. The Functional exemplar must
  refuse this too. The exemplar is in Python; it uses Python's native
  tools (frozen dataclasses, tuples, comprehensions, union types,
  `typing.Protocol`) in the functional *style* rather than in a cosplay
  of another language.

The faithful Functional exemplar is the one where: the core domain
module has zero imports from `logging`, `os`, `requests`, or any
database library; every dataclass is `frozen=True`; errors are returned
as tagged values, not raised; and any newcomer who is fluent in Python
(but not in Haskell) can read the code top to bottom without a glossary.

## 8. Rubric — how to recognize a faithful Functional fixture

- [ ] **No mutation of passed-in arguments.** Functions return new values;
      they do not reach into their inputs and change them.
- [ ] **All domain dataclasses are `frozen=True`.** Or the language's
      equivalent immutable construct. Records describe facts, not slots.
- [ ] **I/O is isolated at the edges.** The domain core module has zero
      imports of `logging`, `os`, `requests`, `sqlite3`, database clients,
      or the clock (`time`, `datetime.now`).
- [ ] **Errors are returned as values**, not raised. A `Result`,
      `Either`, or tagged-union pattern is used consistently for failure.
- [ ] **No shared mutable globals.** No module-level dict, set, or list
      that mutates during execution. Constants are allowed; registries
      are not.
- [ ] **For-loops with accumulators are absent** where `map`, `filter`,
      comprehensions, or `functools.reduce` would serve honestly.
- [ ] **Type annotations are dense and meaningful.** No bare `Any`. No
      `Optional` where a `Result` would tell the truth more precisely.
- [ ] **Inheritance is used only for `Protocol` or ABC definitions** —
      never to reuse behavior by extending a concrete class.
- [ ] **Composition is explicit.** Pipelines are built from named functions
      combined with `compose`, `pipe`, or straight-line application; not
      from classes whose methods call each other.
- [ ] **Any function in the core can be evaluated in the REPL** without
      staging files, databases, or network mocks. Referential transparency
      is demonstrable, not merely claimed.

A fixture that passes all ten is Functional. Eight or nine is a draft.
Seven or fewer is probably imperative code wearing functional decoration.

---

## See also

- [docs/philosophy/classical.md](classical.md) — Functional rejects
  inheritance-based reuse and stateful encapsulation, both of which
  Classical embraces.
- [docs/philosophy/data-oriented.md](data-oriented.md) — Functional's
  sharpest disagreement: immutability requires copying, which destroys
  cache locality. These two schools are nearly irreconcilable on the
  question of how values live in memory.
- [docs/principles.md](../principles.md) — Principle #5 (state must be
  visible) is Functional's purest contribution to the universal core.
