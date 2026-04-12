# Gaudí RFC: Multi-Philosophy Architecture Support

**Status:** Draft  
**Author:** Nathan Krupa / Chestertron  
**Date:** 2026-04-10  
**Scope:** Core engine design — philosophy-aware rule evaluation

---

## Problem Statement

Gaudí v0.1.0 implicitly assumes a single normative philosophy of software architecture: the Classical/Structural school (Clean Architecture, SOLID, DDD). This creates false positives when linting codebases that are well-architected under a *different* set of axioms.

A Django project penalized for "too many implicit conventions" is not poorly architected — it is faithfully following Convention-Over-Configuration philosophy. A game engine penalized for "insufficient abstraction" may be following Data-Oriented philosophy, where abstraction is considered actively harmful.

**Architectural beauty is not philosophy-neutral.** Gaudí must be opinionated *within* a declared philosophy, not *across* all philosophies simultaneously.

---

## The Seven Schools

### 1. Classical / Structural

**Axiom:** Order is the precondition for beauty.

**Intellectual lineage:** Robert C. Martin (*Clean Architecture*), the SOLID principles, Eric Evans (*Domain-Driven Design*), the Gang of Four patterns tradition, and — as Gaudí's own foundation — the Thomistic aesthetic framework (integritas, proportio, claritas).

**What "good" looks like:**
- Layered separation of concerns with explicit dependency direction
- Single Responsibility at every level (function, class, module, service)
- Contracts and interfaces over concrete dependencies
- Minimal coupling, maximal cohesion
- Named patterns applied consistently (Repository, Factory, Strategy, etc.)
- Code that reveals intent through structure

**Characteristic smell:** Unnecessary coupling, God objects, circular dependencies, implicit contracts.

**Danger zone:** Over-engineering, premature abstraction, pattern worship divorced from actual requirements. The Cathedral of Abstractions that nobody can navigate.

**Thomistic mapping:**
- *Integritas* → completeness of contract, nothing missing from the interface
- *Proportio* → balanced layering, no layer doing too much or too little
- *Claritas* → the code radiates its own purpose through naming and structure

---

### 2. Pragmatic / Evolutionary

**Axiom:** Do not design for the future. Design for today and refactor toward tomorrow.

**Intellectual lineage:** Kent Beck (*Extreme Programming*), Martin Fowler (*Refactoring*), Ward Cunningham (technical debt as metaphor), the Agile movement broadly.

**What "good" looks like:**
- YAGNI (You Aren't Gonna Need It) as sacred principle
- Duplication preferred over premature abstraction ("Rule of Three")
- Architecture emerges from iterative refactoring, not upfront design
- Comprehensive test coverage as the safety net for continuous refactoring
- Small, frequent commits that evolve the design
- Code that solves the *current* problem clearly

**Characteristic smell:** Speculative generality, unused abstractions, frameworks built for requirements that never materialized.

**Danger zone:** Technical debt that never gets repaid, emergent chaos mistaken for emergent architecture, test suites that calcify bad designs.

**Key conflict with Classical:** The Classical school sees premature abstraction as a virtue (designing for extension); the Pragmatic school sees it as the primary waste. A Classical lint rule like "extract interface for any class with more than one consumer" is heresy here.

---

### 3. Functional / Algebraic

**Axiom:** Mutation is the root of all evil. Purity is the path to correctness.

**Intellectual lineage:** Haskell and ML family, Elm Architecture, parts of Rust and Scala, Rich Hickey (*Clojure* — "Simple Made Easy"), Category Theory applied to programming.

**What "good" looks like:**
- Immutable data structures by default
- Pure functions (no side effects) as the dominant building block
- Side effects pushed to the edges (IO monad, effect systems, ports and adapters)
- Composition over inheritance — pipelines of transformations
- Types as documentation and proof
- Referential transparency: any expression can be replaced by its value

**Characteristic smell:** Mutable state, side effects in business logic, inheritance hierarchies, null as a value, exceptions as control flow.

**Danger zone:** Abstraction astronautics (monad transformer stacks nobody can read), type-level programming that excludes team members, purity dogma that makes simple I/O tasks baroque.

**Key conflict with Pragmatic:** A Pragmatic developer will freely mutate local state for clarity. A Functional developer considers that a correctness hazard. A Pragmatic "simple" solution may be a Functional "dangerous" solution.

**Key conflict with Classical:** Classical architecture loves classes and inheritance hierarchies. Functional architecture considers these inherently problematic.

---

### 4. Unix / Minimalist

**Axiom:** Each program should do one thing well. Compose small tools via standard interfaces.

**Intellectual lineage:** Doug McIlroy (Unix pipes), *The Art of Unix Programming* (Eric S. Raymond), Plan 9, the Suckless movement, Go standard library philosophy, the KISS principle.

**What "good" looks like:**
- Small, focused programs/modules composed via text streams or standard interfaces
- Flat is better than nested
- Configuration files over code when possible
- Minimal dependencies — vendor or eliminate
- Plain text as universal interface
- "Worse is better" — a simpler, slightly wrong solution beats a complex, correct one

**Characteristic smell:** Dependency bloat, framework lock-in, abstraction layers that add complexity without enabling composition, "smart" objects instead of dumb data + smart pipelines.

**Danger zone:** Fragmentation into too many tiny tools nobody can hold in their head, shell script spaghetti, reinventing wheels to avoid dependencies.

**Key conflict with Convention-Over-Configuration:** Unix minimalism is deeply suspicious of large frameworks. Rails/Django are the antithesis of "small, sharp tools."

**Key conflict with Classical:** The Clean Architecture's multiple layers of abstraction look like unnecessary complexity to a Unix minimalist. "Just pipe the data through."

---

### 5. Resilience-First / Distributed Systems

**Axiom:** Failure is inevitable and must be designed for. A system that cannot degrade gracefully is not well-architected.

**Intellectual lineage:** Joe Armstrong (Erlang/OTP — "Let it crash"), Netflix chaos engineering (Chaos Monkey), Michael Nygard (*Release It!*), the CAP theorem tradition, Site Reliability Engineering (Google SRE).

**What "good" looks like:**
- Supervision trees: every process has a supervisor that knows how to restart it
- Bulkheads: failures in one subsystem cannot cascade to others
- Circuit breakers: automatic fallback when a dependency is failing
- Timeouts on everything — no indefinite waits
- Idempotent operations as default
- Observability (structured logging, distributed tracing, health checks) built in from day one

**Characteristic smell:** Single points of failure, shared mutable state across service boundaries, synchronous calls without timeouts, optimistic assumptions about network reliability, "happy path only" code.

**Danger zone:** Distributed systems complexity for problems that don't need it, microservices as resume-driven development, operational overhead that exceeds the reliability gained.

**Key conflict with Classical:** A beautifully structured monolith — the Classical ideal — is a single point of failure. The Resilience-First school would break it apart even at the cost of structural elegance.

**Key conflict with Functional:** Pure functional code assumes referential transparency, but distributed systems are inherently side-effectful (network calls, retries, timeouts). The Functional school's purity constraints can be impractical here.

---

### 6. Data-Oriented

**Axiom:** The data layout IS the architecture. Cache coherence and memory access patterns trump all abstractions.

**Intellectual lineage:** Mike Acton (Insomniac Games — "Data-Oriented Design and C++"), Jonathan Blow, Casey Muratori (*Handmade Hero*), the game engine tradition, Andrew Kelley (Zig language design), Entity-Component-System (ECS) pattern.

**What "good" looks like:**
- Data laid out for how it is *accessed*, not how it is *conceptualized*
- Struct-of-Arrays (SoA) over Array-of-Structs (AoS) when iteration dominates
- Hot/cold data splitting — frequently accessed fields packed together
- Minimal pointer chasing; contiguous memory preferred
- Batch processing over individual object method calls
- Performance measured, not assumed

**Characteristic smell:** Virtual dispatch in hot loops, pointer-heavy data structures (linked lists, tree nodes with parent pointers), OOP hierarchies that scatter related data across the heap, abstractions that hide memory access patterns.

**Danger zone:** Premature optimization, code that is fast but incomprehensible, abandoning all abstraction in pursuit of cache lines, performance gains that don't matter for the actual workload.

**Key conflict with Classical:** OOP — the foundation of Classical architecture — is considered actively harmful in Data-Oriented design because it co-locates unrelated data in objects and scatters related data across the heap. The Classical "Shape hierarchy" example is the Data-Oriented school's canonical anti-pattern.

**Key conflict with Functional:** Immutable data structures require copying, which destroys cache locality. The Functional school's core axiom (no mutation) is the Data-Oriented school's core performance hazard.

---

### 7. Convention-Over-Configuration (Framework-Centric)

**Axiom:** Shared convention eliminates unnecessary decisions. The framework IS the architecture.

**Intellectual lineage:** David Heinemeier Hansson (Ruby on Rails — "convention over configuration"), Django ("the framework for perfectionists with deadlines"), Laravel, Spring Boot auto-configuration, the "opinionated framework" tradition.

**What "good" looks like:**
- Following the framework's prescribed patterns (MVC/MTV, ActiveRecord, etc.)
- "The Rails Way" / "The Django Way" as architectural authority
- Generators, scaffolding, and standard project layout
- Deviating from convention only with explicit justification
- Rapid development enabled by shared vocabulary and assumptions
- New team members productive immediately because the architecture is the framework

**Characteristic smell:** Fighting the framework, custom solutions for problems the framework already solves, non-standard project layout, "not invented here" abstractions layered on top of framework abstractions.

**Danger zone:** Framework lock-in, inability to deviate when the framework's assumptions don't match the problem, cargo-cult adherence to convention without understanding, framework-specific skills that don't transfer.

**Key conflict with Unix:** Frameworks are monolithic by nature. The Unix school would decompose a Rails app into a dozen small programs.

**Key conflict with Classical:** Clean Architecture says the framework is a detail that should be swappable. Convention-Over-Configuration says the framework *is* the architecture. These are irreconcilable axioms.

---

## Cross-Cutting Conflict Matrix

| | Classical | Pragmatic | Functional | Unix | Resilient | Data-Oriented | Convention |
|---|---|---|---|---|---|---|---|
| **Classical** | — | Premature abstraction | Inheritance vs composition | Layering vs flatness | Monolith vs distribution | OOP vs data layout | Framework as detail vs framework as architecture |
| **Pragmatic** | | — | Mutation tolerance | Partial agreement (KISS) | Partial agreement (iterate) | Partial agreement (measure first) | Partial agreement (convention saves time) |
| **Functional** | | | — | Composition agreement | Purity vs side effects | Immutability vs cache locality | Framework impurity |
| **Unix** | | | | — | Agreement on small services | Partial agreement (simplicity) | Fundamental conflict |
| **Resilient** | | | | | — | Neutral (different domains) | Framework as constraint |
| **Data-Oriented** | | | | | | — | Framework overhead |

---

## Proposed Gaudí Implementation

### 1. Configuration

```toml
[philosophy]
# Primary school — determines which rules are active by default
school = "classical"

# Optional: secondary influence — activates compatible rules from another school
# without overriding the primary school's axioms
influence = "pragmatic"
```

Valid values: `classical`, `pragmatic`, `functional`, `unix`, `resilient`, `data-oriented`, `convention`

### 2. Rule Metadata

Each rule declares its philosophical scope:

```python
class SingleResponsibilityRule(Rule):
    """Functions should have a single, clear responsibility."""
    
    id = "ARCH-001"
    severity = Severity.WARNING
    
    # Which philosophies consider this rule valid
    philosophies = ["classical", "functional", "unix"]
    
    # Which philosophies consider this rule actively wrong
    conflicts = ["pragmatic", "data-oriented"]
    
    # Rules that apply regardless of philosophy
    universal = False
```

### 3. Rule Categories by Scope

**Universal rules** (philosophy-independent):
- Don't use deprecated APIs
- Don't ignore errors/exceptions silently
- Don't commit secrets or credentials
- Don't use known-vulnerable dependencies
- Syntax correctness and language version compatibility
- All existing Python 3.14 compatibility rules (PY314-001 through PY314-006)

**Philosophy-dependent rules** (the architectural beauty rules):
- Single Responsibility (Classical, Functional, Unix)
- Interface segregation (Classical)
- Prefer immutability (Functional)
- Minimize dependencies (Unix)
- Add timeout to network calls (Resilient)
- Avoid virtual dispatch in loops (Data-Oriented)
- Follow framework conventions (Convention)
- Avoid premature abstraction (Pragmatic)

**Philosophy-conflicting rules** (only active when their philosophy is primary):
- "Extract interface" — Classical says yes, Pragmatic says wait
- "Avoid mutation" — Functional says yes, Data-Oriented says no
- "Use the framework's ORM" — Convention says yes, Unix says no
- "Add abstraction layer" — Classical says yes, Unix says no

### 4. Evaluation Engine Changes

```python
def should_evaluate(rule: Rule, config: GaudiConfig) -> bool:
    """Determine if a rule should run given the active philosophy."""
    
    # Universal rules always run
    if rule.universal:
        return True
    
    # If the active philosophy is in the rule's conflict list, skip
    if config.philosophy.school in rule.conflicts:
        return False
    
    # If the rule declares specific philosophies, check membership
    if rule.philosophies:
        active = {config.philosophy.school}
        if config.philosophy.influence:
            active.add(config.philosophy.influence)
        return bool(active & set(rule.philosophies))
    
    # Default: evaluate
    return True
```

### 5. Reporting

When Gaudí reports findings, philosophy-dependent rules should indicate their philosophical basis:

```
ARCH-001 [WARNING] (Classical) Function `process_order` has 4 distinct responsibilities
  → Consider extracting: validation, pricing, inventory check, notification
  
  Note: This rule reflects Classical/Structural philosophy.
  Pragmatic philosophy would suggest: "Inline until you need to extract."
```

This transparency turns Gaudí from a judge into a *counselor* — it tells you what your declared philosophy recommends and, optionally, what an alternative philosophy would say. This aligns with the Chestertron principle of diplomatic honesty: presenting the case clearly without pretending there is only one valid perspective.

---

## Theological Aside: Why This Matters

The original Gaudí insight was Thomistic: beauty requires *integritas* (completeness), *proportio* (due proportion), and *claritas* (radiance of form). This remains true — but the *application* of these transcendentals varies by context.

A Gothic cathedral and a Japanese tea house both possess integritas, proportio, and claritas. But a rule that says "beauty requires flying buttresses" would fail to recognize the tea house. The transcendentals are universal; their material expression is not.

Gaudí's universal rules are the transcendentals. The philosophy-dependent rules are the material expressions. The configuration is the declaration: "I am building a cathedral" or "I am building a tea house."

This is subsidiarity applied to code quality: the general principle governs, but the specific application belongs to the community (team, project, ecosystem) closest to the work.

---

## Implementation Sequence

1. **Add `philosophy` to `gaudi.toml` schema** — parser, validation, default (`classical`)
2. **Add `philosophies`, `conflicts`, `universal` fields to `Rule` base class**
3. **Update `should_evaluate()` in the core engine** to filter by philosophy
4. **Audit all existing rules** — tag each with philosophy scope
5. **Add philosophy-specific rule packs:**
   - `gaudi.packs.philosophy.pragmatic`
   - `gaudi.packs.philosophy.functional`
   - `gaudi.packs.philosophy.unix`
   - `gaudi.packs.philosophy.resilient`
   - `gaudi.packs.philosophy.data_oriented`
   - `gaudi.packs.philosophy.convention`
6. **Update CLI output** to show philosophy attribution on findings
7. **Write documentation** — explain each philosophy, help teams choose
8. **Add `gaudi init` philosophy selection** — interactive wizard for new projects

---

## Open Questions

1. **Should influence allow more than one secondary?** A Rust project might be Functional + Unix + Resilient simultaneously. But unlimited stacking could recreate the "evaluate everything" problem.

2. **Philosophy profiles?** Common combinations could be named: `rust-idiomatic` = Functional + Unix, `enterprise-java` = Classical + Convention, `game-engine` = Data-Oriented + Pragmatic.

3. **Philosophy detection?** Could Gaudí infer the likely philosophy from the project's language, framework, and dependency tree? A Django project is almost certainly Convention; a Haskell project is almost certainly Functional. This could serve as a smart default.

4. **Per-directory philosophy?** A monorepo might have a Rails frontend (Convention) and a Rust data pipeline (Functional + Data-Oriented). Should `gaudi.toml` support path-scoped overrides?

5. **Should conflicting-philosophy notes be opt-in?** The "alternative perspective" notes in findings are educational but could be noisy. A `[reporting] show_alternatives = true` flag might be appropriate.

---

## References

- Martin, Robert C. *Clean Architecture.* Prentice Hall, 2017.
- Beck, Kent. *Extreme Programming Explained.* Addison-Wesley, 2000.
- Fowler, Martin. *Refactoring.* Addison-Wesley, 2018.
- Raymond, Eric S. *The Art of Unix Programming.* Addison-Wesley, 2003.
- Armstrong, Joe. "Making reliable distributed systems in the presence of software errors." PhD thesis, 2003.
- Acton, Mike. "Data-Oriented Design and C++." CppCon 2014.
- Heinemeier Hansson, David. "The Rails Doctrine." rubyonrails.org, 2016.
- Aquinas, Thomas. *Summa Theologica.* I, q. 39, a. 8 (on beauty as integritas, proportio, claritas).
