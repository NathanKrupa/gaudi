# Functional / Algebraic — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/functional.md](../../../../docs/philosophy/functional.md)
**Rubric score:** 10/10

The third reference implementation of the canonical task, completing
the triangle **Classical ↔ Pragmatic ↔ Functional** that every later
school's exemplar can be compared against. Every value is immutable.
Every error is returned as data. Every function is a pure
transformation. The core imports nothing from logging, os, requests,
or the clock.

---

## Running it

```bash
conda run -n Oversteward pytest tests/philosophy/functional/ -v
```

Fourteen tests exercise the same acceptance criteria the Classical
and Pragmatic exemplars pass — the ten parametrized seed-data cases
plus four Functional-specific assertions:

1. ``test_confirmed_order_decrements_available_inventory`` — threads
   the world through two successive calls, demonstrating that the
   reservation persisted without mutation.
2. ``test_out_of_stock_order_does_not_partially_reserve`` — rejected
   orders return the world *unchanged* (same object identity), and
   the follow-up order still succeeds at full quantity.
3. ``test_process_order_is_referentially_transparent`` — calling
   ``process_order`` twice on the same world produces equal
   outcomes and equal worlds. Catechism #7 as a test.
4. ``test_core_is_free_of_io_imports`` — the pipeline module is
   grepped for forbidden imports (``logging``, ``os``, ``requests``,
   ``sqlite3``, ``from time import``) and for any ``datetime.now(``
   call. Catechism #3 as a structural proof.

---

## Directory shape

```
canonical/
├── README.md    # this file
├── result.py    # Ok[T] / Err[E] frozen value types
├── models.py    # 10 frozen dataclasses, zero methods
└── pipeline.py  # pure functions + process_order composition
```

Three source files. No service layer, no infrastructure layer, no
composition root separate from the caller. The input state is a
single ``World`` record; the output is a ``(Outcome, World)`` tuple.
Threading the new world through successive calls is the caller's
job, not the pipeline's.

---

## Rubric score against [functional.md](../../../../docs/philosophy/functional.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | No mutation of passed-in arguments | ✓ | Every function returns new values. ``reserve_inventory`` builds a fresh dict. ``process_order`` uses ``dataclasses.replace`` to produce a new ``World``. |
| 2 | All domain dataclasses are ``frozen=True`` | ✓ | Every class in ``models.py`` is ``@dataclass(frozen=True)`` and every class has **zero** methods. Helpers that read from records live as free functions in ``pipeline.py``. |
| 3 | I/O isolated at the edges | ✓ | ``pipeline.py`` imports only ``dataclasses.replace``, ``datetime``, ``decimal.Decimal``, ``typing.Mapping``, and the local ``models`` + ``result`` modules. No ``logging``, ``os``, ``requests``, ``sqlite3``, or ``datetime.now()``. Time is passed in as a value. ``test_core_is_free_of_io_imports`` is the structural enforcement. |
| 4 | Errors are returned as values, not raised | ✓ | ``Ok[T]`` and ``Err[E]`` are frozen dataclasses in ``result.py``. Every validation step returns a ``Result``; the pipeline uses ``isinstance`` early-return checks to thread errors. No ``raise`` anywhere except the test file. |
| 5 | No shared mutable globals | ✓ | The pipeline has no module-level state. Reservation IDs are passed in as function arguments; there is no ``itertools.count`` holding a hidden counter. |
| 6 | For-loops with accumulators absent where map/filter/reduce would serve | ✓ mostly | ``compute_subtotal`` is a generator + ``sum``. ``find_insufficient_skus`` is a comprehension. ``reserve_inventory`` is a dict comprehension plus one small delta-building loop. ``resolve_lines`` is a small for-loop with early return on error — the honest Python translation of threading errors, rather than pretending Python has ``traverse``. |
| 7 | Type annotations are dense and meaningful | ✓ | Every public function's parameters and return are typed. ``Result`` uses ``Generic[T]``. No bare ``Any``. No ``Optional`` where a ``Result`` would tell the truth more precisely — the one ``\| None`` case is ``Order.promo_code``, which is a field of the input, not a return value. |
| 8 | Inheritance only for ``Protocol`` / ABC definitions | ✓ | Zero inheritance in this exemplar. Frozen dataclasses do not count as inheritance — they are value records. No ``Protocol``s are needed because the pipeline uses plain ``Mapping`` types at every boundary. |
| 9 | Composition is explicit | ✓ | ``process_order`` is a straight-line composition of ``validate_customer`` → ``resolve_lines`` → ``find_insufficient_skus`` → ``compute_final_price`` → ``reserve_inventory``. Each step is a named pure function that can be unit-tested in isolation. |
| 10 | Any function in the core can be evaluated in the REPL | ✓ | Demonstrable: ``from tests.philosophy.functional.canonical.pipeline import compute_subtotal; compute_subtotal(())`` returns ``Decimal(0)`` without staging a database, a filesystem, or a clock. ``test_process_order_is_referentially_transparent`` exercises the stronger property. |

**10/10.**

---

## The findings on this exemplar

Running ``gaudi check`` against the Gaudí project with this exemplar
merged produces **one universal finding** on the exemplar files (plus
the usual project-level infra findings that are unrelated to the
exemplar):

### SMELL-003 LongFunction on ``process_order`` (×1, ~41 lines)

``process_order`` is the composition root of the five-stage
pipeline. At ~41 lines it exceeds the ``SMELL-003`` threshold. This
is **universal** (no school scope excludes it), and it fires under
every valid school. It is the honest cost of threading errors
through five stages with explicit early returns in Python — a
language that lacks ``do``-notation or a native ``bind`` operator.

The Functional discipline accepts this cost deliberately: the
alternative (Haskell-style monad transformer stacks, or a hand-rolled
``bind``/``map``/``and_then`` combinator library) is precisely the
abstraction-astronautics that [functional.md](../../../../docs/philosophy/functional.md)
section 6 warns against. One long composition root with explicit
pattern matching is the honest Python translation; a 200-line monad
combinator library would score 10/10 on the rubric too, and the
readers of the code would be worse off.

### No OOP-specific findings

**Zero** findings from the OOP-targeted rules:

- ``SMELL-014 LazyElement`` (scoped to Pragmatic/Unix/Functional/DO)
  does not fire because the dataclasses have zero methods.
- ``SMELL-022 DataClassSmell`` (scoped to Classical/Convention) does
  not fire — and would only matter under schools this exemplar is
  not targeting.
- ``SMELL-009 FeatureEnvy``, ``SMELL-020 LargeClass``, ``SMELL-023
  RefusedBequest``, ``DOM-001 AnemicDomainModel`` all stay silent.

This is the property ``test_functional_exemplar_findings_are_scope_invariant``
pins: under every valid school, the finding set on this exemplar is
bit-identical. Because the exemplar trips only universal rules, the
scope system has nothing to filter — and the stability is the proof
that the universal rules really are universal.

---

## Comparison with Classical and Pragmatic

| Property | Classical | Pragmatic | Functional |
|---|---|---|---|
| Files | 8 | 1 | 3 |
| Impl lines | ~450 | ~120 | ~220 |
| Public classes | 12 | 0 | 10 (all frozen dataclasses, zero methods) |
| Protocols / interfaces | 5 | 0 | 0 |
| Single-method wrapper classes | 6 | 0 | 0 |
| Mutation of passed-in state | some (inventory) | yes | **none** |
| Errors raised / returned | raised (ValidationFailure) | raised (ValueError) | returned (Err) |
| Composition root lines | short (orchestration) | ~80 (one function) | ~41 |
| Scope-sensitive gaudi findings | YES (SMELL-014 false positives under non-Classical schools) | no | no |
| Scope-invariant gaudi findings | — | SMELL-003 + SMELL-004 + STRUCT-021 | SMELL-003 only |

Three observations from the triangle:

1. **Classical is the only scope-sensitive exemplar so far.** It
   uses single-method wrapper classes that Pragmatic/Unix/Functional/DO
   consider dead weight. The matrix test pins this as "same code,
   different verdict."

2. **Functional is strictly cleaner than Pragmatic** under Gaudí's
   universal criteria (one universal finding vs. three). This is the
   honest trade-off: Functional buys the clean finding profile with
   more structural machinery — the ``Result`` type, ``World`` value,
   frozen dataclasses, and free-function helpers. Pragmatic buys its
   smaller file with SMELL-003 + SMELL-004 + STRUCT-021 findings.
   Neither is better; they are faithful to different axioms about
   where complexity should live.

3. **All three pass the same 12 acceptance tests** against the same
   shared seed data. The canonical task's invariants are enforced
   identically. What differs is *how* the three disciplines spend
   their complexity budget.

---

## Notes for future exemplars

- **Convention (Django)** will almost certainly trip ``SMELL-020
  LargeClass`` and ``ARCH-002 GodModel`` on its model classes — and
  both rules are scoped *away* from Convention in the audit. That
  asymmetry is the next matrix row to pin.
- **Data-Oriented** will be the first exemplar expected to refuse
  this file's ``resolve_lines`` comprehension style in favour of
  manual fused loops. The contrast with Functional on that exact
  question is the Functional-vs-DO teaching moment.
- **Event-Sourced** will look closest to Functional in the
  write-path (immutable events, pure command handlers) but will
  introduce a projection layer the other exemplars do not have.

---

## See also

- [docs/philosophy/functional.md](../../../../docs/philosophy/functional.md) — The axiom sheet.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [docs/rule-registry.md](../../../../docs/rule-registry.md) — The rule audit, including the scope tags the matrix test verifies.
- [tests/philosophy/classical/canonical/README.md](../../classical/canonical/README.md) — The Classical reference exemplar.
- [tests/philosophy/pragmatic/canonical/README.md](../../pragmatic/canonical/README.md) — The Pragmatic reference exemplar.
