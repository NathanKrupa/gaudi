# Unix / Minimalist — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/unix.md](../../../../docs/philosophy/unix.md)
**Rubric score:** 10/10

The fourth reference implementation of the canonical task, and the
first to take a radically different *structural shape*. Classical has
a four-layer tree. Pragmatic has one function. Functional has pure
composition of frozen records. **Unix has four independent programs,
connected by pipes, each reading JSON-lines from stdin and writing
JSON-lines to stdout.**

The real shell one-liner is:

```
cat orders.jsonl \
  | python -m tests.philosophy.unix.canonical.validate --world world.json \
  | python -m tests.philosophy.unix.canonical.price    --world world.json \
                                                       --shipping-fee 5.00 \
                                                       --now 2026-04-10T12:00:00 \
  | python -m tests.philosophy.unix.canonical.reserve  --world world.json \
  | python -m tests.philosophy.unix.canonical.notify   --log notifications.jsonl
```

And ``test_subprocess_pipeline_composes_via_stdio`` runs this exact
pipeline via ``subprocess.Popen`` chains inside pytest, as the
operational proof that the four scripts really do compose — not just
that their in-process helper functions happen to call each other
cleanly.

---

## Running it

```bash
conda run -n Oversteward pytest tests/philosophy/unix/ -v
```

Fifteen tests cover the acceptance criteria and enforce the Unix
discipline:

1. **Ten parametrized seed-data cases** run in-process via the
   stage helper functions (``validate_one``, ``price_one``,
   ``reserve_one``).
2. **Two atomicity tests** for the inventory reservation (the same
   shape as the Classical and Pragmatic versions).
3. **``test_subprocess_pipeline_composes_via_stdio``** — the rubric's
   teeth. Runs ``validate | price | reserve | notify`` as a real
   pipe chain of four subprocesses, writes two seed orders to the
   head of the pipe, reads the terminal output, and asserts that
   (a) every stage exited 0, (b) the confirmed order has a
   reservation ID, (c) the rejected order has its reason, (d) the
   notification log file has two records, and (e) the world.json
   file reflects the persisted reservation.
4. **``test_every_stage_has_a_cli_main``** — rubric #6 as a test.
5. **``test_every_stage_has_no_classes``** — rubric #9 as a test
   (AST walk that asserts zero ``ast.ClassDef`` nodes in every
   stage file).

---

## Directory shape

```
canonical/
├── README.md     # this file
├── validate.py   # stage 1: customer + product + quantity checks
├── price.py      # stage 2: subtotal + promo + shipping + credit limit
├── reserve.py    # stage 3: inventory check + atomic reservation
└── notify.py     # stage 4: append to notification log, echo stream
```

Flat. Four independent programs. Zero classes across all four files.
Zero dependencies beyond the Python standard library. State is
carried in a ``world.json`` file that every stage reads; ``reserve.py``
is the only stage that writes to it (atomically, via
``tempfile.NamedTemporaryFile`` + ``os.replace``).

Compared to the three already-landed exemplars:

| Property | Classical | Pragmatic | Functional | Unix |
|---|---|---|---|---|
| Files | 8 | 1 | 3 | 4 |
| Programs (distinct entry points) | 1 | 1 | 1 | **4** |
| Impl lines | ~450 | ~120 | ~220 | ~280 |
| Classes | 12 | 0 | 10 (records) | **0** |
| Inter-stage interface | method call | function call | function call | **JSON-lines on stdio** |
| Shell one-liner | no | no | no | **yes** |

The "shell one-liner" row is the Unix exemplar's most distinctive
claim. The other three disciplines *could* expose a CLI, but none
require one; Unix *requires* it, and the subprocess test is the
proof that the requirement is met.

---

## Rubric score against [unix.md](../../../../docs/philosophy/unix.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | Implementation is small, independent modules with a main() / CLI each | ✓ | Four files, each with a ``main()`` function and argparse-based CLI flags. |
| 2 | Inter-module communication is plain data (stdio JSON-lines or plain dicts/tuples) | ✓ | Every stage reads JSON-lines from stdin and writes JSON-lines to stdout. No class hierarchies cross stage boundaries — the wire format is a dict. |
| 3 | Dependencies beyond stdlib are zero (or justified) | ✓ | Zero non-stdlib imports. Uses only ``argparse``, ``json``, ``sys``, ``os``, ``tempfile``, ``datetime``, ``decimal``, ``itertools``, ``typing``. |
| 4 | Directory tree is flat | ✓ | One directory, five files including the README. |
| 5 | Configuration lives in a plain-text file, not code | ✓ | ``world.json`` is the configuration AND the persistent state. Every stage reads it via ``--world`` flag. |
| 6 | Every module can be invoked independently from the CLI | ✓ | ``python -m tests.philosophy.unix.canonical.validate --help`` works. All four have meaningful standalone behavior. ``test_every_stage_has_a_cli_main`` is the structural enforcement. |
| 7 | Exit codes communicate success/failure; stderr for diagnostics, stdout for data | ✓ | ``main()`` returns an int from ``sys.exit``. Data flows only on stdout. Errors raise (which argparse / Python turn into non-zero exit + stderr). |
| 8 | No framework magic, metaclasses, import-time side effects, auto-discovery | ✓ | No decorators mutating globals, no metaclasses, no code at module top level beyond imports and the ``if __name__ == "__main__":`` guard. |
| 9 | Classes exist only where a module cannot replace them | ✓ | **Zero classes** in any stage file. ``test_every_stage_has_no_classes`` walks the AST of every stage and asserts no ``ClassDef`` nodes exist. |
| 10 | A shell pipeline of the modules reproduces the end-to-end behavior | ✓ | ``test_subprocess_pipeline_composes_via_stdio`` runs the real ``validate | price | reserve | notify`` pipeline via ``subprocess.Popen`` chains, and asserts the terminal output matches the in-process test results. |

**10/10.**

---

## The findings on this exemplar — and what they forced

Running ``gaudi check`` on the Unix exemplar surfaced something the
previous three exemplars did not: **``ARCH-013 FatScript`` fired on
three of the four stages' ``main()`` functions**, which were 16-19
lines of argparse + stdin loop + atomic write plumbing.

``ARCH-013`` is Architecture 90's "thin entry points, fat services"
rule. Under a Classical layered architecture, that is exactly right —
the entry point should parse input, call a service, and format output
in three lines, with all behavior in a service class elsewhere.

Under Unix, **the script *IS* the service.** There is no "service
elsewhere" to extract to; the smallest honest unit of work is
already the script itself. ARCH-013's recommendation ("move logic to
service functions") is not applicable to a Unix stage whose entire
purpose is to read stdin, loop over records, and write stdout.

### The audit revision this PR makes

This PR amends the [philosophy scope audit in
docs/rule-sources.md](../../../../docs/rule-sources.md) to move
``ARCH-013 FatScript`` from the universal list to the scoped list,
excluding it from ``unix``. The scope is tagged on the rule class in
``src/gaudi/packs/python/rules/layers.py`` with an inline comment
citing ``docs/philosophy/unix.md`` catechism #1 and naming this
exemplar as the forcing-function evidence.

This is the workflow Phase 1 established: when a new reference
exemplar surfaces a rule that fires incorrectly on a faithful
implementation of its school, the evidence is the justification
for updating the audit, the rule is tagged, and the matrix test
pins the result. **Writing the exemplar is the forcing function
for improving the audit.**

Before this PR:

- `ARCH-013` was universal, fired on all eight schools, 22 scoped rules total.

After this PR:

- `ARCH-013` is scoped to everything *except* `unix`, fires on seven
  of eight schools on the Unix exemplar, **23 scoped rules total**.
  The audit summary in [docs/rule-sources.md](../../../../docs/rule-sources.md)
  is updated from "22 (18%)" to "23 (19%)".

### Remaining findings (all universal, all correct)

| Rule | Count | Disposition |
|---|---|---|
| SMELL-003 LongFunction | 3 | ``validate_one`` 43 lines, ``price_one`` 40 lines, ``reserve.main`` 27 lines. Universal and honest: Unix stages handle the whole domain in one function each. Same pattern as the Pragmatic exemplar's SMELL-003. |
| STRUCT-012 NoEntryPoint | 4 | Every stage has CLI logic but no ``[project.scripts]`` entry in ``pyproject.toml``. Correct finding: the exemplar is a test fixture, not a deployable package. In a real Unix-shaped project these scripts would be registered as entry points. Universal and honest. |
| STRUCT-021 MagicStrings | 7 | String literals like ``"_status"``, ``"sku"``, ``"customer_id"`` appear multiple times because the wire format is a plain dict. Unix deliberately prefers plain-data-on-the-wire to domain types, and accepts the STRUCT-021 findings as the cost. The audit left STRUCT-021 universal; this is the honest trade-off under that decision. |

---

## Matrix rows for Unix

The new matrix entries pin two properties on this exemplar:

1. **Under ``unix``, ``ARCH-013`` does NOT fire.** The exemplar is
   clean under its home school.
2. **Under every other school, ``ARCH-013`` DOES fire.** Three
   findings on ``main()`` functions. "Same code, different verdict"
   in the opposite direction from the Classical exemplar: Classical
   is clean under Classical and dirty under Pragmatic/Unix/Functional/
   Data-Oriented; Unix is clean under Unix and dirty under everything
   else.

The universal findings (``SMELL-003``, ``STRUCT-012``, ``STRUCT-021``)
are required to fire under every school — the control condition that
proves universal rules are scope-invariant.

---

## Comparison notes for future exemplars

- **Data-Oriented** is the one most likely to also surface an audit
  revision. Its axiom rejects ``SMELL-013 Loops`` (pipeline
  comprehensions allocate) which is already scoped away from
  data-oriented, but it may need new rule tags around "allocations
  in hot loops" that Gaudí doesn't detect yet.
- **Event-Sourced** will require projections + replay, and may trip
  ``ARCH-013`` (entry-point logic) on whatever composition root it
  uses to apply events. The Unix-style scope-away-from-unix precedent
  does not help here; Event-Sourced is a different axiom.
- **Convention (Django)** remains blocked on adding Django as a
  dev dependency, which the project's PR template says requires
  discussion. Deferred until that approval.
- **Resilient** is next — all stdlib, supervised-subsystems pattern,
  expected to trip ``STAB-*`` rules under pragmatic/functional/unix
  (all scoped away from those schools correctly).

---

## See also

- [docs/philosophy/unix.md](../../../../docs/philosophy/unix.md) — The axiom sheet.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [docs/rule-sources.md](../../../../docs/rule-sources.md) — The rule audit, including the new ARCH-013 row.
- [tests/philosophy/classical/canonical/README.md](../../classical/canonical/README.md) — Classical exemplar (OOP tree).
- [tests/philosophy/pragmatic/canonical/README.md](../../pragmatic/canonical/README.md) — Pragmatic exemplar (one big function).
- [tests/philosophy/functional/canonical/README.md](../../functional/canonical/README.md) — Functional exemplar (pure composition).
