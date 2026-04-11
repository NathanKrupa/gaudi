"""
Functional / Algebraic reference implementation of the canonical task.

Every value is immutable. Every error is returned as data, not raised.
Every function is a pure transformation over frozen inputs. The
domain kernel imports nothing from logging, os, requests, or the
clock — time is passed in as a value. See ``README.md`` in this
directory for the full rubric score.
"""
