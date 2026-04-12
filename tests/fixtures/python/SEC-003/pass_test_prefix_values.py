"""Fixture for SEC-003: credential variables with test-placeholder values.

Values prefixed with "test-", "fake-", "dummy-" etc. are clearly not
real secrets and should not trigger the rule.
"""

SECRET_KEY = "test-secret-not-used-in-production"
api_key = "fake-api-key-for-unit-tests"
auth_token = "dummy-token-12345"
