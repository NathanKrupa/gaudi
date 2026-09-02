"""Fixture for SEC-003: a file PATH that mentions a secret is not a secret.

A constant holding a path names a tool or a location on disk; the credential
word in it is part of the filename. One estate repo renamed such a constant
purely to dodge this finding, which is the tool distorting the code rather
than the code carrying a defect.
"""

SECRET_SCAN_SCRIPT = "scripts/dev/secret_scan.py"
API_KEY_FIXTURE_PATH = "tests/data/api_key_samples.json"
PRIVATE_KEY_PATH = "/etc/ssl/private/server.pem"
