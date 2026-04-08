# ABOUTME: Fail case for OPS-008 -- hardcoded host and port in a service module.
# ABOUTME: Bind values must come from configuration, not literals.
from flask import Flask

app = Flask(__name__)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
