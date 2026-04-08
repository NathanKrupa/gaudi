# ABOUTME: Ops pack context -- structural information about deploy/build artifacts.
# ABOUTME: Currently models Dockerfiles; CI configs and Makefiles will join later.
"""Context object passed to ops pack rules.

Mirrors the shape of :mod:`gaudi.packs.python.context` but for non-language
artifacts. Each artifact type gets its own dataclass; rules walk the lists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DockerfileLine:
    """One logical Dockerfile instruction after line-continuation stitching.

    Attributes:
        lineno: 1-based line number where the instruction begins.
        instruction: Uppercased Dockerfile instruction (FROM, RUN, COPY, ...).
        args: The remainder of the instruction, with continuations joined.
        raw: The original raw text of the instruction (multi-line if continued).
    """

    lineno: int
    instruction: str
    args: str
    raw: str


@dataclass
class DockerfileInfo:
    """A single Dockerfile parsed into logical instructions."""

    path: Path
    relative_path: str
    source: str = ""
    instructions: list[DockerfileLine] = field(default_factory=list)


@dataclass
class OpsContext:
    """Complete structural context for the ops artifacts in a project."""

    root: Path
    dockerfiles: list[DockerfileInfo] = field(default_factory=list)
