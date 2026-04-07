# ABOUTME: Tests for anthropic SDK library rules (LLM-ARCH-001, LLM-ERR-001, LLM-SCALE-001).
# ABOUTME: Covers detection, positive triggers, and negative (clean code) cases.
"""Tests for anthropic SDK library rules."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack
from gaudi.packs.python.parser import parse_project

_PYPROJECT_MINIMAL = '[project]\nname="t"\n'
_PYPROJECT_ANTHROPIC = '[project]\nname="t"\ndependencies = ["anthropic"]\n'
_PYPROJECT_TOML = "pyproject.toml"
_APP_PY = "app.py"
_LOCK_FILE = "requirements-lock.txt"
_LIBRARY = "anthropic"
_CODE_ARCH = "LLM-ARCH-001"
_CODE_ERR = "LLM-ERR-001"
_CODE_SCALE = "LLM-SCALE-001"


def _findings_for(source: str, code: str) -> list:
    """Create a temp project with anthropic dependency, run pack, filter by rule code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / _PYPROJECT_TOML).write_text(_PYPROJECT_ANTHROPIC)
        (root / _LOCK_FILE).write_text("")
        (root / _APP_PY).write_text(source)
        pack = PythonPack()
        findings = pack.check(root)
        return [f for f in findings if f.code == code]


class TestAnthropicDetection:
    def test_detect_from_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / _PYPROJECT_TOML).write_text(
                '[project]\nname = "myapp"\ndependencies = ["anthropic>=0.18"]\n'
            )
            (root / _APP_PY).write_text("x = 1\n")
            ctx = parse_project(root)
            assert _LIBRARY in ctx.detected_libraries

    def test_detect_from_requirements(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / _PYPROJECT_TOML).write_text(_PYPROJECT_MINIMAL)
            (root / "requirements.txt").write_text("anthropic>=0.18\n")
            (root / _APP_PY).write_text("x = 1\n")
            ctx = parse_project(root)
            assert _LIBRARY in ctx.detected_libraries

    def test_detect_from_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / _PYPROJECT_TOML).write_text(_PYPROJECT_MINIMAL)
            (root / _APP_PY).write_text("import anthropic\n")
            ctx = parse_project(root)
            assert _LIBRARY in ctx.detected_libraries

    def test_rules_skipped_when_not_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / _PYPROJECT_TOML).write_text(_PYPROJECT_MINIMAL)
            (root / _LOCK_FILE).write_text("")
            (root / _APP_PY).write_text("def hello():\n    return 42\n")
            pack = PythonPack()
            findings = pack.check(root)
            llm_codes = [f.code for f in findings if f.code.startswith("LLM-")]
            assert llm_codes == [], f"LLM rules fired without library: {llm_codes}"


class TestHardcodedModel:
    """LLM-ARCH-001: Model name as string literal instead of config/constant."""

    def test_hardcoded_model_string(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "msg = client.messages.create(\n"
            '    model="claude-3-5-sonnet-20241022",\n'
            "    max_tokens=100,\n"
            '    messages=[{"role": "user", "content": "hi"}],\n'
            ")\n"
        )
        hits = _findings_for(source, _CODE_ARCH)
        assert len(hits) == 1

    def test_hardcoded_model_in_async(self):
        source = (
            "import anthropic\n"
            "client = anthropic.AsyncAnthropic()\n"
            "async def call():\n"
            "    msg = await client.messages.create(\n"
            '        model="claude-3-opus-20240229",\n'
            "        max_tokens=100,\n"
            '        messages=[{"role": "user", "content": "hi"}],\n'
            "    )\n"
        )
        hits = _findings_for(source, _CODE_ARCH)
        assert len(hits) == 1

    def test_model_from_variable_no_finding(self):
        source = (
            "import anthropic\n"
            "MODEL = 'claude-3-5-sonnet-20241022'\n"
            "client = anthropic.Anthropic()\n"
            "msg = client.messages.create(\n"
            "    model=MODEL,\n"
            "    max_tokens=100,\n"
            '    messages=[{"role": "user", "content": "hi"}],\n'
            ")\n"
        )
        hits = _findings_for(source, _CODE_ARCH)
        assert len(hits) == 0

    def test_model_from_config_no_finding(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "msg = client.messages.create(\n"
            "    model=config.MODEL_NAME,\n"
            "    max_tokens=100,\n"
            '    messages=[{"role": "user", "content": "hi"}],\n'
            ")\n"
        )
        hits = _findings_for(source, _CODE_ARCH)
        assert len(hits) == 0


class TestBareAPICall:
    """LLM-ERR-001: API call without error handling."""

    def test_bare_api_call(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "def call():\n"
            "    msg = client.messages.create(\n"
            "        model=MODEL,\n"
            "        max_tokens=100,\n"
            '        messages=[{"role": "user", "content": "hi"}],\n'
            "    )\n"
        )
        hits = _findings_for(source, _CODE_ERR)
        assert len(hits) == 1

    def test_api_call_with_try_except(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "def call():\n"
            "    try:\n"
            "        msg = client.messages.create(\n"
            "            model=MODEL,\n"
            "            max_tokens=100,\n"
            '            messages=[{"role": "user", "content": "hi"}],\n'
            "        )\n"
            "    except anthropic.APIError:\n"
            "        pass\n"
        )
        hits = _findings_for(source, _CODE_ERR)
        assert len(hits) == 0

    def test_api_call_with_generic_except(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "def call():\n"
            "    try:\n"
            "        msg = client.messages.create(\n"
            "            model=MODEL,\n"
            "            max_tokens=100,\n"
            '            messages=[{"role": "user", "content": "hi"}],\n'
            "        )\n"
            "    except Exception:\n"
            "        pass\n"
        )
        hits = _findings_for(source, _CODE_ERR)
        assert len(hits) == 0

    def test_top_level_call_no_try(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "msg = client.messages.create(\n"
            "    model=MODEL,\n"
            "    max_tokens=100,\n"
            '    messages=[{"role": "user", "content": "hi"}],\n'
            ")\n"
        )
        hits = _findings_for(source, _CODE_ERR)
        assert len(hits) == 1


class TestNoTokenCounting:
    """LLM-SCALE-001: Prompt construction without token length check."""

    def test_no_token_counting(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "def call(text):\n"
            "    msg = client.messages.create(\n"
            "        model=MODEL,\n"
            "        max_tokens=100,\n"
            '        messages=[{"role": "user", "content": text}],\n'
            "    )\n"
        )
        hits = _findings_for(source, _CODE_SCALE)
        assert len(hits) == 1

    def test_with_count_tokens(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "def call(text):\n"
            "    token_count = client.count_tokens(text)\n"
            "    if token_count > 4000:\n"
            "        text = text[:4000]\n"
            "    msg = client.messages.create(\n"
            "        model=MODEL,\n"
            "        max_tokens=100,\n"
            '        messages=[{"role": "user", "content": text}],\n'
            "    )\n"
        )
        hits = _findings_for(source, _CODE_SCALE)
        assert len(hits) == 0

    def test_with_tiktoken(self):
        source = (
            "import anthropic\n"
            "import tiktoken\n"
            "client = anthropic.Anthropic()\n"
            "def call(text):\n"
            "    enc = tiktoken.get_encoding('cl100k_base')\n"
            "    tokens = enc.encode(text)\n"
            "    msg = client.messages.create(\n"
            "        model=MODEL,\n"
            "        max_tokens=100,\n"
            '        messages=[{"role": "user", "content": text}],\n'
            "    )\n"
        )
        hits = _findings_for(source, _CODE_SCALE)
        assert len(hits) == 0

    def test_with_num_tokens_reference(self):
        source = (
            "import anthropic\n"
            "client = anthropic.Anthropic()\n"
            "def call(text):\n"
            "    num_tokens = estimate_tokens(text)\n"
            "    msg = client.messages.create(\n"
            "        model=MODEL,\n"
            "        max_tokens=100,\n"
            '        messages=[{"role": "user", "content": text}],\n'
            "    )\n"
        )
        hits = _findings_for(source, _CODE_SCALE)
        assert len(hits) == 0
