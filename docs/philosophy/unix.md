# Unix / Minimalist — Axiom Sheet

> *Do one thing well. Compose via text.*

---

## 1. Prime axiom

> **A program should do one thing well. Large behavior is built by composing
> small programs through a shared, universal, human-readable interface —
> and the smaller the program, the more honest it can be about what it does.**

The Unix school treats complexity as the enemy and composition as the cure.
A small tool can be held entirely in the reader's head. A pipeline of small
tools inherits the readability of each of its stages, because the interface
between stages is plain text that any engineer can inspect with `cat`. Large
monolithic programs trade that inspectability for convenience, and then
charge interest on the trade for the rest of their lives.

## 2. The rejected alternative

Unix architecture refuses:

- **Frameworks that own the main loop.** The Rails/Django/Spring model —
  where the framework calls your code and you can only hook into its
  blessed extension points — is the direct negation of the Unix axiom.
- **Binary protocols by default.** A protocol you cannot debug with
  `less` is a protocol that will, sooner or later, require tooling the
  Unix tradition has spent fifty years avoiding.
- **Deep inheritance hierarchies.** An object whose behavior is distributed
  across eight superclasses is opaque in a way no Unix program can afford.
- **Abstraction layers that do not compose.** A wrapper, adapter, or
  facade that exists to make one API look like another — but cannot be
  used independently or piped into something else — adds mass without
  adding composability.
- **Dependencies for what the standard library provides.** Every dependency
  is a future compatibility problem; the first question is always "can we
  do without?"
- **Vendor lock-in.** Any API surface that cannot be replaced with
  equivalent plumbing in an afternoon is a liability held against the
  project.
- **Import-time side effects.** A module that changes the world when
  imported is a module that cannot be trusted to do *only* what its
  interface claims.

## 3. Canonical citations

- McIlroy, Doug. "Programming pearls: a little language." *Communications
  of the ACM*, 1986. — The originating piece on Unix pipes as the
  composition model.
- Kernighan, Brian & Pike, Rob. *The Unix Programming Environment.*
  Prentice Hall, 1984. — The canonical text. Every example is still
  pedagogically alive.
- Raymond, Eric S. *The Art of Unix Programming.* Addison-Wesley, 2003. —
  The explicit enumeration of the seventeen rules (modularity, clarity,
  composition, separation, simplicity, parsimony, transparency,
  robustness, representation, least surprise, silence, repair, economy,
  generation, optimization, diversity, extensibility).
- Pike, Rob. "Notes on Programming in C." 1989. — The five rules that
  compress much of the Unix sensibility into five paragraphs.
- Pike, Rob. "Simplicity is Complicated." dotGo, 2015. — The Go
  standard-library philosophy as modern Unix inheritance.
- Gancarz, Mike. *The Unix Philosophy.* Digital Press, 1994. — An
  independent, accessible gloss on the same principles.
- Salus, Peter. *A Quarter-Century of Unix.* Addison-Wesley, 1994. —
  The historical context for why this philosophy took the shape it did.

## 4. The catechism

Seven derived commitments:

1. **Do one thing well.** A program whose description needs the word "and"
   is two programs sharing a binary. Split them.
2. **Compose via standard streams.** Text flowing through stdin and stdout
   is the universal interface, because every tool ever written for Unix
   can already speak it.
3. **Flat is better than nested.** A directory tree with three levels is
   a tree that can be held in the head. A tree with ten levels is a tree
   that requires a map.
4. **Configuration files over code.** Tuning is not recompilation. A
   plain-text config (TOML, INI, even just environment variables) lets
   the same program serve many masters.
5. **Minimal dependencies.** The first question for any dependency is
   "can the stdlib do this?" The second is "is the saving worth the
   compatibility surface?" The default answer to "should we add a library?"
   is no.
6. **Worse is better.** A simple solution that is 90% correct today beats
   a perfect solution shipped next year. Richard Gabriel's phrasing, but
   the sentiment is older and the Unix tradition is its native home.
7. **The standard library is the architecture.** Your project's
   architecture should be derivable from what is in the stdlib, plus a
   very small number of additions each of which you could justify aloud
   in one sentence.

## 5. Rule shape this axiom generates

- **Forbid** — framework lock-in, deep inheritance, non-text configuration
  when text would serve, dependencies the stdlib duplicates, monolithic
  entry points that do multiple jobs, import-time side effects, modules
  that cannot be imported independently.
- **Require** — each module invokable as a standalone program, plain-text
  data formats at boundaries, meaningful exit codes, stderr for diagnostics
  and stdout for data, composable shell pipelines that reproduce behavior.
- **Prefer** — flat package layouts, small independent scripts over one
  large application, plain dicts and tuples at module boundaries over
  custom classes, the `re` module over a PEG parser, `json` over a
  bespoke serialization format.

The Unix axiom is the one the Gaudí project itself most resembles at the
tool level: `gaudi check` is a program that reads files and writes a
report to stdout, with findings formatted so that `grep ERROR` works.
That is not an accident — it is an inheritance.

## 6. The degenerate case

Every axiom has a failure mode. For Unix, the failure mode is
**minimalism as pride**.

- Shell script spaghetti — seven thousand lines of Bash because "it
  avoided a dependency on Python." The dependency has been replaced by
  a custom, untested, unmaintainable language embedded inside a shell.
- Reinventing libraries to avoid importing them, producing weaker,
  buggier versions of well-tested wheels.
- A dozen tiny programs so fragmented that no single person can hold
  the whole system in their head. The composition was supposed to be the
  feature; instead it has become the liability.
- "Small" that means "partial" — a tool that does its one thing, but
  does it halfway, and leaves the other half as an exercise for the user
  who expected it to work.
- The Suckless-pilled engineer who ships a broken text editor because
  any dependency is impure. Minimalism has become an identity, and the
  identity is doing the work that judgment should do.
- Hubris masquerading as humility: "We don't need Django; we'll write
  our own web framework." Two years later the project has reinvented
  three-quarters of Django, badly, and shipped nothing.

The test for minimalism-as-pride: ask whether a reasonable reader would
reach for the same tools. If the answer is "no, they would have used
`requests` / `click` / `pytest` and saved themselves a month," the
minimalism has turned into ceremony.

## 7. Exemplar temptation

When writing the Unix implementation of the canonical task, the exemplar
must navigate two opposite temptations:

- **The convenience shortcut.** It will be tempting to reach for Django,
  SQLAlchemy, Pydantic, Click, or FastAPI. The Unix exemplar must refuse
  — the point is that the stdlib and small independent scripts can carry
  this load, and the discipline of refusing is the teaching. That refusal
  is what makes the exemplar faithful.
- **The ceremonial shortcut.** It will also be tempting to refuse the
  `re` module, write a custom parser, refuse `json`, invent a framing
  protocol. The Unix exemplar must refuse this too. The stdlib is not
  the enemy; needless dependencies are. Using `json.dumps` to serialize
  events between pipeline stages is exactly what the Unix tradition
  recommends — plain text, a universal parser, nothing fancy.

The faithful Unix exemplar is the one where: the order pipeline is a
sequence of small Python scripts, each of which reads JSON-lines from
stdin and writes JSON-lines to stdout; each script has a `main()` that
can be invoked as `python order_validate.py < orders.jsonl`; the
dependency list is `[]`; the directory tree is flat; and a shell
one-liner can pipe all the stages together end-to-end.

## 8. Rubric — how to recognize a faithful Unix fixture

- [ ] **The implementation is composed of small, independent modules**,
      each with a `main()` or equivalent CLI entry point.
- [ ] **Inter-module communication is via plain data** — stdin/stdout
      streams of JSON-lines, or function returns of plain dicts/tuples.
      No class hierarchies cross module boundaries.
- [ ] **Dependencies beyond the Python standard library are zero**, or
      every non-stdlib dependency is justified in a one-sentence comment
      naming the stdlib gap it fills.
- [ ] **The directory tree is flat** — one or two levels, readable at a
      glance with `ls`.
- [ ] **Configuration lives in a plain-text file**, not in Python code.
      The exemplar demonstrates a config being loaded and used.
- [ ] **Every module can be invoked independently from the command line**
      with meaningful behavior. `python validate.py --help` works. The
      full pipeline is reproducible as a shell one-liner.
- [ ] **Exit codes communicate success or failure** at the OS level.
      Stderr carries diagnostics; stdout carries data.
- [ ] **No framework magic.** No decorators that mutate globals, no
      metaclasses, no import-time side effects, no auto-discovery of
      classes by walking the module tree.
- [ ] **Classes exist only where a module could not replace them.** If a
      class is just a namespace for related functions, it is a module in
      disguise and should be dissolved.
- [ ] **A shell pipeline of the modules reproduces the end-to-end
      behavior.** `cat orders.jsonl | python validate.py | python
      price.py | python reserve.py | python notify.py` produces the
      same results as the in-process run.

Ten out of ten is Unix. Eight or nine is a draft. Seven or fewer is a
framework application with a minimalist accent.

---

## See also

- [docs/philosophy/convention.md](convention.md) — Unix's structural
  opposite. A convention-driven framework and a Unix pipeline are
  irreconcilable axioms about where complexity should live.
- [docs/philosophy/classical.md](classical.md) — Classical architecture
  builds cathedrals; Unix builds toolsheds. Both can be beautiful; they
  are beautiful by different measures.
- [docs/principles.md](../principles.md) — Principle #7 (layers must
  earn their existence) is the principle closest to the Unix sensibility
  in Gaudí's universal core.
