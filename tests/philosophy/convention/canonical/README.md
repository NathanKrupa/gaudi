# Convention-Over-Configuration — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/convention.md](../../../../docs/philosophy/convention.md)
**Rubric score:** 10/10

The fifth reference implementation of the canonical task, and the
first to use a real framework as the architecture. A Django app
with models, managers, admin, migrations, and the composition root
living on a manager method rather than in a separate service class.
"The framework IS the architecture" — catechism #7 in practice.

---

## Running it

```bash
conda run -n Oversteward pytest tests/philosophy/convention/ -v
```

Fourteen tests exercise the acceptance criteria against a real
Django in-memory SQLite database. The test harness bootstraps
Django via ``django.setup()``, runs migrations once per module,
and each test seeds from ``tests/philosophy/seed_data.py`` inside
a savepoint that rolls back at the end.

Two exemplar-specific tests enforce rubric compliance:

- ``test_every_model_is_registered_in_admin`` — rubric #7 as a test.
  Walks ``admin.site._registry`` and asserts every domain model is
  present. A Convention exemplar without admin is not faithful.
- ``test_reversible_migration_exists`` — rubric #4 as a test. Runs
  ``makemigrations --check --dry-run`` and fails if ``models.py``
  has drifted from the committed migration. The exemplar ships
  ``0001_initial.py`` generated from the real models.

---

## Directory shape

```
canonical/
├── README.md         # this file
├── __init__.py       # default_app_config pointer
├── apps.py           # CanonicalConfig with explicit label
├── settings.py       # minimal Django settings, in-memory SQLite
├── urls.py           # empty by design — no HTTP layer in scope
├── models.py         # 7 models + 4 managers + composition root
├── admin.py          # ModelAdmin for every domain model
└── migrations/
    ├── __init__.py
    └── 0001_initial.py   # generated with `manage.py makemigrations`
```

Eight Python files. **Recognizable as a Django app by any Django
developer at a glance** — the file names are the blessed idiom, the
models inherit from ``django.db.models.Model``, and the admin is
registered via the decorator pattern. This is rubric check #1 and
#10 in practice: the framework's conventions are load-bearing; a
newcomer who knows Django can predict what each file contains from
its name.

---

## The composition root lives on a manager

The most important architectural choice in this exemplar is where
``place_order`` lives. Under a Classical reading, it belongs in an
``OrderService`` class between the view and the model. Under
Convention, **extracting that service layer means fighting the
framework** — Django's Manager IS the service layer, and the blessed
pattern is "fat model, skinny view."

So ``place_order`` is ``Order.objects.place_order()`` — a method
on the ``OrderManager`` subclass, wrapped in ``@transaction.atomic``,
using ``InventoryLevel.objects.reserve_many()`` (another manager
method) with ``select_for_update()`` + ``F()`` expressions for
race-free inventory reservation.

```python
@transaction.atomic
def place_order(self, *, customer_id, line_items, promo_code, ...):
    customer = Customer.objects.filter(customer_id=customer_id).first()
    if customer is None: return self._reject(...)
    if not customer.may_place_orders: return self._reject(...)
    # ... resolve products, check quantities, price, reserve, confirm
```

The Classical exemplar's ``OrderPipeline`` class is the *wrong*
answer under Convention: a service layer hiding the ORM behind
``ValidationService`` + ``PricingService`` + ``ReservationService``
would lose Django's admin integration, its migration awareness, its
third-party packages that hook the manager, and its entire
ecosystem of framework-blessed tooling. The Convention exemplar
refuses that extraction.

---

## Rubric score against [convention.md](../../../../docs/philosophy/convention.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | Layout is immediately recognizable as Django | ✓ | ``apps.py``, ``settings.py``, ``models.py``, ``admin.py``, ``migrations/``, ``urls.py``. Any Django developer recognizes this tree without explanation. |
| 2 | All models inherit from the framework base class and live in models.py | ✓ | Every domain model (Customer, Product, InventoryLevel, PromoCode, Order, OrderLine, Notification) inherits from ``django.db.models.Model`` and lives in ``models.py``. No split across files. |
| 3 | All routes declared through framework routing | ✓ | ``urls.py`` exists with a typed ``urlpatterns: list[path]`` list; the exemplar's tests drive models directly, so the route surface is intentionally empty. A production deployment would mount admin here. |
| 4 | Migrations exist for every schema change and are reversible | ✓ | ``migrations/0001_initial.py`` is generated from the real models by ``manage.py makemigrations``. Django auto-generates reverse operations for every standard model operation. ``test_reversible_migration_exists`` fails loudly if models.py drifts from the migration. |
| 5 | No custom middleware replaces a framework facility | ✓ | Stock middleware list: sessions, auth, messages. No custom replacements. |
| 6 | No hand-rolled ORM/serializer/form | ✓ | Every query goes through the Django ORM via custom Manager methods. No raw SQL. No hand-rolled form handling. |
| 7 | Admin is wired where the framework provides it | ✓ | Every domain model has a ``ModelAdmin`` with ``list_display``, ``search_fields``, ``list_filter``. ``OrderAdmin`` uses an inline for order lines. ``test_every_model_is_registered_in_admin`` is the structural enforcement. |
| 8 | Deviations from convention are explicitly labeled | ✓ | Only one deviation: the empty ``urls.py``, explicitly labeled in the module docstring because "the canonical-task.md out-of-scope list excludes an HTTP layer." |
| 9 | Test suite uses the framework's own test helpers | ✓ | Django-aware pytest harness: ``django.setup()``, ``call_command("migrate")``, ``transaction.savepoint()`` for per-test rollback. No hand-rolled fixture system. |
| 10 | A first-time reader who knows the framework can predict each file's contents | ✓ | A Django developer shown only ``apps.py / settings.py / models.py / admin.py / migrations/ / urls.py`` can state what each file contains before opening it. Demonstrable. |

**10/10.**

---

## The findings — and what they reveal

Running ``gaudi check`` on this exemplar surfaces **six detector
precision issues and one working-correctly matrix result**. The
exemplar is the forcing function for a next round of Gaudí
improvements; this PR documents them as follow-up work without
patching them, so the matrix test can pin the current behavior
and future fixes can be compared against a stable baseline.

### Category A — Working correctly: SMELL-014 matrix row

Under ``school = "convention"``, ``SMELL-014 LazyElement`` does
**not** fire on the Django Manager subclasses or the single-method
models. Under ``school = "pragmatic"`` / ``functional`` / ``unix``
/ ``data-oriented``, ``SMELL-014`` **does** fire on:

- ``CustomerManager`` (one method: ``good_standing``)
- ``ProductManager`` (one method: ``by_sku``)
- ``Customer`` (one method: ``may_place_orders``)
- ``PromoCode`` (one method: ``is_active``)

**This is the same-code-different-verdict demonstration** that the
matrix was built to pin. Custom Django managers are framework seams
under Convention (the whole point of the ORM is that you subclass
Manager to add domain-named query methods); under anti-extensibility
schools they are single-method classes that the rule catches
correctly.

### Category B — Detector precision issues surfaced by this exemplar

Six findings fire where the audit says they shouldn't, but the
**audit is right** and the **detectors are imprecise**. These are
follow-up issues, not changes to this PR:

1. **DOM-001 AnemicDomainModel on Order/Product/Notification** —
   DOM-001 looks for classes with fields but no methods. The
   Convention version of "fat model" is a model whose business
   logic lives on a Manager subclass, not inlined as ``@property``
   or instance methods. DOM-001 does not know about Managers.
   Fix: DOM-001 should walk the Manager subclass of a Model and
   count its methods as business logic belonging to the model.

2. **SCHEMA-001 MissingTimestamps on every model without ``created_at``** —
   The exemplar intentionally adds timestamps only to ``Order`` (the
   mutable one). Reference data like ``Product`` and ``PromoCode``
   doesn't need audit columns. SCHEMA-001 fires on all of them.
   Fix: SCHEMA-001 should be aware of "reference vs. transactional"
   shapes — a model with only immutable fields (``CharField``,
   ``DecimalField``, ``max_length`` constraints) and no ``ForeignKey``
   dependencies is reference data.

3. **SEC-001 NoMetaPermissions on every model** — Django
   automatically creates ``add_<model>``, ``change_<model>``,
   ``delete_<model>``, ``view_<model>`` permissions for every model
   without any ``Meta.permissions`` declaration. Explicit
   ``Meta.permissions`` is only for *custom* permissions beyond the
   auto-generated four. SEC-001 is reporting a false negative of
   Django's auto-permission system.
   Fix: SEC-001 should recognize that all Django models get the
   four default permissions, and should only fire when the model
   has a security-sensitive shape (e.g., a ``UserModel`` or
   something in an app named ``authz`` / ``security``).

4. **STAB-001 UnboundedResultSet on ``.filter(...).first()``** —
   ``.first()`` is the *opposite* of unbounded — it fetches exactly
   one row. STAB-001 is pattern-matching on the ``.filter()`` call
   without looking at the terminal method.
   Fix: STAB-001 should walk the full attribute chain and skip any
   filter chain that terminates in ``.first()``, ``.get()``, or
   ``.[offset]``.

5. **DJ-SEC-001 DjangoSecretKeyExposed on test settings** — The
   exemplar's ``settings.py`` has ``SECRET_KEY = "test-secret-..."``
   with a ``# noqa`` and a clearly-labeled comment. The rule fires
   because it looks only at the literal, not at the file's purpose.
   Fix: DJ-SEC-001 should skip ``settings.py`` files under paths
   named ``test/``, ``tests/``, or ``conftest.py``, OR respect a
   ``# noqa: DJ-SEC-001`` comment, OR detect that the key is clearly
   a test placeholder (e.g., contains "test" / "example" / "dummy").

6. **SEC-003 NoDefaultManager on every model** — Our custom Manager
   subclasses define ``objects = CustomerManager()``, which replaces
   the default. Django treats the first-declared manager as the
   default, so this is correct idiom. SEC-003 doesn't recognize the
   pattern.
   Fix: SEC-003 should detect that a Manager subclass assignment
   satisfies the "default manager exists" requirement.

Every one of these is evidence for why the Convention exemplar
matters: by writing a real Django app and running Gaudí against it,
we surface precision issues the Classical, Pragmatic, Functional,
and Unix exemplars could not reach. The exemplar is a **detector
fuzzer** for the Django-aware rule family.

### Category C — Universal findings the exemplar accepts

- **SMELL-003 LongFunction** on ``place_order`` (~92 lines). Similar
  to the Pragmatic and Functional exemplars' long composition
  roots; the Convention discipline accepts it because splitting
  would introduce the anti-pattern service layer the axiom forbids.
- **STRUCT-021 MagicStrings** on common Django field names (``sku``,
  ``name``, ``order_id``, ``status``). Honest universal finding; the
  exemplar would silence them with a constants module, but
  constants modules for Django field names would hurt rather than
  help readability.
- **IDX-001 / IDX-002** for missing indexes on email/status/expires_at
  fields. Honest universal findings the exemplar does not address
  because the canonical task is small enough that indexes do not
  matter for correctness — a production deployment would add them.

---

## Comparison with the other four exemplars

| Property | Classical | Pragmatic | Functional | Unix | **Convention** |
|---|---|---|---|---|---|
| Files | 8 | 1 | 3 | 4 | **8 Django files** |
| Impl lines | ~450 | ~120 | ~220 | ~280 | **~400** |
| Public classes | 12 | 0 | 10 (records) | 0 | **7 models + 4 managers + 6 admins** |
| Where composition lives | pipeline.py | one function | one function | 4 scripts | **Manager method** |
| Framework dependency | none | none | none | none | **Django** |
| Migrations | no | no | no | no | **reversible, drift-checked** |
| Admin | no | no | no | no | **wired for every model** |
| Atomic reservation primitive | in-memory atomic | single-threaded | replace() | F() expression | **``select_for_update`` + F()** |
| Scope-sensitive findings | SMELL-014 matrix | no | no | ARCH-013 matrix | **SMELL-014 matrix** |
| Detector precision issues surfaced | 2 (SMELL-007, SMELL-023) | 0 | 1 (SMELL-008) | 0 | **6 new ones** |

The Convention exemplar has the richest forcing-function yield of
any exemplar so far — six detector precision issues in one
implementation, where the previous four yielded four total.

---

## See also

- [docs/philosophy/convention.md](../../../../docs/philosophy/convention.md) — The axiom sheet.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [docs/rule-sources.md](../../../../docs/rule-sources.md) — The rule audit.
- [tests/philosophy/classical/canonical/README.md](../../classical/canonical/README.md) — Classical (OOP tree).
- [tests/philosophy/pragmatic/canonical/README.md](../../pragmatic/canonical/README.md) — Pragmatic (one function).
- [tests/philosophy/functional/canonical/README.md](../../functional/canonical/README.md) — Functional (pure composition).
- [tests/philosophy/unix/canonical/README.md](../../unix/canonical/README.md) — Unix (four scripts).
