# ABOUTME: Tests for the ops pack -- Dockerfile parser, OpsPack discovery, and engine integration.
# ABOUTME: The two-pack integration test proves Python and Ops findings co-exist on a mixed project.
"""Tests for the ops pack."""

from __future__ import annotations

from pathlib import Path

from gaudi.engine import Engine
from gaudi.packs.ops.context import OpsContext
from gaudi.packs.ops.pack import OpsPack
from gaudi.packs.ops.parser import _stitch_instructions, parse_project
from gaudi.packs.python.pack import PythonPack


class TestDockerfileParser:
    """The line-stitching parser is the load-bearing primitive for every ops rule."""

    def test_skips_blank_and_comment_lines(self) -> None:
        source = "\n# a comment\n\nFROM scratch\n"
        instructions = _stitch_instructions(source)
        assert len(instructions) == 1
        assert instructions[0].instruction == "FROM"
        assert instructions[0].args == "scratch"
        assert instructions[0].lineno == 4

    def test_uppercases_instruction_keyword(self) -> None:
        instructions = _stitch_instructions("from python:3.12-slim\n")
        assert instructions[0].instruction == "FROM"

    def test_stitches_backslash_continuations(self) -> None:
        source = "RUN apt-get update \\\n    && apt-get install -y curl \\\n    && rm -rf /var/lib/apt/lists/*\n"
        instructions = _stitch_instructions(source)
        assert len(instructions) == 1
        instr = instructions[0]
        assert instr.instruction == "RUN"
        assert "apt-get update" in instr.args
        assert "apt-get install -y curl" in instr.args
        assert "rm -rf /var/lib/apt/lists/*" in instr.args
        assert instr.lineno == 1


class TestOpsPackDiscovery:
    """OpsPack must claim Dockerfiles by name (no extension) via the new filenames hook."""

    def test_can_handle_directory_with_dockerfile(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        assert OpsPack().can_handle(tmp_path) is True

    def test_does_not_claim_directory_without_dockerfile(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
        assert OpsPack().can_handle(tmp_path) is False

    def test_parser_returns_ops_context(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        context = parse_project(tmp_path)
        assert isinstance(context, OpsContext)
        assert len(context.dockerfiles) == 1
        assert context.dockerfiles[0].instructions[0].instruction == "FROM"


class TestTwoPackIntegration:
    """A project with both .py files and a Dockerfile should fire both packs.

    This is the proof that the new ops pack co-exists with the python pack
    instead of stealing or shadowing it. Findings from both packs must appear
    in a single engine.check() result, sorted by severity then code.
    """

    def test_both_packs_fire_on_mixed_project(self, tmp_path: Path) -> None:
        # A bad Dockerfile (OPS-006: pip install without --no-cache-dir)
        # and a bad service module (OPS-008: hardcoded host/port).
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname = 'mixed'\nversion = '0.0.0'\n", encoding="utf-8"
        )
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.12-slim\n"
            "COPY requirements.txt .\n"
            "RUN pip install -r requirements.txt\n"
            "COPY . .\n",
            encoding="utf-8",
        )
        (tmp_path / "server.py").write_text(
            "from flask import Flask\napp = Flask(__name__)\napp.run(host='0.0.0.0', port=8080)\n",
            encoding="utf-8",
        )

        engine = Engine()
        engine.register_pack(PythonPack())
        engine.register_pack(OpsPack())

        findings = engine.check(tmp_path)
        codes = {f.code for f in findings}
        assert "OPS-006" in codes, "ops pack did not fire on the bad Dockerfile"
        assert "OPS-008" in codes, "python pack did not fire on the bad server module"
