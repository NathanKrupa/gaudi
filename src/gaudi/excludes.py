# ABOUTME: Shared glob-based path exclusion used by every pack's project walker.
# ABOUTME: One regex compiler, one matcher, one set of universal skip patterns.
"""Glob-based path exclusion shared across packs.

The same pattern syntax (and the same compiler) handles both built-in skip
lists (.git, venv, node_modules, ...) and user-supplied excludes from
``gaudi.toml``. Packs import from here instead of duplicating the regex
compiler.

Pattern syntax (gitignore-ish):
    ``**``  -- match any number of path segments (including zero)
    ``*``   -- match any characters except ``/``
    ``?``   -- match a single character except ``/``

Patterns are matched against POSIX-style relative paths.
"""

from __future__ import annotations

import re

# Universal skip patterns. Every pack should ignore these. Pack-specific skips
# (Django migrations for the python pack, for example) are added by the pack
# itself, layered on top of this list.
CORE_EXCLUDE_GLOBS: tuple[str, ...] = (
    "**/venv/**",
    "**/.venv/**",
    "**/env/**",
    "**/.env/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.git/**",
)


def compile_glob(pattern: str) -> re.Pattern[str]:
    """Translate a gitignore-ish glob into an anchored regex."""
    out: list[str] = ["^"]
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*" and i + 1 < len(pattern) and pattern[i + 1] == "*":
            i += 2
            if i < len(pattern) and pattern[i] == "/":
                # ``**/`` matches zero or more leading directories.
                out.append("(?:.*/)?")
                i += 1
            else:
                # Trailing ``**`` matches anything (including ``/``).
                out.append(".*")
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c in r".+()|^${}\\":
            out.append("\\" + c)
            i += 1
        else:
            out.append(c)
            i += 1
    out.append("$")
    return re.compile("".join(out))


def compile_exclude_patterns(patterns: list[str] | tuple[str, ...]) -> list[re.Pattern[str]]:
    return [compile_glob(p) for p in patterns]


def is_excluded(relpath: str, compiled: list[re.Pattern[str]]) -> bool:
    """Return True if the POSIX-normalized relative path matches any pattern."""
    posix = relpath.replace("\\", "/")
    return any(rx.match(posix) for rx in compiled)
