"""
A minimal Result type for returning errors as values.

``Ok`` carries a success value; ``Err`` carries a failure value. Both
are frozen dataclasses, so a ``Result`` can be stored in other frozen
structures and passed between pure functions without aliasing
hazards. Callers discriminate via ``isinstance`` or ``match``.

The exemplar deliberately does not ship a ``bind`` / ``map`` / ``and_then``
combinator library. Python is not Haskell; the honest functional
translation of error threading in Python is an early-return check
with a pattern match, and inventing a monad library just to prove
erudition is precisely the abstraction-astronautics that the
Functional axiom sheet's degenerate-case section warns against.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    """A successful result carrying its value."""

    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    """A failed result carrying an error value."""

    error: E
