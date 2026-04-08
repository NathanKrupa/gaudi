# ABOUTME: Pass case for OPS-008 -- config modules are exempt.
# ABOUTME: Hardcoded host/port in a file named config.py is allowed.
from flask import Flask

app = Flask(__name__)
app.run(host="0.0.0.0", port=8080)
