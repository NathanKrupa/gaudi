# The Canonical Task: Order Processing Pipeline

> *One problem, eight implementations. The contrast is the teaching.*

---

## Purpose

To demonstrate — in working, reviewable code — what each of the eight
architectural schools looks like when applied faithfully to the same
meaty domain problem. The implementations are scored against the
rubrics in their respective axiom sheets, so a reviewer can judge
faithfulness without having a vibes-based argument.

The canonical task also serves as the fixture corpus for
`test_philosophy_matrix.py` (forthcoming): each implementation is a
reference example its school's philosophy-scoped rules must accept,
and cross-school runs demonstrate where school-scoped rules should
fire and where they should not.

This task is deliberately domain-realistic rather than toy-sized.
A rate limiter or a URL shortener cannot honestly showcase Convention
(Django on a three-line problem is parody) or Event-Sourced (no
intent to preserve on a read-only lookup). Order processing has the
structural surface area to show every school at full stretch.

---

## The Problem

An e-commerce system receives orders from customers and must process
each order through four stages before it is confirmed:

1. **Validation** — is the order structurally well-formed? Do the
   referenced products and the customer exist? Is the quantity within
   allowed limits? Is the customer in good standing?
2. **Pricing** — what is the final price for this order? This includes
   unit prices, quantity discounts, promotional codes, tax, and
   shipping.
3. **Inventory reservation** — are enough units in stock for every line
   item? If yes, reserve them so a parallel order cannot grab them. If
   no, the order is rejected with the specific unfillable line items.
4. **Notification** — tell the customer the outcome (confirmed or
   rejected) and, for confirmed orders, queue the downstream
   fulfillment work.

Each stage can succeed or fail. A failure at any stage halts the
pipeline for that order and produces an explanation. A success at
every stage produces a confirmed order with a finalized price, a
reservation receipt, and a notification record.

---

## Why This Problem

Order processing touches every architectural concern the eight schools
care about:

| Concern | Which schools get to show off |
|---|---|
| **Layering and boundaries** | Classical (domain kernel, layered services) |
| **YAGNI and small commits** | Pragmatic (straight-through function, refactored only under pressure) |
| **Pure transformations** | Functional (pipeline of pure functions, I/O at edges) |
| **Small composable programs** | Unix (one stage per script, piped via JSON-lines) |
| **Failure modes** | Resilience-First (timeouts, retries, circuit breakers, idempotency) |
| **Batch processing** | Data-Oriented (hot/cold data separation, SoA layout, measured speedup) |
| **Framework idioms** | Convention (Django models, admin, generic views, migrations) |
| **Intent preservation** | Event-Sourced (OrderPlaced, PricingCalculated, OrderCancelledByCustomer) |

Every school has a genuine architectural claim on this problem. None
is out of its element, and none has an unfair advantage. The contrast
between implementations is therefore a contrast between philosophies,
not between the task and the school.

---

## The Shared Domain

All eight implementations operate on the same conceptual domain,
expressed here in language-agnostic form. Each school may represent
these concepts differently in code (a Django model, a frozen dataclass,
a parallel numpy array, an event stream, a dict) — the point of the
exercise is that the *same domain concepts* receive different
architectural treatment.

### Entities

- **Customer** — identified by `customer_id`. Has a `name`, an
  `email`, a `standing` (one of `good`, `hold`, `banned`), and a
  `credit_limit` (monetary).
- **Product** — identified by `sku`. Has a `name`, a `unit_price`
  (monetary), a `max_per_order` (integer), and a `category` (free
  string).
- **Inventory level** — for each `sku`, the current `on_hand` quantity
  (non-negative integer) and a `reserved` quantity (non-negative,
  `reserved <= on_hand`).
- **PromoCode** — identified by `code`. Has a `percent_off`
  (0–100) and an `expires_at` timestamp.
- **Order** — a customer-originated request. Before processing: a
  `customer_id`, a list of `(sku, quantity)` line items, an optional
  `promo_code`, a `shipping_address`, and an `order_id`. After
  processing: all of the above plus a `status` (one of `confirmed`,
  `rejected`, plus the reason), a `final_price`, and a
  `reservation_id` (if confirmed).

### Invariants

Every faithful implementation must enforce these invariants, whatever
its layering or storage model:

1. A customer with `standing` ∉ `{good}` cannot place an order.
2. A line item's `quantity` must satisfy
   `0 < quantity <= product.max_per_order`.
3. An order's `final_price` after promo and shipping must not exceed
   `customer.credit_limit`.
4. Inventory must not go negative: you cannot confirm an order whose
   line items exceed the available (`on_hand - reserved`) quantity
   for any `sku`.
5. Reservation must be atomic *per order*: either all line items are
   reserved, or none are.
6. A confirmed order's `final_price` is the sum of
   `(unit_price * quantity)` across line items, reduced by
   `promo_code.percent_off` if applicable and not expired, plus a
   flat `shipping_fee`.
7. A rejected order names the specific reason: which invariant
   failed, and for which line item (if applicable).

---

## Acceptance Criteria

Every implementation must satisfy all of the following:

### Functional correctness

- [ ] Accepts a well-formed order and produces a confirmed outcome
      with final price and reservation receipt.
- [ ] Rejects a customer on hold with a specific reason.
- [ ] Rejects an order with an over-quantity line item, naming the
      offending line.
- [ ] Rejects an order whose final price exceeds the customer's
      credit limit.
- [ ] Rejects an order with an out-of-stock line item, naming every
      insufficient line item (not just the first).
- [ ] Applies a valid promo code and reflects the discount in the
      final price.
- [ ] Refuses an expired promo code without failing the whole order
      (the order proceeds at list price; the promo is simply ignored).

### Testing

- [ ] Every stage (validation, pricing, reservation, notification)
      has at least one passing and one failing test case.
- [ ] At least one end-to-end test runs a real order through all
      four stages.
- [ ] Tests run with `pytest` and complete in under ten seconds on
      a modest machine.
- [ ] The test suite exercises every invariant listed above.

### Reproducibility

- [ ] The implementation lives in
      `tests/fixtures/philosophy/<school>/canonical/` with a clear
      `README.md` explaining how to run it.
- [ ] Any external dependencies (a single framework library like
      Django is acceptable for Convention; numpy is acceptable for
      Data-Oriented) are listed in the README and pinned to a
      version.
- [ ] No network access is required to run the tests. All external
      systems (database, notification sender) are simulated in-process
      or via temporary SQLite files.

### Rubric conformance

- [ ] The implementation scores 10/10 on its school's rubric in the
      corresponding axiom sheet. A 9/10 is a draft. A score below 9
      is a signal that the implementation should be rewritten, not
      patched.

---

## What Is Out of Scope

Deliberately *not* required, so the implementations stay comparable
and readable:

- **Persistence beyond in-memory or SQLite.** No Postgres, no Redis,
  no Kafka. Convention may use Django's default SQLite for
  authenticity; Event-Sourced may use an in-process append-only list
  as its event log. Real infrastructure is an orthogonal concern.
- **Authentication and authorization.** A customer is a row; a
  request is a function call. No login, no tokens, no user sessions.
- **HTTP layer.** No Flask, FastAPI, or Django views (except in the
  Convention implementation, where the framework is the point).
- **Real payment processing.** Credit limits are checked; payments
  are not taken.
- **Concurrency beyond what the school demands.** Only the
  Resilience-First and Data-Oriented implementations need to address
  parallel orders explicitly; the others may assume single-threaded
  execution for clarity.
- **Production deployment.** No Dockerfiles, Helm charts, or CI
  pipelines per implementation. These are project-level concerns
  measured by other Gaudí rules.

---

## The Shared Test Data

Every implementation runs against the same seed data, so differences
in output are attributable to differences in architecture rather than
to differences in test setup. The seed data lives at
`tests/fixtures/philosophy/seed-data.json` and includes:

- 4 customers: one `good` with a high credit limit, one `good` with
  a limit that is exactly tight, one on `hold`, one `banned`.
- 6 products across 2 categories, with varied `unit_price` and
  `max_per_order` values.
- Inventory levels: two products fully in stock, two products with
  low stock, two products out of stock.
- 2 promo codes: one valid, one expired.
- 10 seed orders covering every acceptance criterion case above.

The seed data file will be written during Phase 0d alongside the
first reference implementation (Classical), and every subsequent
implementation is required to use it unchanged. If a school's
implementation needs additional test cases beyond the shared seed
(e.g., Resilience-First may want cases that simulate dependency
failure; Data-Oriented may want cases that exercise batch sizes),
it adds them in a sibling file rather than modifying the shared seed.

---

## How to Score an Implementation

1. **Read the axiom sheet** for the school whose implementation is
   under review.
2. **Walk the ten-item rubric** at the bottom of the axiom sheet.
   Check each box honestly.
3. **Ten out of ten** is a faithful exemplar. Nine or below means
   the implementation needs revision before it can serve as a
   reference.
4. **Cross-read.** Run one school's implementation against another
   school's rubric — for example, score the Classical implementation
   against the Pragmatic rubric. The Classical implementation should
   fail several Pragmatic checks (it has abstractions a Pragmatic
   exemplar would not yet have), and that failure is what *correctly*
   demonstrates the philosophical difference.
5. **Commit the score.** When a reference implementation lands, its
   rubric score is recorded in its README alongside the reviewer's
   name and date. A score can be revisited if a later reader spots
   a check that was scored too generously.

---

## Implementation Order

The eight implementations will land in separate PRs, in this order:

1. **Classical** — the default for Gaudí's existing doctrine and the
   school closest to `principles.md`. Doing it first anchors the
   format and the shared domain.
2. **Pragmatic** — the sharpest contrast with Classical on the same
   problem; writing it second makes the key philosophical difference
   visible early.
3. **Functional** — pure-transformation treatment of the same
   domain; reveals the Functional exemplar's sharpest disagreements
   with both Classical (inheritance) and Data-Oriented (mutation).
4. **Convention** — Django implementation; demonstrates where the
   Convention school's axioms actively contradict Classical layering.
5. **Resilience-First** — same core logic as Classical, but every
   external boundary is wrapped with timeout, retry, circuit-breaker,
   and idempotency concerns. The delta from Classical is the teaching.
6. **Unix** — decomposition into small scripts communicating via
   JSON-lines on stdio. The most radical shape departure.
7. **Data-Oriented** — batch processing, SoA layout, measured
   speedup on a thousand-order benchmark. Radically different data
   structures, same domain invariants.
8. **Event-Sourced** — orders as streams of past-tense events, with
   projections rebuilt from the log. The most radical data-model
   departure.

Each implementation may draw freely on earlier ones for comparison
and contrast; later implementations are explicitly allowed (and
encouraged) to reference earlier ones in their README to highlight
the philosophical delta.

---

## See also

- [docs/philosophy/README.md](README.md) — The index of eight axiom
  sheets.
- [docs/philosophy/classical.md](classical.md) — The first axiom
  sheet and the home of the first reference implementation.
- [docs/principles.md](../principles.md) — The universal core these
  implementations collectively illustrate.
- [docs/testing-fixtures.md](../testing-fixtures.md) — The
  fixture-first TDD rubric that the reference implementations extend
  to the philosophy layer.
