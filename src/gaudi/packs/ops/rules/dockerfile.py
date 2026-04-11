# ABOUTME: Dockerfile rules for the ops pack -- starts with OPS-006 anti-patterns.
# ABOUTME: Operates on the stitched DockerfileLine list, not the raw text.
from __future__ import annotations

import re

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.ops.context import DockerfileInfo, DockerfileLine, OpsContext

# A `pip install` invocation, allowing `pip3` and `python -m pip` forms.
# We match the *invocation*, not just the substring "pip install", so that
# "skip pip install errors" or similar prose in a comment cannot trip us up
# (comments are stripped by the parser anyway, but defensive matching is cheap).
_PIP_INSTALL_RE = re.compile(
    r"(?:^|[\s;&|])"  # start, or after whitespace/separator
    r"(?:python(?:3)?\s+-m\s+)?"  # optional `python -m`
    r"pip(?:3)?\s+install\b",
)

# Filenames that, when COPY'd, indicate a dependency-manifest copy. The cache
# layer that follows them gets reused as long as these files don't change, so
# they must be COPY'd before the broad COPY of the rest of the source.
_DEPENDENCY_MANIFEST_TOKENS: tuple[str, ...] = (
    "requirements.txt",
    "requirements-",  # requirements-dev.txt, requirements-prod.txt, ...
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "uv.lock",
)


def _is_pip_install_without_no_cache_dir(line: DockerfileLine) -> bool:
    if line.instruction != "RUN":
        return False
    args = line.args
    if not _PIP_INSTALL_RE.search(args):
        return False
    return "--no-cache-dir" not in args


def _copy_sources(args: str) -> list[str]:
    """Return the source operands of a COPY instruction.

    Dockerfile COPY syntax is ``COPY [--chown=...] <src>... <dest>``. The last
    token is the destination; everything else (after stripping flags) is a
    source. Both shell and JSON-array forms are accepted; rules don't care.
    """
    tokens = args.split()
    # Strip leading flags like --chown=user:group, --from=stage.
    while tokens and tokens[0].startswith("--"):
        tokens.pop(0)
    if len(tokens) < 2:
        return []
    return tokens[:-1]


def _is_broad_source_copy(args: str) -> bool:
    """A COPY whose source is the build context root (`.`) is a broad copy."""
    sources = _copy_sources(args)
    return any(src == "." for src in sources)


def _is_dependency_manifest_copy(args: str) -> bool:
    sources = _copy_sources(args)
    for src in sources:
        # Strip leading ./ to compare bare names.
        bare = src.lstrip("./")
        for token in _DEPENDENCY_MANIFEST_TOKENS:
            if bare == token or bare.startswith(token):
                return True
    return False


# ---------------------------------------------------------------
# OPS-006  DockerfileAntiPattern
# ---------------------------------------------------------------


class DockerfileAntiPattern(Rule):
    """Detect Dockerfile patterns that bloat images or bust the layer cache.

    Two related patterns are flagged:

    1. ``RUN pip install ...`` without ``--no-cache-dir``. The wheel cache adds
       tens of megabytes to every layer for no runtime benefit.
    2. ``COPY . .`` (or any broad source copy) appearing *before* a COPY of a
       dependency manifest (``requirements.txt``, ``pyproject.toml``,
       ``poetry.lock``, ``Pipfile``). Docker's layer cache is keyed by the COPY
       contents, so a broad copy invalidates every dependency-install layer on
       any source change. The fix is to COPY the manifest first, install, then
       COPY the rest.

    Principles: #6 (Configuration is a boundary, not a literal),
    #14 (Build pipelines are part of the architecture).
    Source: Docker Best Practices, 12-Factor App V (Build/release/run).
    """

    code = "OPS-006"
    severity = Severity.WARN
    category = Category.OPERATIONS
    message_template = "Dockerfile {file}:{line} -- {detail}"
    recommendation_template = (
        "Pass --no-cache-dir to pip install, and COPY dependency manifests"
        " (requirements.txt, pyproject.toml, poetry.lock) before COPY . ."
        " so the dependency-install layer is cached across source changes."
    )

    def check(self, context: OpsContext) -> list[Finding]:
        findings: list[Finding] = []
        for dockerfile in context.dockerfiles:
            findings.extend(self._check_dockerfile(dockerfile))
        return findings

    def _check_dockerfile(self, dockerfile: DockerfileInfo) -> list[Finding]:
        findings: list[Finding] = []
        instructions = dockerfile.instructions

        # Pattern 1: pip install without --no-cache-dir.
        for instr in instructions:
            if _is_pip_install_without_no_cache_dir(instr):
                findings.append(
                    self.finding(
                        file=dockerfile.relative_path,
                        line=instr.lineno,
                        detail="pip install without --no-cache-dir bloats the image layer",
                    )
                )

        # Pattern 2: broad COPY before dependency manifest COPY.
        first_broad_copy_idx: int | None = None
        first_manifest_copy_idx: int | None = None
        for idx, instr in enumerate(instructions):
            if instr.instruction != "COPY":
                continue
            if first_broad_copy_idx is None and _is_broad_source_copy(instr.args):
                first_broad_copy_idx = idx
            if first_manifest_copy_idx is None and _is_dependency_manifest_copy(instr.args):
                first_manifest_copy_idx = idx

        if first_broad_copy_idx is not None and (
            first_manifest_copy_idx is None or first_broad_copy_idx < first_manifest_copy_idx
        ):
            broad = instructions[first_broad_copy_idx]
            findings.append(
                self.finding(
                    file=dockerfile.relative_path,
                    line=broad.lineno,
                    detail=(
                        "broad COPY before dependency manifest copy busts the"
                        " dependency-install layer cache"
                    ),
                )
            )

        return findings


# ---------------------------------------------------------------
# OPS-007  NoDockerignore
# ---------------------------------------------------------------


class NoDockerignore(Rule):
    """Detect projects that have a Dockerfile but no .dockerignore.

    Without ``.dockerignore``, every ``COPY .`` ships the entire build context
    to the daemon -- ``.git``, virtualenvs, ``__pycache__``, secrets, test
    fixtures, the lot. Image builds get slower and leakier with every
    untracked file added.

    Principles: #6 (Configuration is a boundary, not a literal),
    #14 (Build pipelines are part of the architecture).
    Source: Docker Best Practices.
    """

    code = "OPS-007"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has Dockerfile but no .dockerignore"
    recommendation_template = (
        "Add .dockerignore at the project root to keep .git, venv,"
        " __pycache__, tests, and secrets out of the build context."
        " Without it, every COPY . sends megabytes of noise to the daemon"
        " and risks leaking files into the image."
    )

    def check(self, context: OpsContext) -> list[Finding]:
        if not context.dockerfiles:
            return []
        if (context.root / ".dockerignore").exists():
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-009  MissingHealthCheck
# ---------------------------------------------------------------


class MissingHealthCheck(Rule):
    """Detect Dockerfiles that have no HEALTHCHECK instruction.

    Without a HEALTHCHECK, orchestrators (Docker, Kubernetes, ECS) cannot
    distinguish a process that is running from one that is healthy. A wedged
    container with a live PID happily receives traffic until something else
    notices, which is usually a customer.

    Principles: #11 (The reader is the user -- the orchestrator IS a reader),
    #14 (Build pipelines are part of the architecture).
    Source: Nygard *Release It!* Ch. 17, Docker Best Practices.
    """

    code = "OPS-009"
    severity = Severity.INFO
    category = Category.OPERATIONS
    # Health checks are a long-lived-service concept. One-shot Unix
    # containers and Data-Oriented batch jobs terminate by completing.
    philosophy_scope = frozenset(
        {
            "classical",
            "pragmatic",
            "functional",
            "resilient",
            "convention",
            "event-sourced",
        }
    )
    message_template = "Dockerfile {file} has no HEALTHCHECK instruction"
    recommendation_template = (
        "Add a HEALTHCHECK instruction so orchestrators can detect a sick"
        " container before routing traffic to it. For pure builder stages"
        " or one-shot CLIs, suppress this rule per file."
    )

    def check(self, context: OpsContext) -> list[Finding]:
        findings: list[Finding] = []
        for dockerfile in context.dockerfiles:
            if any(instr.instruction == "HEALTHCHECK" for instr in dockerfile.instructions):
                continue
            findings.append(self.finding(file=dockerfile.relative_path))
        return findings


DOCKERFILE_RULES: tuple[Rule, ...] = (
    DockerfileAntiPattern(),
    NoDockerignore(),
    MissingHealthCheck(),
)
