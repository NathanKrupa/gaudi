# ABOUTME: Pass case for OPS-008 -- test files are exempt.
# ABOUTME: Hardcoded host/port inside the tests/ tree is allowed.
from flask import Flask

app = Flask(__name__)
app.run(host="127.0.0.1", port=5555)
