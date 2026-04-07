# Fixture for SEC-003 HardcodedCredential.
import os

# POSITIVE: hardcoded password literal
password = "hunter2"

# POSITIVE: hardcoded api_key
api_key = "sk-1234567890abcdef"

# POSITIVE: hardcoded secret
SECRET = "my-super-secret-value"

# POSITIVE: hardcoded token
auth_token = "ghp_abcdefghijklmnop"


# NEGATIVE: read from environment
db_password = os.getenv("DB_PASSWORD")

# NEGATIVE: empty string placeholder
client_secret = ""

# NEGATIVE: not a credential name
greeting = "hello world"

# NEGATIVE: obvious placeholder
api_key_example = "your-api-key-here"
