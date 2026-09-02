# ABOUTME: ERR-003 keys on the swallow, not on the level the handler logged at.
# ABOUTME: A warning-logged swallow is the same defect as an error-logged one.

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from gaudi.packs.python.ast_helpers import LOG_METHODS, is_logger_call
from gaudi.packs.python.pack import PythonPack

# Every level a logger exposes. #256 measured one estate repo at 127
# warning-logged swallows against 17 error-logged: keying on the level made
# the rule blind to 88% of its own population, and that blindness shipped
# grantspider 7461aa6a.
LOG_LEVELS = ("debug", "info", "warning", "warn", "error", "exception", "critical")


def _swallowing_module(level: str) -> str:
    return textwrap.dedent(f"""
        import logging

        logger = logging.getLogger(__name__)


        def fetch(store, key):
            try:
                return store.read(key)
            except OSError:
                logger.{level}("could not read %s", key)
                return None
    """)


def _reraising_module(level: str) -> str:
    return textwrap.dedent(f"""
        import logging

        logger = logging.getLogger(__name__)


        def fetch(store, key):
            try:
                return store.read(key)
            except OSError:
                logger.{level}("could not read %s", key)
                raise
    """)


def _codes(tmp_path: Path, source: str) -> set[str]:
    module = tmp_path / "swallow.py"
    module.write_text(source, encoding="utf-8")
    return {f.code for f in PythonPack().check(module)}


class TestLevelIndependence:
    @pytest.mark.parametrize("level", LOG_LEVELS)
    def test_a_swallow_fires_at_every_level(self, level: str, tmp_path: Path):
        assert "ERR-003" in _codes(tmp_path, _swallowing_module(level))

    @pytest.mark.parametrize("level", LOG_LEVELS)
    def test_a_re_raise_clears_it_at_every_level(self, level: str, tmp_path: Path):
        assert "ERR-003" not in _codes(tmp_path, _reraising_module(level))


class TestScope:
    def test_a_handler_that_does_not_log_is_out_of_scope(self, tmp_path: Path):
        """ERR-001 and ERR-004 own the silent handler; ERR-003 must not duplicate them."""
        source = textwrap.dedent("""
            def fetch(store, key):
                try:
                    return store.read(key)
                except OSError:
                    return None
        """)

        assert "ERR-003" not in _codes(tmp_path, source)

    def test_a_bare_pass_handler_stays_err_004s(self, tmp_path: Path):
        """Subsumption: ERR-004 already fires on `except: pass`. ERR-003 stays off it."""
        source = textwrap.dedent("""
            def fetch(store, key):
                try:
                    return store.read(key)
                except OSError:
                    pass
        """)

        codes = _codes(tmp_path, source)
        assert "ERR-004" in codes
        assert "ERR-003" not in codes


class TestSharedHelper:
    """The logger-call test lives in one place, not once per rule file."""

    def test_log_methods_covers_every_level(self):
        assert set(LOG_LEVELS) <= LOG_METHODS

    def test_is_logger_call_recognises_an_attribute_call(self):
        import ast

        call = ast.parse("logger.warning('x')").body[0].value
        assert is_logger_call(call) is True

    def test_is_logger_call_rejects_a_plain_function_call(self):
        import ast

        call = ast.parse("warning('x')").body[0].value
        assert is_logger_call(call) is False
