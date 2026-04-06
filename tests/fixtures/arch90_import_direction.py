"""Fixture: Import direction violation — inner layer imports outer."""

# Simulates a connector/store file importing from a CLI/script module
from scripts.deploy import run_deployment
from cli.commands import handle_command

# Clean import — inner importing from inner
from database.connection import get_engine
