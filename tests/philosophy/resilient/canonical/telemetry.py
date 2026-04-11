"""
Structured logging with correlation IDs.

Rubric #4: every log line must be structured (JSON or equivalent
key-value form) and carry a correlation ID that follows an order
through every stage of the pipeline. Principle #13 made concrete:
the system must explain itself to its on-call engineer.

The correlation ID lives in a ContextVar so every log call in the
pipeline inherits it without having to pass the ID through every
function signature. ``correlation`` is a context manager: entering
it sets the ID for the duration of the block, exiting it restores
the previous value. Every log line emitted from inside the block
— including logs from helper threads that inherit the context via
``contextvars.copy_context()`` — is automatically tagged.
"""

from __future__ import annotations

import contextlib
import json
import sys
import time
from contextvars import ContextVar
from typing import Any, Iterator, TextIO

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# In-memory sink; good enough for the exemplar and for tests. Swap
# for a logging handler + fluentbit + a real log backend in prod.
SINK: list[dict[str, Any]] = []


@contextlib.contextmanager
def correlation(cid: str) -> Iterator[str]:
    """Bind ``cid`` as the active correlation ID for the duration of the block."""
    token = _correlation_id.set(cid)
    try:
        yield cid
    finally:
        _correlation_id.reset(token)


def log(level: str, event: str, stream: TextIO | None = None, **fields: Any) -> None:
    """Emit one structured log line.

    Fields are rendered as JSON with a timestamp, level, event name,
    correlation_id, and any caller-supplied keys. The record is also
    stored in the in-process sink so tests can assert on telemetry
    without parsing stdout.
    """
    record: dict[str, Any] = {
        "ts": _now_iso(),
        "level": level,
        "event": event,
        "correlation_id": _correlation_id.get(),
    }
    record.update(fields)
    SINK.append(record)
    out = stream if stream is not None else sys.stderr
    out.write(json.dumps(record, default=str) + "\n")


def reset_sink() -> None:
    SINK.clear()


def _now_iso() -> str:
    # ``time.time`` rather than datetime.utcnow so we do not import a
    # module for one call; the telemetry format is ISO-8601-ish UTC.
    t = time.time()
    ms = int((t - int(t)) * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f".{ms:03d}Z"
