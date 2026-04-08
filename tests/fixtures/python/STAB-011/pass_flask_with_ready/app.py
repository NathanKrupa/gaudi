"""Flask service with a /ready route."""

from flask import Flask

app = Flask(__name__)


@app.route("/items")
def items():
    return []


@app.route("/ready")
def ready():
    return "ok"
