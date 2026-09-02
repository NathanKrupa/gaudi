# ABOUTME: Locates the project root and project-scoped files from any path inside a project.
# ABOUTME: Project-level questions must be answered against the project, not the checked path.
"""Project-root discovery.

``gaudi check apps/billing`` asks about one directory, but some questions —
"does this project declare a pyproject.toml?", "which gaudi.toml governs this
code?" — are about the *project*, and answering them from the checked path
manufactures findings the project already answers. That is why one estate repo
carried six app-scoped copies of ``gaudi.toml``: the config was only ever read
from the path passed to ``check``.
"""

from __future__ import annotations

from pathlib import Path

# Files and directories that mark a directory as the root of a project. The
# walk runs nearest-first, so a monorepo member carrying its own pyproject.toml
# is its own root, and ``.git`` terminates the walk at the repository boundary
# rather than letting it escape into the user's home directory.
PROJECT_ROOT_MARKERS: tuple[str, ...] = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "uv.lock",
    ".git",
    "requirements.txt",
)


def find_project_root(start: Path) -> Path:
    """Return the nearest ancestor of ``start`` (inclusive) that looks like a project root.

    Falls back to ``start`` itself when nothing above it is marked — a bare
    directory is its own project, which is what makes STRUCT-011 still fire on
    a genuinely unpackaged tree.
    """
    start = start if start.is_dir() else start.parent
    for candidate in (start, *start.parents):
        if any((candidate / marker).exists() for marker in PROJECT_ROOT_MARKERS):
            return candidate
    return start


def find_config_file(start: Path, filename: str) -> Path | None:
    """Find ``filename`` at ``start`` or in an ancestor, stopping at the project root.

    The walk is bounded so a stray config outside the project — in a parent
    directory, a temp directory, the user's home — can never be adopted by it.
    """
    start = start if start.is_dir() else start.parent
    root = find_project_root(start)

    candidate = start
    while True:
        path = candidate / filename
        if path.exists():
            return path
        if candidate == root or candidate == candidate.parent:
            return None
        candidate = candidate.parent
