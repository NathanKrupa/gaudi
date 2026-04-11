# Data-Oriented — Axiom Sheet

> *The data layout is the architecture. Cache lines are the unit of decision.*

---

## 1. Prime axiom

> **Software exists to transform data. The shape and layout of that data
> determines everything meaningful about performance, and performance is
> not an optimization concern applied at the end — it is a design input
> from the first line.**

The Data-Oriented school starts from a single empirical observation: modern
hardware does not execute "code" in any abstract sense; it moves bytes
between memory tiers and does arithmetic on them in SIMD lanes. The cost of
a program is dominated by how well the data it touches fits in cache and
how well the access pattern matches what the hardware was built to do
quickly. Abstractions that obscure the access pattern hide the real cost
of the code, and hidden costs compound the same way hidden bugs do.

## 2. The rejected alternative

Data-Oriented architecture refuses:

- **Object-oriented encapsulation as the default.** An object that bundles
  hot fields (updated every frame) with cold fields (touched once at
  creation) forces the cache to load both every time either is needed.
- **Virtual dispatch in the inner loop.** Every virtual call is an
  indirection the CPU cannot predict and an allocation the compiler
  cannot inline. Inside a loop that runs millions of times per frame,
  this is the difference between 4ms and 40ms.
- **Pointer chasing.** Linked lists, tree nodes with parent pointers,
  graphs of small heap-allocated nodes — all of them scatter the data
  the loop needs across pages the cache must then chase.
- **"Expressive" code that hides allocations.** A comprehension that
  looks clean but allocates three intermediate lists inside a hot loop
  is expensive code disguised as elegant code. The elegance was a
  costume.
- **Assumptions about performance.** "This should be fast" is not a
  performance claim; it is a wish. Only measurements are claims.
- **Premature abstraction of the data layout.** The layout is the
  architecture; abstracting it is abstracting the architecture. Do
  that later, if ever — and only after measurement justifies the cost.
- **OOP hierarchies for entities.** The inheritance tree optimizes for
  conceptual clarity at the expense of memory locality. Data-Oriented
  design inverts this ranking.

## 3. Canonical citations

- Acton, Mike. "Data-Oriented Design and C++." CppCon, 2014. — The
  definitive talk. Reframes the entire discipline around three premises:
  the purpose of a program is to transform data, hardware has a specific
  shape, and different problems require different solutions.
- Fabian, Richard. *Data-Oriented Design: Software Engineering for
  Limited Resources and Short Schedules.* 2018. — The book-length
  treatment, with worked examples in C++.
- Muratori, Casey. *Handmade Hero.* handmadehero.org, 2014–present. —
  A multi-year from-scratch implementation of a game engine with no
  dependencies, with running commentary on why every abstraction is
  being refused or accepted.
- Blow, Jonathan. Jai language design talks, 2014–present. — The case
  for a language designed around the needs of programmers who care
  about data layout, with a sustained critique of C++'s abstraction
  mechanisms.
- Kelley, Andrew. Zig language design talks and blog posts. — A
  contemporary language design that takes data-oriented principles as
  first-class constraints.
- Nystrom, Robert. *Game Programming Patterns.* Genever Benning, 2014.
  — Chapter 17, "Data Locality," is the accessible introduction for
  programmers coming from an OOP background.
- Insomniac Games. Various engineering talks, 2010–present. — The
  production-scale demonstration that DOD is not academic.

## 4. The catechism

Seven derived commitments:

1. **Measure first.** Assumptions about performance are lies until a
   profiler agrees. The profiler is the arbiter; intuition is the
   hypothesis.
2. **Data layout precedes algorithm.** A cache-coherent O(n²) beats a
   cache-thrashing O(n log n) at realistic sizes, because the cache miss
   is measured in hundreds of cycles and the instruction count is
   measured in handfuls.
3. **Struct-of-Arrays over Array-of-Structs** when the iteration
   dominates the access pattern. Pack the fields you actually read; leave
   the rest elsewhere.
4. **Batch over individual.** Ten thousand orders processed in one pass
   beats ten thousand method calls — both in wall-clock time and in
   readability, because the batch version makes the work legible.
5. **No virtual dispatch in the inner loop.** The indirection cost
   dominates the work. If you need polymorphism, dispatch once outside
   the loop and specialize inside.
6. **Allocations are events to be budgeted**, not conveniences to be
   consumed. The heap is slow; reuse is cheap. A pre-allocated buffer
   outperforms a "clean" list comprehension every time the comprehension
   is in a hot path.
7. **The problem IS the data.** Objects are a convenient fiction; the
   real thing is rows of data being transformed by functions. The
   Data-Oriented mental model is a spreadsheet, not a class diagram.

## 5. Rule shape this axiom generates

- **Forbid** — virtual methods in iterated code, allocations inside hot
  loops, linked lists where arrays would serve, OOP hierarchies that
  scatter related data across the heap, abstractions that obscure memory
  access patterns, "flexibility" knobs that turn inner loops into
  dispatch tables.
- **Require** — measurements before claims of speed, batch APIs for bulk
  operations, contiguous storage for iterated data, explicit separation
  of hot and cold fields.
- **Prefer** — arrays over dicts for small keyspaces, parallel arrays
  (SoA) for bulk, pre-allocated buffers over per-iteration allocation,
  `__slots__` on dataclasses that will exist in quantity, `numpy` or
  `array` where the access pattern justifies it.

Under a Python linter, this axiom generates rules of a particular
character: not "count your cache lines" (Python cannot honestly offer
that), but "do not use a dict where a list would serve," "do not put
a for-loop with a polymorphic method call on the hot path," "prefer
`numpy.ndarray` when the size is known and the operations are
vectorizable," "measure before you claim." The discipline is the
mental model; the rules are its Python-legible shadow.

## 6. The degenerate case

Every axiom has a failure mode. For Data-Oriented, the failure mode is
**premature optimization as identity**.

- Code that is unreadable, not maintainable, and not actually faster
  because the hot path was not where the author thought it was. The
  author skipped the measurement because they "knew" where the cost
  was, and they were wrong.
- Counting cache lines in a script that runs once a day for a minute.
  The total budget for the program's lifetime performance is dominated
  by startup, and the author spent a week on the inner loop.
- Rewriting a readable dict-comprehension into a manual loop "for
  branch prediction" on code that is not on any hot path.
- Performance theater in code that spends 99% of its time waiting on
  the network. The right optimization would have been the `requests`
  `Session` connection pool, not the struct-of-arrays rewrite of the
  response parser.
- Dogmatism that forgets Acton's first rule — *measure*. A purist who
  rejects a clean solution on DOD grounds without profiling is no longer
  doing DOD; they are doing folk performance theology.
- Reaching for `numpy` on a problem with N=12 and then celebrating the
  "speedup" as a win, when the overhead of entering `numpy` exceeds the
  pure-Python alternative at that size.

The test for premature-optimization-as-identity: ask for the profiler
output. A faithful Data-Oriented change has one; an unfaithful one has
a story.

## 7. Exemplar temptation

When writing the Data-Oriented implementation of the canonical task,
the exemplar must navigate two opposite temptations:

- **The OOP shortcut.** It will be tempting to model each order as an
  `Order` object with `validate()`, `price()`, `reserve()`, and
  `notify()` methods, and iterate through a list of them calling each
  method in turn. The Data-Oriented exemplar must refuse this —
  processing must be batched, hot fields must be packed, and the
  per-order method call must give way to a per-stage bulk operation.
- **The C-in-Python parody.** It will also be tempting to pretend Python
  is a systems language, manually unroll loops, use `ctypes`, or contort
  the code to count cycles Python does not actually expose. The exemplar
  must refuse this too. The point is to demonstrate the *mental model*
  in a form Python can honestly express — numpy arrays where the
  operation is vectorizable, `__slots__` dataclasses where objects must
  exist, explicit hot/cold field separation, and batch-oriented APIs.

The faithful Data-Oriented exemplar is the one where: orders are stored
as parallel arrays or structured numpy columns, not as a list of Order
objects; processing is done stage-by-stage over the whole batch, not
order-by-order over all stages; hot fields (price, quantity, status)
live in one structure and cold fields (billing address, customer notes)
live elsewhere; at least one benchmark exists with measured numbers;
and a reader can state the hot loop in one sentence and explain why it
is cache-friendly.

## 8. Rubric — how to recognize a faithful Data-Oriented fixture

- [ ] **Orders are processed in batches**, not one at a time in a method-
      call-per-order loop.
- [ ] **Hot data** (fields touched in every pass) **is separated from cold
      data** (fields touched rarely or once). The separation is visible
      in the data structure definitions.
- [ ] **At least one structure uses Struct-of-Arrays layout** — parallel
      lists, parallel numpy arrays, or a record with list-valued columns
      — where an Array-of-Structs would have been the OO default.
- [ ] **No virtual dispatch in the main processing loop.** Polymorphism,
      if any, is resolved outside the loop. The inner loop calls concrete
      functions on concrete data.
- [ ] **At least one benchmark exists** and is referenced in a comment or
      sibling file, with measured numbers and a brief note on the
      hardware.
- [ ] **Allocations in the main loop are minimized.** Where Python allows,
      buffers are pre-allocated and reused. Hot loops do not build new
      lists that will be immediately discarded.
- [ ] **Data structures are described by their access pattern** in
      comments or naming, not by their "entity identity."
- [ ] **Python-native performance tools are used honestly** — `numpy`,
      `array`, `__slots__`, `dataclasses(frozen=True, slots=True)` — not
      as cosplay of C, but as the honest Python expression of a
      data-oriented mental model.
- [ ] **Performance assumptions are explicit.** The code or an adjacent
      comment states which loops matter, which do not, and why.
- [ ] **A reader can state, in one sentence, what the hot loop is and
      why it is cache-friendly** (or, in Python's honest idiom, why it
      is vectorizable / memory-local).

Ten out of ten is Data-Oriented. Eight or nine is a draft. Seven or
fewer is OOP code wearing a performance hat.

---

## See also

- [docs/philosophy/functional.md](functional.md) — The sharpest conflict
  in the entire matrix. Functional requires immutability (copy on
  change); Data-Oriented requires in-place batch updates for cache
  locality. These two axioms are nearly irreconcilable on shared memory.
- [docs/philosophy/classical.md](classical.md) — Classical OOP
  hierarchies are this school's canonical anti-pattern. The Shape
  hierarchy example from every OOP textbook is the Data-Oriented
  school's example of how not to lay out data.
- [docs/principles.md](../principles.md) — This school's contribution
  to the universal core is narrower: it mostly adds rules, rather than
  changing them, because its prime concern (memory layout) is largely
  orthogonal to the three pillars.
