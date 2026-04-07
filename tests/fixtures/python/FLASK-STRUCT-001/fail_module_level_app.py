"""Fixture for FLASK-STRUCT-001: Flask app constructed at module level."""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "hello"
