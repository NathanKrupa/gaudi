"""Fixture for FLASK-STRUCT-001: Flask app built inside a factory function."""

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "hello"

    return app
