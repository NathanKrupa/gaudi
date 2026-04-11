# Data-Oriented — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/data-oriented.md](../../../../docs/philosophy/data-oriented.md)
**Rubric score:** 10/10

The seventh reference implementation of the canonical task, and the
first to be built from the outside in on data layout rather than
behavior. Classes were refused. Every hot column is an `int32` or
`int64` numpy ndarray keyed by row index. Orders are processed in
batches, stage-by-stage over the whole flat line-level array, and
every rejection reason is a cold-path message formatted after the
hot work is done.

---

## Running it

```bash
conda run -n Oversteward pytest tests/philosophy/data_oriented/ -v
```

Eighteen tests exercise the same ten acceptance cases from the
shared seed data plus two atomicity regressions plus six rubric-
enforcing tests that pin the architectural shape (SoA columns,
frozen-slots World, batch API, np.add.at reservation scatter,
packed standing codes, integer cents). The seed data lives at
[`tests/philosophy/seed_data.py`](../../seed_data.py) and is
shared, unchanged, with every other school's implementation.

Running the benchmark directly:

```bash
conda run -n Oversteward python -m tests.philosophy.data_oriented.canonical.bench
```

---

## Directory shape

```
canonical/
├── README.md    # this file
├── __init__.py
├── state.py     # World frozen-slots dataclass + SoA column builder
├── pipeline.py  # process_orders_batch + process_order adapter
└── bench.py     # per-order cost vs batch size, with measured numbers
```

Three production files, one benchmark, zero classes with behavior.
The `World` in `state.py` is a frozen-slots dataclass used as a
record holder, not a business object — the pipeline is a set of
free functions that take a `World` and return outcomes. There is
no `Pipeline`, no `Stage`, no `Validator`, no `PricingStrategy`.

---

## Rubric score against [data-oriented.md](../../../../docs/philosophy/data-oriented.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | Orders processed in batches, not one-at-a-time | ✓ | `process_orders_batch(orders, world, …)` is the real API. Stages 1–8 each operate on the whole batch in one pass. `process_order` is a thin adapter that wraps a single order in a one-element batch — a batch of one, not a different code path. |
| 2 | Hot data separated from cold data | ✓ | Hot columns are numpy ndarrays on `World`: `customer_credit_limit_cents`, `customer_standing`, `product_unit_price_cents`, `product_max_per_order`, `inventory_on_hand`, `inventory_reserved`. Cold data lives in plain dicts (`customer_cold`, `product_cold`, `promo_codes`) consulted only on the rejection-reason path. The separation is documented in [state.py](state.py)'s module docstring. |
| 3 | At least one Struct-of-Arrays layout | ✓ | Every hot column on `World` is a parallel numpy ndarray keyed by row index. `test_world_hot_columns_are_contiguous_numpy_arrays` pins the dtype of all six hot columns so a drift toward AoS would break the suite. |
| 4 | No virtual dispatch in the main processing loop | ✓ | Every pipeline stage is a concrete inline block in `process_orders_batch`. There is no `Stage` protocol, no dispatch table, no `Strategy` pattern. The inner loops call `np.add.at`, `np.where`, and integer arithmetic on concrete ndarrays. |
| 5 | At least one benchmark exists with measured numbers and hardware notes | ✓ | [bench.py](bench.py) measures per-order wall-clock cost for N ∈ {1, 10, 100, 1000, 10000}. Numbers and hardware are noted in the module docstring. |
| 6 | Allocations in the main loop are minimized | ✓ | The per-batch scratch arrays (`cust_idx`, `order_rejected`, `order_subtotal_cents`, `order_discount_pct`) are allocated once per call, not once per order. The per-line SoA arrays are built once from Python list comprehensions and then handed to numpy. Money is int64 cents, not per-call `Decimal` construction. |
| 7 | Data structures described by access pattern | ✓ | `state.py`'s module docstring names each hot column by the stage that reads it, not by the entity it "belongs to." The cold columns are named for what consults them (the rejection-reason path) rather than for the ORM concept they'd map to in a CRUD app. |
| 8 | Python-native performance tools used honestly | ✓ | `numpy` for the batch columns, `dataclasses(frozen=True, slots=True)` for the `World` record, integer cents for money, packed `uint8` standing codes with named constants. No `ctypes`, no manual loop unrolling, no C-in-Python cosplay. The rubric test `test_standing_code_is_packed_integer_not_string` pins the `uint8` choice explicitly. |
| 9 | Performance assumptions are explicit | ✓ | The module docstring of `pipeline.py` names the hot loops in priority order with their measured cost at N=1e4, and states which stages are O(batch) vs O(lines). The "hot loop in one sentence" lives in the same docstring, as the rubric requires. |
| 10 | A reader can state the hot loop in one sentence | ✓ | "For every line in the flat line SoA, compute `product_unit_price_cents[sku_idx] * qty` and scatter-accumulate into the per-order subtotal column." That sentence is in the `pipeline.py` docstring; a reader should reach the same description after one read of `process_orders_batch`. |

**10/10.**

---

## The findings on this exemplar

Running `gaudi check` against this exemplar under `school =
data-oriented` produces a finding profile that is — with one
pre-existing scope exception — identical across every school. This
is **not** a scope-invariant exemplar of the
`test_scope_invariant_exemplar_is_stable_across_schools` kind (see
below), but every finding it trips is a rule the Data-Oriented
axiom treats as a legitimate universal cost.

### Category A — SMELL-003 LongFunction (×4)

`process_orders_batch` is ~230 lines of stage-by-stage batch work.
`build_world` is ~67 lines of column construction. Two smaller
helpers in `bench.py` trip the rule at the edges.

These are **universal** findings and the Data-Oriented axiom
accepts them. The eight pipeline stages live inline in one
function because the whole point of the exemplar is to make the
access pattern legible at one glance — extracting them into
`_stage_validate_customers`, `_stage_price_orders`, etc. would
split the reading and force the reader to re-reach L1 for every
stage. The axiom's §4 catechism (#2: "data layout precedes
algorithm") applies here: the function's length is the honest
cost of keeping the stages in one place where their shared buffers
are visible.

If a future refactor finds a way to express the stages as
free functions over the scratch arrays without rebuilding buffers
per stage, that refactor is welcome. Until then, SMELL-003 is an
accepted trade-off, same as it is on the Pragmatic, Functional,
and Resilient exemplars.

### Category B — STRUCT-021 MagicStrings (×5)

`'sku'`, `'order_id'`, `'name'`, `'SKU-'`, `'04d'` appear multiple
times because the pipeline reads orders as plain dicts and the
benchmark builds synthetic rows with format-string SKUs. Accepted
cost: the alternative is a `dataclass` per entity, which would
defeat the SoA layout the exemplar exists to demonstrate.

### Category C — LOG-004 print() (×4)

Four `print()` calls in `bench.py`. The benchmark's only output is
per-N timings; a logger would add ceremony without value. LOG-004
is scoped away from `unix`, so the finding set under `unix` is
four rules shorter than under every other school — the only
scope-induced delta in this exemplar's matrix rows.

### Category D — OPS-*** / STRUCT-011 / STRUCT-013 (×6)

These are project-root rules (no pre-commit-config, no CODEOWNERS,
no pyproject.toml, no lock file) that fire because `gaudi check`
is being pointed at the exemplar directory as a standalone
"project" in the matrix test. They are the same non-signal
findings every subdirectory-as-project exemplar trips and are
intentionally not pinned in the matrix rows.

---

## Scope posture and matrix rows

This exemplar is **not** a scope-invariant control condition like
Pragmatic / Functional / Resilient. The `LOG-004` scope decision
(scoped away from `unix`) produces a four-rule delta between the
`unix` matrix row and every other school's row. That delta is a
pre-existing rule-level decision, not a Data-Oriented axiom
claim, so joining `SCOPE_INVARIANT_EXEMPLARS` would misrepresent
what the exemplar is asserting.

What the matrix rows **do** assert, under every school:

- **Required:** `SMELL-003`, `STRUCT-021` — universal costs of the
  Data-Oriented discipline.
- **Forbidden:** the OOP-specific rules that presuppose classes
  with behavior — `SMELL-014` (single-method classes),
  `SMELL-018` (middle-man), `SMELL-020` (large class),
  `SMELL-022` (pure-data class), `SMELL-023` (inheritance),
  `ARCH-002` (models), `DOM-001` (domain classes). If any of
  these ever fires on this exemplar, either the exemplar grew a
  class it shouldn't have, or a scope filter broke.

The `World` frozen-slots dataclass has zero methods, so the
OOP-specific rules stay silent without needing a scope decision
to filter them out. That silence is the exemplar's contribution:
the Data-Oriented shape does not land in any of the gaps those
rules are designed to catch.

---

## Comparison with the other exemplars

| Property | Classical | Pragmatic | Data-Oriented |
|---|---|---|---|
| Files | 8 across 4 layers | 1 | 3 + 1 bench |
| Public classes with behavior | 12 | 0 | 0 |
| Protocols / interfaces | 5 | 0 | 0 |
| Hot-path collections | `list[Order]` | `list[dict]` | `np.ndarray` columns |
| Money representation | `Decimal` | `Decimal` | `int64` cents |
| Dispatch in inner loop | method per stage | inline branches | `np.add.at`, vectorized ops |
| `gaudi check` SMELL-003 | 0 findings | 1 finding | 4 findings |
| `gaudi check` STRUCT-021 | 2 findings | 4 findings | 5 findings |

**The same ten acceptance tests pass against all three.** The
canonical task's invariants are enforced identically. What
differs is *where* the work lives: Classical pushes it into layered
objects; Pragmatic keeps it in one function; Data-Oriented keeps
it in one function but over SoA columns where the hot loop is
vectorizable.

The Data-Oriented exemplar is **not** a general recommendation
against OO or against single-function Pragmatic shape. It is the
faithful expression of a different axiom: when the cost of a
program is dominated by the shape of the data it touches, the
shape of the data is the architecture, and the cost of hiding
that shape behind an object model is paid in cache misses the
profiler will eventually find.

---

## Honest limitations

- **N is tiny in the acceptance suite.** The acceptance tests
  call `process_order` (a batch of one) ten times. At that
  scale, numpy's per-call overhead dominates and the SoA
  pipeline is measurably *slower* per order than the Pragmatic
  one-function baseline. The rubric's degenerate-case section
  warns explicitly about this: "Reaching for `numpy` on a problem
  with N=12 and then celebrating the speedup." The exemplar is
  not celebrating a speedup at N=10; it is demonstrating a shape
  that pays off at N=10_000, which is what [`bench.py`](bench.py)
  measures.
- **Four customers, six products is not a benchmark.** The
  acceptance seed is deliberately small so every other school can
  pass the same tests. `bench.py` synthesizes a 1000×500 world and
  10k orders separately so there is real data under the
  measurement.
- **Money is int cents, which caps amounts at ~$92 trillion per
  cell.** Every seed amount fits comfortably.

---

## See also

- [docs/philosophy/data-oriented.md](../../../../docs/philosophy/data-oriented.md) — The axiom sheet and rubric.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [tests/philosophy/pragmatic/canonical/README.md](../../pragmatic/canonical/README.md) — The single-function baseline this exemplar is most directly in dialogue with.
- [tests/philosophy/functional/canonical/README.md](../../functional/canonical/README.md) — The school the Data-Oriented axiom conflicts with most sharply (immutable records vs in-place column updates).
