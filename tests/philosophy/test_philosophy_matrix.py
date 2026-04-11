"""Cross-school matrix test for philosophy-scope filtering.

This is Phase 2 of the multi-philosophy work: once every school's
reference exemplar exists, this matrix becomes a grid that pins the
expected finding deltas for every (school, exemplar) pair. Until
then, the grid exercises what we do have — the Classical exemplar —
across every valid school, pinning the deltas that the Phase 1
engine change (PR #160) and the scope tags (PR #161) produce.

The matrix answers three questions that the audit and the fixture
corpus cannot:

1. Does the engine actually *filter* the way the tags say it should?
   A rule tagged ``{classical, convention}`` must produce findings
   under those schools and nothing under the others.
2. Does a rule whose scope *excludes* the active school really
   disappear from ``gaudi check`` output, even when the underlying
   code would otherwise trip it?
3. Are the six SMELL-014 false positives the Classical exemplar
   surfaced in PR #158 actually gone under ``school = classical``?

The Classical exemplar lives at
``tests/philosophy/classical/canonical/``. Future reference
exemplars will live as sibling directories. When a new exemplar
lands, a new row is added to ``EXEMPLAR_EXPECTATIONS`` and the
grid grows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from gaudi.core import VALID_SCHOOLS, Finding
from gaudi.engine import Engine
from gaudi.packs.ops.pack import OpsPack
from gaudi.packs.python.pack import PythonPack

EXEMPLAR_ROOT = Path(__file__).parent


@dataclass(frozen=True)
class ExemplarExpectation:
    """Expected finding counts for one exemplar under one school."""

    exemplar: str
    school: str
    # Rule codes the engine MUST produce at least one finding for under
    # this (exemplar, school) pair. Scoped-away rules must NOT appear.
    required_rules: frozenset[str]
    forbidden_rules: frozenset[str]


# The Classical reference exemplar:
# - Under "classical" itself, scoped-away rules must not fire.
# - Under "pragmatic"/"unix"/"functional"/"data-oriented", the anti-
#   extensibility rules (SMELL-014, SMELL-015, SMELL-018) must fire
#   because the exemplar uses the Repository/Clock single-method
#   classes those schools treat as dead weight.
CLASSICAL_EXEMPLAR = "classical/canonical"

# The Pragmatic reference exemplar — the structural opposite of the
# Classical one. It is a single straight-through function with no
# classes, no protocols, and no scaffolding. Its gaudi findings are
# entirely universal rules (SMELL-003 LongFunction, SMELL-004
# LongParameterList, STRUCT-021 MagicStrings) that fire identically
# under every school. That stability is *itself* the matrix
# assertion: universal rules must not shift based on scope, and the
# Pragmatic exemplar is the clean control condition that proves it.
PRAGMATIC_EXEMPLAR = "pragmatic/canonical"

# The Functional reference exemplar — pure functions over immutable
# records, Ok/Err return values, no mutation, no raised exceptions.
# Like Pragmatic, it is scope-invariant: its gaudi findings are the
# same under every school. Unlike Pragmatic, it trips only one
# universal rule (SMELL-003 on the compositional process_order) vs.
# Pragmatic's three. The delta isolates which universal rule costs
# each discipline chooses to accept.
FUNCTIONAL_EXEMPLAR = "functional/canonical"

# The Unix reference exemplar — four independent programs composed
# via JSON-lines over stdio. Classes are refused; the script IS the
# service. Unlike Pragmatic and Functional, this exemplar is NOT
# scope-invariant: ARCH-013 FatScript (moved from universal to
# scoped-away-from-unix in the PR that introduced this exemplar)
# fires under every school except ``unix``. This is the matrix's
# second "same code, different verdict" demonstration, symmetric
# to Classical's SMELL-014 behavior but going the opposite
# direction: clean at home, dirty abroad.
UNIX_EXEMPLAR = "unix/canonical"

# The Convention reference exemplar — a real Django app. The
# composition root lives on a Manager method (OrderManager.place_order),
# every model is registered in admin, and a drift-checked migration
# exists. Under ``convention`` the scoped-to-convention rules
# (SMELL-020 LargeClass, DOM-001 AnemicDomainModel, SCHEMA-001
# MissingTimestamps, ARCH-002 GodModel, STRUCT-001 SingleFileModels)
# are permitted to fire on real Django models because the audit
# treats them as Convention-specific concerns. Under other schools,
# most of these must NOT fire — SMELL-020, ARCH-002, STRUCT-001 are
# scoped AWAY from Convention only, so they still run elsewhere.
#
# The scope-sensitive finding that pins this exemplar in the matrix
# is SMELL-014 LazyElement: under ``convention``, the single-method
# CustomerManager, ProductManager, Customer, and PromoCode classes
# are seams the framework uses; under every non-convention/classical/
# resilient/event-sourced school, those classes are "dead weight"
# the audit correctly flags.
CONVENTION_EXEMPLAR = "convention/canonical"

# The Resilience-First reference exemplar — a single-process order
# pipeline with explicit timeouts, bounded retries with exponential
# backoff, a Nygard-style three-state circuit breaker, idempotency
# keys on every state-mutating call, structured logging with
# correlation-ID propagation into worker threads, and a health check
# that tests real capability. Stdlib-only. See
# ``tests/philosophy/resilient/canonical/README.md`` for the rubric
# and findings triage.
#
# Like Pragmatic and Functional, the Resilient exemplar is
# scope-invariant across every valid school: its finding set is
# identical under ``resilient``, ``pragmatic``, ``unix``,
# ``functional``, ``classical``, ``convention``, ``data-oriented``,
# and ``event-sourced``. This is deliberate — the resilience
# machinery (timeouts, retries, breaker, idempotency) is built from
# universal building blocks that no school's axiom rejects. The
# STAB-* family that this exemplar would stress is AST-pattern
# matched against third-party HTTP/queue library calls, which this
# stdlib-only exemplar does not use, so no STAB rule fires and no
# audit revision surfaces. The exemplar's contribution to the
# matrix is a third scope-invariant control condition spanning the
# three most structurally different disciplines (Pragmatic: one
# function; Functional: pure records; Resilient: seven-file
# pipeline with concurrency primitives).
RESILIENT_EXEMPLAR = "resilient/canonical"

# The Data-Oriented reference exemplar — Struct-of-Arrays numpy
# columns on a frozen-slots World dataclass, processed in batches
# stage-by-stage by a single free function. Classes are refused
# (the World is a record holder with zero methods); virtual
# dispatch in the inner loop is refused (every stage inlines a
# concrete numpy op); Decimal in the hot path is refused (money is
# int64 cents). The exemplar's process_order entry point is a
# thin adapter that wraps a single order in a batch of one. See
# ``tests/philosophy/data_oriented/canonical/README.md`` for the
# rubric (10/10) and findings triage.
#
# Unlike the scope-invariant exemplars above, the Data-Oriented
# exemplar's finding set is NOT identical across every school: the
# ``LOG-004`` rule (print() calls in bench.py) is scoped away from
# ``unix``, producing a four-rule delta between the unix row and
# every other school's row. That delta is a pre-existing rule-
# level decision and not a Data-Oriented axiom claim, so the
# exemplar does not join SCOPE_INVARIANT_EXEMPLARS; its matrix
# rows pin required/forbidden sets directly.
DATA_ORIENTED_EXEMPLAR = "data_oriented/canonical"

# The Event-Sourced reference exemplar — orders as streams of
# past-tense frozen events, an in-process append-only event
# store, two read-side projections (current orders +
# reservations) rebuildable from the log, a pure command handler
# that enforces six invariants and emits named rejection events
# for each, and a time-travel query implemented as a replay up
# to a cutoff. See
# ``tests/philosophy/event_sourced/canonical/README.md`` for the
# rubric (10/10) and findings triage.
#
# Like Pragmatic, Functional, and Resilient, the Event-Sourced
# exemplar is fully scope-invariant: its finding set is bit-
# identical under every valid school. No OOP-specific rule fires
# because events are frozen dataclasses with zero methods, the
# aggregate is a free function, and the two holder classes
# (EventStore, CurrentOrdersProjection, InventoryReservationsProjection)
# are not single-method wrappers. No STAB-* rule fires because
# there is no third-party HTTP or queue client to pattern-match
# against. The exemplar's contribution to the matrix is a fourth
# scope-invariant control condition that exercises a discipline
# (frozen events + replay + time-travel) no other exemplar shares.
EVENT_SOURCED_EXEMPLAR = "event_sourced/canonical"

# Exemplars whose finding set is expected to be identical under
# every valid school. These are the "control conditions" for the
# matrix: universal rules must be scope-invariant, and a divergence
# on one of these exemplars means a supposedly-universal rule has
# accidentally leaked a scope decision.
SCOPE_INVARIANT_EXEMPLARS: tuple[str, ...] = (
    PRAGMATIC_EXEMPLAR,
    FUNCTIONAL_EXEMPLAR,
    RESILIENT_EXEMPLAR,
    EVENT_SOURCED_EXEMPLAR,
)

# Under every school, the Resilient exemplar must trip this set of
# universal rules. These are the honest costs of the resilience
# discipline — the long stage functions needed to make timeouts and
# retries legible, the ``world`` dict threaded through the pipeline
# stages, the module-level circuit-breaker singleton referenced from
# multiple functions, the magic strings in plain-dict wire format,
# and the process_order parameter list that grows with the
# dependencies it coordinates.
RESILIENT_REQUIRES_EVERYWHERE: frozenset[str] = frozenset(
    {
        "SMELL-003",  # long stage functions
        "SMELL-008",  # module-level NOTIFICATION_BREAKER in multiple funcs
        "STRUCT-021",  # magic strings in plain-dict wire format
        "CPLX-002",  # world threaded through 9 functions
        "CPLX-003",  # process_order parameter count
    }
)

# Under every school, the Resilient exemplar must NOT trip these
# OOP-specific or classical-layering rules. The exemplar has only
# two classes (CircuitBreaker and the FlakySwitch dataclass used by
# tests), neither of which is a single-method wrapper, a
# middle-man, a lazy element, or a pure-data holder with behavior
# elsewhere. If one of these fires, either the exemplar grew a
# class it shouldn't have, or a scope decision leaked.
RESILIENT_FORBIDS_EVERYWHERE: frozenset[str] = frozenset(
    {
        "SMELL-014",  # no single-method classes (CircuitBreaker has 3)
        "SMELL-018",  # no middle-man wrappers
        "SMELL-020",  # no large classes
        "SMELL-023",  # no inheritance besides Exception hierarchy
        "ARCH-002",  # no models
        "DOM-001",  # no domain classes
    }
)

# Under every school, the Pragmatic exemplar must trip SMELL-003
# (long function) and SMELL-004 (long parameter list). These are
# the deliberate trade-offs the Pragmatic discipline accepts as the
# honest cost of refusing premature abstraction.
PRAGMATIC_REQUIRES_EVERYWHERE: frozenset[str] = frozenset({"SMELL-003", "SMELL-004"})

# Under every school, the Pragmatic exemplar must NOT trip any of
# the anti-extensibility or OOP-specific rules, because it has no
# classes at all to trip them on. If one of these ever fires on
# the Pragmatic exemplar, something has regressed: either the
# implementation grew a class or the scope filter broke.
PRAGMATIC_FORBIDS_EVERYWHERE: frozenset[str] = frozenset(
    {
        "SMELL-014",  # no single-method classes
        "SMELL-018",  # no middle-man wrappers
        "SMELL-020",  # no large classes (no classes at all)
        "SMELL-022",  # no pure-data classes
        "SMELL-023",  # no inheritance
        "ARCH-002",  # no models
        "DOM-001",  # no domain classes
    }
)

# Under every school, the Functional exemplar must trip SMELL-003
# (long function on process_order at ~41 lines). This is the
# honest cost of composing five pipeline stages with explicit
# early-return error threading in Python. See
# tests/philosophy/functional/canonical/README.md.
FUNCTIONAL_REQUIRES_EVERYWHERE: frozenset[str] = frozenset({"SMELL-003"})

# Under every school, the Functional exemplar must NOT trip the
# OOP-specific rules (the frozen dataclasses have zero methods)
# or the anti-extensibility rules (no wrapper classes, no
# inheritance, no mutation). If any of these ever fires, either
# the exemplar grew a method it shouldn't have, or the scope
# filter broke.
FUNCTIONAL_FORBIDS_EVERYWHERE: frozenset[str] = frozenset(
    {
        "SMELL-014",  # no single-method classes (frozen records have zero methods)
        "SMELL-018",  # no middle-man wrappers
        "SMELL-020",  # no large classes
        "SMELL-022",  # classical-scoped, and records have zero methods besides
        "SMELL-023",  # no inheritance
        "SMELL-008",  # no shotgun surgery after inlining the type alias
        "SMELL-009",  # no feature envy (no methods at all)
        "ARCH-002",  # no models
        "DOM-001",  # no domain classes with behavior — frozen records excluded
    }
)

CLASSICAL_FORBIDS_UNDER_CLASSICAL: frozenset[str] = frozenset(
    {
        # These are the six audit-predicted false positives from
        # tests/philosophy/classical/canonical/README.md.
        "SMELL-014",
        # Convention-scoped rules must also not fire under classical,
        # since the rule is scoped AWAY from classical.
        "DOM-001",
        "SMELL-009",  # classical keeps this one, but verify no duplicates
    }
)

# Under classical: SMELL-009 and SMELL-023 stay scoped TO classical, so
# if they would have fired, they should. The Classical exemplar is
# written to avoid those smells, so they should not appear either.
CLASSICAL_REQUIRES_UNDER_CLASSICAL: frozenset[str] = frozenset()

# Under pragmatic: SMELL-014 MUST fire on the Repository classes. This
# is the "the same code, different verdict" demonstration the matrix
# exists to enforce.
CLASSICAL_REQUIRES_UNDER_PRAGMATIC: frozenset[str] = frozenset({"SMELL-014"})

# Under pragmatic/unix/functional/data-oriented: DOM-001, SCHEMA-001,
# FLASK-STRUCT-001 must NOT fire (they are classical+convention only).
# And the audit-validating rule SMELL-014 must fire at least once.
CLASSICAL_FORBIDS_UNDER_PRAGMATIC: frozenset[str] = frozenset(
    {
        "DOM-001",
        "SCHEMA-001",
        "FLASK-STRUCT-001",
        "SMELL-009",
        "SMELL-022",
        "SMELL-023",
    }
)

# The Unix exemplar's universal findings — these fire under every
# school. SMELL-003 on the long stage functions, STRUCT-012 because
# the test fixture scripts aren't declared as pyproject entry points
# (a real Unix-shaped project would declare them), STRUCT-021 for
# the repeated plain-dict keys ('sku', '_status', 'customer_id').
UNIX_REQUIRES_EVERYWHERE: frozenset[str] = frozenset({"SMELL-003", "STRUCT-012", "STRUCT-021"})

# Universal forbidden: the Unix exemplar has zero classes, so none
# of the OOP-specific rules may fire regardless of school.
UNIX_FORBIDS_EVERYWHERE: frozenset[str] = frozenset(
    {
        "SMELL-014",  # no classes at all
        "SMELL-018",  # no wrappers
        "SMELL-020",  # no large classes
        "SMELL-022",  # no data classes
        "SMELL-023",  # no inheritance
        "ARCH-002",  # no models
        "DOM-001",  # no domain classes
    }
)

# The Convention exemplar's universal findings — these fire under
# every school as honest universal costs of the Django idiom:
# SMELL-003 on the ~92-line place_order manager method,
# STRUCT-021 on repeated Django field-name literals like 'sku' and
# 'status'.
CONVENTION_REQUIRES_EVERYWHERE: frozenset[str] = frozenset({"SMELL-003", "STRUCT-021"})

# Under ``convention``: SMELL-014 must NOT fire on the single-method
# Django Managers and models. Under every non-convention school
# that scopes SMELL-014 IN, it MUST fire. This is the matrix row
# that pins the scope-sensitive demonstration on the Convention
# exemplar (symmetric to the Classical exemplar's SMELL-014 row,
# but with Django Managers as the seam).
CONVENTION_SMELL_014_FIRES_UNDER: frozenset[str] = frozenset(
    {"pragmatic", "functional", "unix", "data-oriented"}
)

# The Data-Oriented exemplar's universal required findings. Both
# are honest costs of the SoA batch discipline:
#
# - ``SMELL-003`` on the ~230-line ``process_orders_batch`` and the
#   ~67-line ``build_world``. Inlining the eight stages into one
#   function is a deliberate choice so the shared per-batch scratch
#   arrays (cust_idx, order_rejected, order_subtotal_cents,
#   order_discount_pct) are visible at one reading. The axiom's
#   §4 catechism #2 ("data layout precedes algorithm") says the
#   length is the right trade for the access pattern legibility.
# - ``STRUCT-021`` on repeated plain-dict keys like ``'sku'``,
#   ``'order_id'``, ``'name'``. The alternative is a dataclass per
#   entity, which would defeat the SoA layout the exemplar exists
#   to demonstrate.
DATA_ORIENTED_REQUIRES_EVERYWHERE: frozenset[str] = frozenset({"SMELL-003", "STRUCT-021"})

# The Data-Oriented exemplar's forbidden findings — the OOP-
# specific rules that presuppose classes with behavior. The
# ``World`` frozen-slots dataclass has zero methods and is not a
# domain aggregate; none of these should ever fire. A regression
# on any of them means either the exemplar grew a class it
# shouldn't have, or a scope filter broke.
DATA_ORIENTED_FORBIDS_EVERYWHERE: frozenset[str] = frozenset(
    {
        "SMELL-014",  # no single-method classes
        "SMELL-018",  # no middle-man wrappers
        "SMELL-020",  # no large classes
        "SMELL-022",  # no pure-data classes with behavior elsewhere
        "SMELL-023",  # no inheritance
        "ARCH-002",  # no models
        "DOM-001",  # no domain classes
    }
)

# The Event-Sourced exemplar's universal required findings.
# All three are honest costs of the aggregate-and-projections
# discipline:
#
# - ``SMELL-003`` on the 181-line ``place_order`` (enforces six
#   invariants inline and emits a named rejection event for each),
#   the 53-line ``process_order`` entry point, the 39-line
#   ``_outcome_from_events`` adapter, and the 33-line projection
#   ``apply`` dispatch. Splitting any of them would scatter the
#   reading of "what events does this command produce under what
#   conditions?"
# - ``SMELL-004`` on ``place_order`` (8 params) and
#   ``process_order`` (11 params). Every parameter is read by an
#   invariant check or a wiring step; bundling them would hide a
#   dependency, not simplify it.
# - ``STRUCT-021`` on plain-dict keys in the outcome shape
#   (``'order_id'``, ``'status'``, ``'final_price'``, ...). The
#   acceptance outcome is a dict shared across every exemplar;
#   a dataclass would diverge from the contract.
EVENT_SOURCED_REQUIRES_EVERYWHERE: frozenset[str] = frozenset(
    {"SMELL-003", "SMELL-004", "STRUCT-021"}
)

# The Event-Sourced exemplar's forbidden findings — the OOP-
# specific rules that presuppose classes with behavior. Every
# event type is a frozen-slots dataclass with zero methods, the
# aggregate is a free function, and the store/projections are
# small holder classes that no detector pattern-matches as
# single-method wrappers, large classes, middle-men, or anemic
# domain objects. A regression on any of these means either the
# exemplar grew a class it shouldn't have or a scope filter broke.
EVENT_SOURCED_FORBIDS_EVERYWHERE: frozenset[str] = frozenset(
    {
        "SMELL-014",  # no single-method classes
        "SMELL-018",  # no middle-man wrappers
        "SMELL-020",  # no large classes
        "SMELL-022",  # no pure-data classes with behavior elsewhere
        "SMELL-023",  # no inheritance
        "ARCH-002",  # no models
        "DOM-001",  # no domain classes
    }
)


EXEMPLAR_EXPECTATIONS: list[ExemplarExpectation] = [
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="classical",
        required_rules=CLASSICAL_REQUIRES_UNDER_CLASSICAL,
        forbidden_rules=frozenset({"SMELL-014"}),
    ),
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="pragmatic",
        required_rules=CLASSICAL_REQUIRES_UNDER_PRAGMATIC,
        forbidden_rules=CLASSICAL_FORBIDS_UNDER_PRAGMATIC,
    ),
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="unix",
        required_rules=frozenset({"SMELL-014"}),
        forbidden_rules=frozenset({"LOG-005", "DOM-001", "SMELL-009"}),
    ),
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="functional",
        required_rules=frozenset({"SMELL-014"}),
        forbidden_rules=frozenset({"SMELL-009", "SMELL-022", "SMELL-023", "DOM-001"}),
    ),
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="data-oriented",
        required_rules=frozenset({"SMELL-014"}),
        forbidden_rules=frozenset({"SMELL-013", "LOG-005", "SMELL-009", "SMELL-022", "DOM-001"}),
    ),
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="convention",
        required_rules=frozenset(),
        # Convention accepts SMELL-020, ARCH-002, STRUCT-001, SCHEMA-001
        # and still rejects the anti-extensibility SMELL-014.
        forbidden_rules=frozenset({"SMELL-014"}),
    ),
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="resilient",
        required_rules=frozenset(),
        forbidden_rules=frozenset({"SMELL-014", "SMELL-015"}),
    ),
    ExemplarExpectation(
        exemplar=CLASSICAL_EXEMPLAR,
        school="event-sourced",
        required_rules=frozenset(),
        forbidden_rules=frozenset({"SMELL-014", "SMELL-015", "SMELL-022", "DOM-001", "SMELL-018"}),
    ),
    # --- Pragmatic exemplar rows ---------------------------------------
    # Eight rows, one per school. Every row asserts the same universal
    # findings fire and the same OOP-specific findings stay silent.
    # The stability across schools is the control-condition assertion.
    *[
        ExemplarExpectation(
            exemplar=PRAGMATIC_EXEMPLAR,
            school=school,
            required_rules=PRAGMATIC_REQUIRES_EVERYWHERE,
            forbidden_rules=PRAGMATIC_FORBIDS_EVERYWHERE,
        )
        for school in sorted(
            {
                "classical",
                "pragmatic",
                "functional",
                "unix",
                "resilient",
                "data-oriented",
                "convention",
                "event-sourced",
            }
        )
    ],
    # --- Functional exemplar rows --------------------------------------
    # Eight rows, one per school. The Functional exemplar is also
    # scope-invariant: under every school it trips only SMELL-003 on
    # the compositional process_order. Unlike Pragmatic, it reaches
    # this with a very different shape — frozen dataclasses, Ok/Err
    # result threading, and free-function helpers. The matrix pins
    # both disciplines independently so neither can regress into
    # the other's finding profile.
    *[
        ExemplarExpectation(
            exemplar=FUNCTIONAL_EXEMPLAR,
            school=school,
            required_rules=FUNCTIONAL_REQUIRES_EVERYWHERE,
            forbidden_rules=FUNCTIONAL_FORBIDS_EVERYWHERE,
        )
        for school in sorted(
            {
                "classical",
                "pragmatic",
                "functional",
                "unix",
                "resilient",
                "data-oriented",
                "convention",
                "event-sourced",
            }
        )
    ],
    # --- Convention exemplar rows --------------------------------------
    # Under ``convention`` (the home school): DOM-001, SCHEMA-001,
    # SMELL-020, ARCH-002, STRUCT-001 are permitted to fire (they are
    # scoped to, or away from, convention per the audit, and the real
    # Django models trigger some of them). SMELL-014 must NOT fire —
    # Django Managers are seams under Convention.
    ExemplarExpectation(
        exemplar=CONVENTION_EXEMPLAR,
        school="convention",
        required_rules=CONVENTION_REQUIRES_EVERYWHERE,
        forbidden_rules=frozenset({"SMELL-014"}),
    ),
    # Under ``classical``: DOM-001 and SCHEMA-001 stay scoped IN
    # (classical+convention), so they fire. SMELL-014 stays scoped
    # AWAY from classical, so it does NOT fire.
    ExemplarExpectation(
        exemplar=CONVENTION_EXEMPLAR,
        school="classical",
        required_rules=CONVENTION_REQUIRES_EVERYWHERE,
        forbidden_rules=frozenset({"SMELL-014"}),
    ),
    # Under schools that scope SMELL-014 IN (pragmatic / functional /
    # unix / data-oriented), SMELL-014 MUST fire on the Django Manager
    # subclasses and single-method models. Meanwhile DOM-001 /
    # SCHEMA-001 / SMELL-020 / SMELL-022 / SMELL-023 / SMELL-009 /
    # ARCH-002 must all stay silent because they are scoped AWAY from
    # those schools.
    *[
        ExemplarExpectation(
            exemplar=CONVENTION_EXEMPLAR,
            school=school,
            required_rules=CONVENTION_REQUIRES_EVERYWHERE | frozenset({"SMELL-014"}),
            forbidden_rules=frozenset(
                {
                    "DOM-001",
                    "SCHEMA-001",
                    "SMELL-020",
                    "ARCH-002",
                    "STRUCT-001",
                    "SMELL-022",
                    "SMELL-023",
                    "SMELL-009",
                }
            ),
        )
        for school in sorted(CONVENTION_SMELL_014_FIRES_UNDER)
    ],
    # Under resilient and event-sourced: SMELL-014 is scoped AWAY, so
    # it does not fire. DOM-001 and SCHEMA-001 are also scoped away
    # from these schools, so they do not fire.
    *[
        ExemplarExpectation(
            exemplar=CONVENTION_EXEMPLAR,
            school=school,
            required_rules=CONVENTION_REQUIRES_EVERYWHERE,
            forbidden_rules=frozenset(
                {
                    "SMELL-014",
                    "DOM-001",
                    "SCHEMA-001",
                    "SMELL-020",
                    "SMELL-022",
                    "SMELL-023",
                }
            ),
        )
        for school in ("resilient", "event-sourced")
    ],
    # --- Resilient exemplar rows ---------------------------------------
    # Eight rows, one per school. The Resilient exemplar is fully
    # scope-invariant (like Pragmatic and Functional): its finding
    # set does not shift when the school changes. Every row asserts
    # the same universal findings fire and the same OOP/layered
    # findings stay silent. The scope-invariance itself is the
    # matrix assertion for this exemplar — any divergence means a
    # supposedly-universal rule accidentally leaked a scope
    # decision, or a STAB-* rule started pattern-matching against
    # the stdlib-only resilience primitives the exemplar uses.
    *[
        ExemplarExpectation(
            exemplar=RESILIENT_EXEMPLAR,
            school=school,
            required_rules=RESILIENT_REQUIRES_EVERYWHERE,
            forbidden_rules=RESILIENT_FORBIDS_EVERYWHERE,
        )
        for school in sorted(
            {
                "classical",
                "pragmatic",
                "functional",
                "unix",
                "resilient",
                "data-oriented",
                "convention",
                "event-sourced",
            }
        )
    ],
    # --- Data-Oriented exemplar rows -----------------------------------
    # Eight rows, one per school. The Data-Oriented exemplar's
    # required/forbidden sets are stable across every school: the
    # universal ``SMELL-003`` (long stage-inlined function) and
    # ``STRUCT-021`` (plain-dict keys) fire everywhere, and the
    # OOP-specific rules stay silent everywhere because the
    # ``World`` record holder has zero methods. The one pre-
    # existing scope delta (``LOG-004`` scoped away from ``unix``)
    # is not pinned here because it is a rule-level decision about
    # ``print()`` in scripts, not a Data-Oriented axiom claim — it
    # would fire on any exemplar with print() calls regardless of
    # discipline.
    *[
        ExemplarExpectation(
            exemplar=DATA_ORIENTED_EXEMPLAR,
            school=school,
            required_rules=DATA_ORIENTED_REQUIRES_EVERYWHERE,
            forbidden_rules=DATA_ORIENTED_FORBIDS_EVERYWHERE,
        )
        for school in sorted(
            {
                "classical",
                "pragmatic",
                "functional",
                "unix",
                "resilient",
                "data-oriented",
                "convention",
                "event-sourced",
            }
        )
    ],
    # --- Event-Sourced exemplar rows -----------------------------------
    # Eight rows, one per school. The Event-Sourced exemplar is
    # fully scope-invariant — its finding set is bit-identical
    # across every school, same as Pragmatic, Functional, and
    # Resilient. Every row asserts the same universal findings
    # fire (SMELL-003, SMELL-004, STRUCT-021) and the same OOP-
    # specific rules stay silent (SMELL-014/018/020/022/023,
    # ARCH-002, DOM-001) because events are frozen dataclasses
    # with zero methods and the aggregate is a free function.
    # The scope-invariance is pinned structurally by
    # test_scope_invariant_exemplar_is_stable_across_schools via
    # the exemplar's inclusion in SCOPE_INVARIANT_EXEMPLARS.
    *[
        ExemplarExpectation(
            exemplar=EVENT_SOURCED_EXEMPLAR,
            school=school,
            required_rules=EVENT_SOURCED_REQUIRES_EVERYWHERE,
            forbidden_rules=EVENT_SOURCED_FORBIDS_EVERYWHERE,
        )
        for school in sorted(
            {
                "classical",
                "pragmatic",
                "functional",
                "unix",
                "resilient",
                "data-oriented",
                "convention",
                "event-sourced",
            }
        )
    ],
    # --- Unix exemplar rows --------------------------------------------
    # Under the Unix home school: ARCH-013 must NOT fire (scoped away).
    # The universal findings (SMELL-003, STRUCT-012, STRUCT-021) fire.
    ExemplarExpectation(
        exemplar=UNIX_EXEMPLAR,
        school="unix",
        required_rules=UNIX_REQUIRES_EVERYWHERE,
        forbidden_rules=UNIX_FORBIDS_EVERYWHERE | frozenset({"ARCH-013"}),
    ),
    # Under every NON-unix school: ARCH-013 fires on main() functions
    # that Unix treats as "the script IS the service." This is the
    # "same code, different verdict" demonstration symmetric to
    # the Classical exemplar's SMELL-014 behavior.
    *[
        ExemplarExpectation(
            exemplar=UNIX_EXEMPLAR,
            school=school,
            required_rules=UNIX_REQUIRES_EVERYWHERE | frozenset({"ARCH-013"}),
            forbidden_rules=UNIX_FORBIDS_EVERYWHERE,
        )
        for school in sorted(
            {
                "classical",
                "pragmatic",
                "functional",
                "resilient",
                "data-oriented",
                "convention",
                "event-sourced",
            }
        )
    ],
]


def _run_exemplar(exemplar: str, school: str) -> list[Finding]:
    """Run the engine against one exemplar under one school.

    Writes a ``gaudi.toml`` in the exemplar directory temporarily
    would be invasive; instead we patch the school via the pack's
    ``check(path, school=...)`` override.
    """
    engine = Engine()
    engine.register_pack(PythonPack())
    engine.register_pack(OpsPack())
    exemplar_path = EXEMPLAR_ROOT / exemplar
    # The engine's check() method drives packs, but our packs accept
    # a school override via their own check() signature. Bypass the
    # engine-level loop and call the Python pack directly with the
    # school override so we do not mutate the on-disk gaudi.toml.
    python_pack = engine.packs["python"]
    return python_pack.check(exemplar_path, school=school)


class TestPhilosophyMatrix:
    @pytest.mark.parametrize(
        "expectation",
        EXEMPLAR_EXPECTATIONS,
        ids=lambda e: f"{e.exemplar}@{e.school}",
    )
    def test_exemplar_under_school(self, expectation: ExemplarExpectation) -> None:
        findings = _run_exemplar(expectation.exemplar, expectation.school)
        codes = {f.code for f in findings}

        missing = expectation.required_rules - codes
        assert not missing, (
            f"{expectation.exemplar} @ {expectation.school}: required rule(s) "
            f"{sorted(missing)} did not fire. Findings observed: {sorted(codes)}"
        )

        present_forbidden = expectation.forbidden_rules & codes
        assert not present_forbidden, (
            f"{expectation.exemplar} @ {expectation.school}: forbidden rule(s) "
            f"{sorted(present_forbidden)} fired when the scope should have "
            f"excluded them. Findings observed: {sorted(codes)}"
        )

    def test_every_school_in_matrix_is_valid(self) -> None:
        """Guardrail: the matrix cannot reference unknown schools."""
        referenced = {e.school for e in EXEMPLAR_EXPECTATIONS}
        unknown = referenced - VALID_SCHOOLS
        assert not unknown, f"Matrix references unknown school(s): {sorted(unknown)}"

    def test_classical_exemplar_covered_by_every_school(self) -> None:
        """The classical exemplar should be run under every valid school.

        This catches the drift where a new school is added to
        ``VALID_SCHOOLS`` but the matrix forgets to exercise it.
        """
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == CLASSICAL_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Classical exemplar matrix is missing schools: {sorted(missing)}"

    def test_pragmatic_exemplar_covered_by_every_school(self) -> None:
        """The pragmatic exemplar should also run under every school.

        Same drift-catcher as the classical version. Every new
        reference exemplar earns its own coverage check so the
        matrix never silently shrinks.
        """
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == PRAGMATIC_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Pragmatic exemplar matrix is missing schools: {sorted(missing)}"

    def test_functional_exemplar_covered_by_every_school(self) -> None:
        """The functional exemplar should also run under every school."""
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == FUNCTIONAL_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Functional exemplar matrix is missing schools: {sorted(missing)}"

    def test_unix_exemplar_covered_by_every_school(self) -> None:
        """The unix exemplar should also run under every school."""
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == UNIX_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Unix exemplar matrix is missing schools: {sorted(missing)}"

    def test_convention_exemplar_covered_by_every_school(self) -> None:
        """The convention exemplar should also run under every school."""
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == CONVENTION_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Convention exemplar matrix is missing schools: {sorted(missing)}"

    def test_resilient_exemplar_covered_by_every_school(self) -> None:
        """The resilient exemplar should also run under every school."""
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == RESILIENT_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Resilient exemplar matrix is missing schools: {sorted(missing)}"

    def test_data_oriented_exemplar_covered_by_every_school(self) -> None:
        """The data-oriented exemplar should also run under every school."""
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == DATA_ORIENTED_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Data-oriented exemplar matrix is missing schools: {sorted(missing)}"

    def test_event_sourced_exemplar_covered_by_every_school(self) -> None:
        """The event-sourced exemplar should also run under every school."""
        covered = {e.school for e in EXEMPLAR_EXPECTATIONS if e.exemplar == EVENT_SOURCED_EXEMPLAR}
        missing = VALID_SCHOOLS - covered
        assert not missing, f"Event-sourced exemplar matrix is missing schools: {sorted(missing)}"

    def test_convention_managers_trip_smell_014_outside_convention(self) -> None:
        """The Convention-flavored same-code-different-verdict pin.

        Under schools that reject anti-extensibility seams
        (pragmatic/functional/unix/data-oriented), Django Manager
        subclasses with one method are SMELL-014 targets. Under
        ``convention`` itself, they are framework seams and the rule
        must stay silent. This test exercises both directions with
        the exact same source files.
        """
        findings_pragmatic = _run_exemplar(CONVENTION_EXEMPLAR, "pragmatic")
        smell_014 = [f for f in findings_pragmatic if f.code == "SMELL-014"]
        assert smell_014, (
            "SMELL-014 did not fire on the Convention exemplar under "
            "school='pragmatic'. The single-method Manager subclasses "
            "(CustomerManager, ProductManager) and single-method models "
            "should have tripped the LazyElement rule."
        )

        findings_convention = _run_exemplar(CONVENTION_EXEMPLAR, "convention")
        smell_014_conv = [f for f in findings_convention if f.code == "SMELL-014"]
        assert not smell_014_conv, (
            "SMELL-014 fired on the Convention exemplar under "
            "school='convention'. Django Managers are seams under "
            "Convention, not dead weight — the audit tags SMELL-014 "
            "as scoped away from convention for this reason. "
            "Findings: " + "; ".join(f"{f.file}:{f.line}" for f in smell_014_conv)
        )

    def test_unix_exemplar_arch013_absent_under_unix(self) -> None:
        """The load-bearing regression test for the Unix exemplar.

        ``ARCH-013 FatScript`` was moved from universal to
        scoped-away-from-unix because the Unix stages tripped it on
        ``main()`` functions that are pure argparse + stdin loop +
        atomic write plumbing. Under Unix catechism #1, the script
        IS the service — there is no "service elsewhere" to extract
        to. This test pins that audit revision: under
        school='unix', ``ARCH-013`` must not fire on the Unix
        exemplar's ~80 lines of stage scripts.
        """
        findings = _run_exemplar(UNIX_EXEMPLAR, "unix")
        arch_013 = [f for f in findings if f.code == "ARCH-013"]
        assert not arch_013, (
            "ARCH-013 fired on the Unix exemplar under school='unix'. "
            "This is the regression the audit revision was supposed "
            "to prevent. Findings: " + "; ".join(f"{f.file}:{f.line}" for f in arch_013)
        )

    def test_unix_exemplar_arch013_present_under_classical(self) -> None:
        """The symmetric demonstration for the ARCH-013 scope.

        The same four stage files that pass cleanly under Unix must
        trip ARCH-013 under Classical, because Classical architecture
        considers a 17-line main() with business logic in it a
        candidate for extraction. This is "same code, different
        verdict" going the opposite direction from the Classical
        exemplar's SMELL-014 behavior: Unix is clean at home, dirty
        abroad; Classical is clean at home, dirty abroad. Two
        independent forcing-function demonstrations that the scope
        system filters per-school rather than globally silencing.
        """
        findings = _run_exemplar(UNIX_EXEMPLAR, "classical")
        arch_013 = [f for f in findings if f.code == "ARCH-013"]
        assert arch_013, (
            "ARCH-013 did not fire on the Unix exemplar under "
            "school='classical'. The main() functions in the four "
            "stage scripts should have tripped the FatScript rule, "
            "proving that philosophy scoping filters rather than "
            "globally silencing."
        )

    @pytest.mark.parametrize("exemplar", SCOPE_INVARIANT_EXEMPLARS)
    def test_scope_invariant_exemplar_is_stable_across_schools(self, exemplar: str) -> None:
        """Universal rules must not shift based on the active school.

        Each scope-invariant exemplar (Pragmatic's class-free
        function, Functional's pure-record composition) trips only
        universal rules. Running it under every valid school must
        produce an identical set of rule codes. If the set diverges
        between any two schools, a rule is accidentally leaking a
        scope decision into a rule the audit classified as universal.

        This is the control-condition half of the matrix's claim.
        The Classical exemplar asserts that **scoped** rules shift
        with the active school ('same code, different verdict').
        These exemplars assert the symmetric property: **universal**
        rules do *not* shift.
        """
        observed: dict[str, frozenset[str]] = {}
        for school in VALID_SCHOOLS:
            findings = _run_exemplar(exemplar, school)
            observed[school] = frozenset(f.code for f in findings)

        baseline_school = next(iter(VALID_SCHOOLS))
        baseline = observed[baseline_school]
        for school, codes in observed.items():
            assert codes == baseline, (
                f"{exemplar} finding set shifted: under {school!r} "
                f"got {sorted(codes)}, but under {baseline_school!r} got "
                f"{sorted(baseline)}. Universal rules must be scope-invariant; "
                f"a shift indicates an accidentally-scoped rule."
            )

    def test_classical_exemplar_false_positives_resolved_under_classical(self) -> None:
        """The load-bearing regression test for the Phase 1 engine change.

        tests/philosophy/classical/canonical/README.md documented six
        SMELL-014 findings that the audit predicted would be false
        positives on a faithful Classical exemplar. This test pins
        the result: under school = "classical", SMELL-014 must not
        fire on that exemplar.
        """
        findings = _run_exemplar(CLASSICAL_EXEMPLAR, "classical")
        smell_014 = [f for f in findings if f.code == "SMELL-014"]
        assert not smell_014, (
            "SMELL-014 fired on the Classical exemplar under school='classical'. "
            "This is the Phase 1 regression that the audit predicted should "
            "disappear. Findings: " + "; ".join(f"{f.file}:{f.line}" for f in smell_014)
        )

    def test_classical_exemplar_under_pragmatic_does_fire_smell_014(self) -> None:
        """The symmetric demonstration: SMELL-014 must still fire under
        schools that scope it IN, even on the same source files.

        This is the 'same code, different verdict' proof that the
        scope system is doing something real — not just globally
        silencing a rule.
        """
        findings = _run_exemplar(CLASSICAL_EXEMPLAR, "pragmatic")
        smell_014 = [f for f in findings if f.code == "SMELL-014"]
        assert smell_014, (
            "SMELL-014 did not fire on the Classical exemplar under "
            "school='pragmatic'. The Repository and Clock wrapper classes "
            "should have tripped the LazyElement rule, proving that "
            "philosophy scoping filters rather than globally silencing."
        )
