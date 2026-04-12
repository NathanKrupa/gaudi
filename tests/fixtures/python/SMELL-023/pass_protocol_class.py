"""Fixture for SMELL-023: Protocol class with stub method bodies.

Protocol classes use ``...`` or ``pass`` as method bodies to define
the interface contract. This is not a refused bequest — Protocol
methods are declarations, not inherited behavior being refused.
"""

from typing import Protocol


class Repository(Protocol):
    def get(self, key: str) -> object: ...

    def save(self, key: str, value: object) -> None: ...

    def delete(self, key: str) -> None: ...
