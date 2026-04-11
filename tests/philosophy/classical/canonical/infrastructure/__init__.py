"""
The infrastructure layer: repository interfaces (Protocols) and their
in-memory implementations. Services depend on the Protocols, not on
the concrete implementations, so a real SQLite or Postgres backend
could replace the in-memory store without touching ``services/`` or
``domain/``.
"""
