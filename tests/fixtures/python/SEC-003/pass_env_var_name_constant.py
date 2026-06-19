"""Fixture for SEC-003: constants naming env vars, not carrying secrets.

Each holder has a credential-ish name (so the rule is consulted), but its
value is an environment-variable NAME (UPPER_SNAKE_CASE), or the holder is
suffixed to mark it as a name — so nothing here is a literal secret.
"""

# Holder-suffix path: the ``_env`` / ``_var`` suffix marks a var-name holder.
AUTH_TOKEN_ENV = "MYAPP_AUTH_TOKEN"
ACCESS_TOKEN_VAR = "SERVICE_ACCESS_TOKEN"

# Value-shape path: a bare UPPER_SNAKE value is an env-var name, not a secret.
auth_token = "DJANGO_AUTH_TOKEN"
