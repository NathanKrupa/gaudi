# ABOUTME: Pass case for OPS-008 -- host and port read from environment.
# ABOUTME: The literals appear inside os.getenv defaults, not as keyword values.
import os

from flask import Flask

app = Flask(__name__)


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8080")))
