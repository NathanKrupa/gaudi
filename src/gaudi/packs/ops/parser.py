# ABOUTME: Ops pack parser -- discovers Dockerfiles and stitches their instructions.
# ABOUTME: Walks a project root for files named Dockerfile (or Dockerfile.*).
"""Ops pack parser.

Reads ops/build/deploy artifacts from a project tree. Currently parses
Dockerfiles; CI configs (GitHub Actions, GitLab CI) will be added later.

The parser is intentionally line-based and dependency-free. We do not pull in
dockerfile-parse or pyparsing -- the rules we ship today only need instruction
names, argument strings, and line numbers, all of which are derivable with
straight string operations.
"""

from __future__ import annotations

from pathlib import Path

from gaudi.config import load_config
from gaudi.excludes import (
    CORE_EXCLUDE_GLOBS,
    compile_exclude_patterns,
    is_excluded,
)
from gaudi.packs.ops.context import DockerfileInfo, DockerfileLine, OpsContext


# Only the canonical filename ``Dockerfile`` is accepted today. Stage variants
# (``Dockerfile.prod``, ``app.Dockerfile``) are a real Docker convention but
# distinguishing them from source files in disguise (``dockerfile.py``,
# ``Dockerfile.tar.gz``) requires either a denylist or a config-driven
# allowlist. Both are speculative until a user asks. The earlier
# ``startswith("dockerfile.")`` check matched ``dockerfile.py`` during dogfood
# and there is no clean structural rule that distinguishes "stage" from
# "extension". Stage-variant support is tracked as a follow-up.
def _is_dockerfile(path: Path) -> bool:
    return path.name == "Dockerfile"


def _stitch_instructions(source: str) -> list[DockerfileLine]:
    """Walk a Dockerfile's text and produce one DockerfileLine per logical instruction.

    Handles backslash line continuations and skips blank/comment lines. The
    `lineno` of each instruction is the 1-based line where it begins.
    """
    instructions: list[DockerfileLine] = []
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        start_lineno = i + 1
        # Stitch continuations: a trailing backslash means the next line is part
        # of the same logical instruction.
        joined_parts: list[str] = []
        raw_parts: list[str] = []
        while True:
            current = lines[i]
            raw_parts.append(current)
            stripped_current = current.rstrip()
            if stripped_current.endswith("\\"):
                joined_parts.append(stripped_current[:-1].strip())
                i += 1
                if i >= len(lines):
                    break
            else:
                joined_parts.append(stripped_current.strip())
                i += 1
                break

        joined = " ".join(p for p in joined_parts if p)
        # Split into instruction word + remainder.
        parts = joined.split(None, 1)
        if not parts:
            continue
        instruction = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""
        instructions.append(
            DockerfileLine(
                lineno=start_lineno,
                instruction=instruction,
                args=args,
                raw="\n".join(raw_parts),
            )
        )
    return instructions


def _parse_dockerfile(path: Path, root: Path) -> DockerfileInfo:
    source = path.read_text(encoding="utf-8", errors="replace")
    relative = path.relative_to(root)
    return DockerfileInfo(
        path=path,
        relative_path=str(relative),
        source=source,
        instructions=_stitch_instructions(source),
    )


def parse_project(path: Path) -> OpsContext:
    """Walk a project tree and return an OpsContext.

    Accepts either a directory (walked recursively) or a single Dockerfile.
    """
    if path.is_file():
        root = path.parent
        context = OpsContext(root=root)
        if _is_dockerfile(path):
            context.dockerfiles.append(_parse_dockerfile(path, root))
        return context

    root = path
    context = OpsContext(root=root)

    config = load_config(root)
    extra_excludes = list(config.get("exclude") or [])
    compiled_excludes = compile_exclude_patterns(list(CORE_EXCLUDE_GLOBS) + extra_excludes)

    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file():
            continue
        relative = str(candidate.relative_to(root))
        if is_excluded(relative, compiled_excludes):
            continue
        if _is_dockerfile(candidate):
            context.dockerfiles.append(_parse_dockerfile(candidate, root))
    return context
