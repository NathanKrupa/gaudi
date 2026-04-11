"""
Classical / Structural reference implementation of the canonical task.

Package layout follows the three-layer convention:

- ``domain/``         — pure value objects and invariants (inner layer)
- ``infrastructure/`` — repository interfaces + in-memory implementations
- ``services/``       — orchestrated business operations (middle layer)
- ``pipeline.py``     — composition root (outer layer)

Every arrow in the import graph points inward. The domain package has
zero imports from infrastructure or services. Services receive their
collaborators via constructor injection; they do not fetch them from
the environment. See ``README.md`` in this directory for the full
rubric score against ``docs/philosophy/classical.md``.
"""
