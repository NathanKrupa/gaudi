# ABOUTME: Scans the codebase and generates a comprehensive tool registry.
# ABOUTME: Universal script — works in any Python project. Run: python scripts/tools/generate_tool_registry.py

"""
Tool Registry Generator
=======================
Introspects the codebase to discover all CLI tools, scripts, and entry points.
Outputs a structured markdown file at data/tool_registry.md.

Discovery sources:
  1. Console scripts from pyproject.toml [project.scripts]
  2. Runnable scripts in scripts/ (detected via ABOUTME, argparse, click, __main__)
  3. Module entry points (__main__.py files)
  4. Streamlit apps
  5. Root-level runnable scripts

Description extraction priority:
  ABOUTME comments > module docstring > argparse description > Click docstring
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Category normalization
# ---------------------------------------------------------------------------


def normalize_category(raw: str) -> str:
    """Map a raw directory/package name to a display-friendly category."""
    return raw.replace("_", " ").title()


def _infer_console_script_category(module_path: str) -> str:
    """Infer a category from a console script's dotted module path."""
    parts = module_path.split(".")
    if len(parts) > 1:
        return normalize_category(parts[1])
    return "General"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

TOOL_TYPE_PRIORITY = {
    "console_script": 0,
    "module_entry": 1,
    "streamlit": 2,
    "script": 3,
    "root_script": 4,
}


@dataclass
class ToolEntry:
    name: str
    location: str  # relative path from project root
    command: str
    description: str
    category: str
    tool_type: str  # console_script | script | module_entry | streamlit | root_script
    internal: bool = False  # True for _prefixed helper scripts

    @property
    def priority(self) -> int:
        return TOOL_TYPE_PRIORITY.get(self.tool_type, 99)


# ---------------------------------------------------------------------------
# Description extraction helpers
# ---------------------------------------------------------------------------


def _read_file(path: Path) -> str:
    """Read a file, tolerating encoding issues."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def extract_aboutme(path: Path) -> str | None:
    """Extract ABOUTME lines from the first 10 lines of a file."""
    text = _read_file(path)
    if not text:
        return None
    lines = text.splitlines()[:10]
    aboutme_lines = []
    for line in lines:
        stripped = line.strip()
        for prefix in ("# ABOUTME:", "ABOUTME:"):
            if stripped.startswith(prefix):
                aboutme_lines.append(stripped[len(prefix) :].strip())
                break
    return " — ".join(aboutme_lines) if aboutme_lines else None


def extract_module_docstring(path: Path) -> str | None:
    """Extract the module-level docstring via AST."""
    text = _read_file(path)
    if not text:
        return None
    try:
        tree = ast.parse(text, filename=str(path))
        doc = ast.get_docstring(tree)
        if doc:
            for line in doc.strip().splitlines():
                line = line.strip()
                if line and not line.startswith("ABOUTME"):
                    return line
        return None
    except SyntaxError:
        return None


def extract_argparse_description(path: Path) -> str | None:
    """Look for ArgumentParser(description=...) in the AST."""
    text = _read_file(path)
    if not text:
        return None
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "ArgumentParser":
            continue
        for kw in node.keywords:
            if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                val = kw.value.value
                if isinstance(val, str) and val.strip():
                    return val.strip()
    return None


def extract_click_group_docstring(path: Path) -> str | None:
    """Extract the docstring from the first Click group/command function."""
    text = _read_file(path)
    if not text:
        return None
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            dec_str = ast.dump(dec)
            if "group" in dec_str or "command" in dec_str:
                doc = ast.get_docstring(node)
                if doc:
                    return doc.strip().splitlines()[0].strip()
    return None


def extract_description(path: Path) -> str:
    """Try all extraction strategies, return best available description."""
    for extractor in (
        extract_aboutme,
        extract_module_docstring,
        extract_argparse_description,
        extract_click_group_docstring,
    ):
        result = extractor(path)
        if result:
            return result
    return "(no description found)"


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _has_main_guard(text: str) -> bool:
    """Check if file has if __name__ == '__main__' block."""
    return bool(re.search(r"""if\s+__name__\s*==\s*['"]__main__['"]""", text))


def _imports_module(text: str, module: str) -> bool:
    """Check if file imports a given module (simple text check)."""
    return bool(
        re.search(rf"(?:^|\s)import\s+{module}|from\s+{module}\s+import", text, re.MULTILINE)
    )


def is_cli_tool(path: Path) -> bool:
    """Determine if a Python file is a runnable CLI tool/script."""
    text = _read_file(path)
    if not text:
        return False
    if "ABOUTME:" in text[:500]:
        return True
    if _has_main_guard(text):
        return True
    if _imports_module(text, "argparse") or _imports_module(text, "click"):
        return True
    return False


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

SKIP_DIRS = (".venv", "site-packages", "node_modules", ".conda", "__pycache__")


def _should_skip(rel_str: str) -> bool:
    return any(skip in rel_str for skip in SKIP_DIRS)


def collect_console_scripts() -> list[ToolEntry]:
    """Parse pyproject.toml for [project.scripts] entries."""
    toml_path = PROJECT_ROOT / "pyproject.toml"
    if not toml_path.exists():
        return []

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    scripts = data.get("project", {}).get("scripts", {})
    entries = []
    for cmd_name, entry_point in scripts.items():
        module_path = entry_point.split(":")[0]
        parts = module_path.split(".")

        # Try src layout first, then flat layout
        file_rel_src = Path("src") / Path(*parts).with_suffix(".py")
        file_rel_flat = Path(*parts).with_suffix(".py")
        file_abs = PROJECT_ROOT / file_rel_src
        if not file_abs.exists():
            file_abs = PROJECT_ROOT / file_rel_flat
            file_rel = file_rel_flat
        else:
            file_rel = file_rel_src

        desc = extract_description(file_abs) if file_abs.exists() else "(module not found)"
        category = _infer_console_script_category(module_path)

        entries.append(
            ToolEntry(
                name=cmd_name,
                location=str(file_rel).replace("\\", "/"),
                command=cmd_name,
                description=desc,
                category=category,
                tool_type="console_script",
            )
        )
    return entries


def collect_scripts_dir() -> list[ToolEntry]:
    """Recursively scan scripts/ for CLI tools."""
    scripts_dir = PROJECT_ROOT / "scripts"
    if not scripts_dir.exists():
        return []

    entries = []
    for py_file in sorted(scripts_dir.rglob("*.py")):
        if py_file.name.startswith("__"):
            continue
        if _should_skip(str(py_file)):
            continue
        if not is_cli_tool(py_file):
            continue

        rel = py_file.relative_to(PROJECT_ROOT)
        rel_posix = str(rel).replace("\\", "/")

        parts = rel.parts
        if len(parts) >= 2 and parts[0] == "scripts":
            raw_cat = parts[1]
            if raw_cat.endswith(".py"):
                raw_cat = "general"
        else:
            raw_cat = "general"
        category = normalize_category(raw_cat)

        internal = py_file.name.startswith("_")
        desc = extract_description(py_file)
        name = py_file.stem.lstrip("_").replace("_", " ").title()
        if internal:
            name = f"_{py_file.stem.lstrip('_')}"

        entries.append(
            ToolEntry(
                name=name,
                location=rel_posix,
                command=f"python {rel_posix}",
                description=desc,
                category=category,
                tool_type="script",
                internal=internal,
            )
        )
    return entries


def collect_module_entries() -> list[ToolEntry]:
    """Find all __main__.py files (module entry points)."""
    entries = []
    for main_file in sorted(PROJECT_ROOT.rglob("__main__.py")):
        rel = main_file.relative_to(PROJECT_ROOT)
        rel_str = str(rel).replace("\\", "/")
        if _should_skip(rel_str):
            continue

        module_dir = main_file.parent
        module_name = str(module_dir.relative_to(PROJECT_ROOT)).replace("\\", ".").replace("/", ".")

        desc = extract_description(main_file)
        top_dir = rel.parts[0] if len(rel.parts) > 1 else "general"
        category = normalize_category(top_dir.replace("_", " "))

        entries.append(
            ToolEntry(
                name=f"python -m {module_name}",
                location=rel_str,
                command=f"python -m {module_name}",
                description=desc,
                category=category,
                tool_type="module_entry",
            )
        )
    return entries


def collect_streamlit_apps() -> list[ToolEntry]:
    """Find Python files that use Streamlit."""
    entries = []
    for py_file in sorted(PROJECT_ROOT.rglob("*.py")):
        rel = py_file.relative_to(PROJECT_ROOT)
        rel_str = str(rel).replace("\\", "/")
        if _should_skip(rel_str):
            continue

        text = _read_file(py_file)
        if not _imports_module(text, "streamlit"):
            continue

        desc = extract_description(py_file)
        top_dir = rel.parts[0] if len(rel.parts) > 1 else "general"
        if top_dir.endswith(".py"):
            category = "Dashboard"
        else:
            category = normalize_category(top_dir.replace("_", " "))

        entries.append(
            ToolEntry(
                name=py_file.stem,
                location=rel_str,
                command=f"streamlit run {rel_str}",
                description=desc,
                category=category,
                tool_type="streamlit",
            )
        )
    return entries


def collect_root_scripts() -> list[ToolEntry]:
    """Find runnable scripts in the project root."""
    entries = []
    for py_file in sorted(PROJECT_ROOT.glob("*.py")):
        if py_file.name.startswith("__") or py_file.name.startswith("."):
            continue

        text = _read_file(py_file)
        if not text:
            continue

        if "ABOUTME:" not in text[:500] and not _has_main_guard(text):
            continue

        desc = extract_description(py_file)
        rel_str = py_file.name

        entries.append(
            ToolEntry(
                name=py_file.stem,
                location=rel_str,
                command=f"python {rel_str}",
                description=desc,
                category="Root",
                tool_type="root_script",
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def deduplicate(entries: list[ToolEntry]) -> list[ToolEntry]:
    """Keep the most specific entry when multiple collectors find the same file."""
    by_location: dict[str, ToolEntry] = {}
    for entry in entries:
        loc = entry.location
        if loc not in by_location or entry.priority < by_location[loc].priority:
            by_location[loc] = entry
    return list(by_location.values())


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def render_markdown(entries: list[ToolEntry]) -> str:
    """Render the tool registry as formatted markdown."""
    console_scripts = sorted(
        [e for e in entries if e.tool_type == "console_script"],
        key=lambda e: e.name,
    )
    other_entries = [e for e in entries if e.tool_type != "console_script"]

    categories: dict[str, list[ToolEntry]] = {}
    for entry in other_entries:
        categories.setdefault(entry.category, []).append(entry)

    for cat in categories:
        categories[cat].sort(key=lambda e: (e.internal, e.name.lower()))

    sorted_cats = sorted(categories.keys())

    total = len(entries)
    cat_count = len(sorted_cats) + (1 if console_scripts else 0)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = []
    lines.append("# Tool Registry")
    lines.append("")
    lines.append(f"> Auto-generated by `scripts/tools/generate_tool_registry.py` on {timestamp}")
    lines.append(f"> Found **{total}** tools across **{cat_count}** categories.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of contents
    lines.append("## Table of Contents")
    lines.append("")
    if console_scripts:
        lines.append(
            "- [Console Scripts (installed CLI commands)](#console-scripts-installed-cli-commands)"
        )
    for cat in sorted_cats:
        anchor = cat.lower().replace(" ", "-").replace("/", "").replace("(", "").replace(")", "")
        lines.append(f"- [{cat}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    if console_scripts:
        lines.append("## Console Scripts (installed CLI commands)")
        lines.append("")
        lines.append(
            "Installed via `pip install -e .` — available as shell commands after activation."
        )
        lines.append("")
        lines.append("| Command | Module | Description |")
        lines.append("|---------|--------|-------------|")
        for e in console_scripts:
            lines.append(f"| `{e.command}` | `{e.location}` | {e.description} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    for cat in sorted_cats:
        cat_entries = categories[cat]
        lines.append(f"## {cat}")
        lines.append("")
        lines.append("| Name | Location | Command | Description |")
        lines.append("|------|----------|---------|-------------|")
        for e in cat_entries:
            loc_display = f"`{e.location}`"
            cmd_display = f"`{e.command}`"
            name_display = f"_{e.name}_" if e.internal else e.name
            lines.append(f"| {name_display} | {loc_display} | {cmd_display} | {e.description} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("Scanning codebase for tools...")

    all_entries: list[ToolEntry] = []

    collectors = [
        ("console scripts (pyproject.toml)", collect_console_scripts),
        ("scripts/ directory", collect_scripts_dir),
        ("module entry points (__main__.py)", collect_module_entries),
        ("Streamlit apps", collect_streamlit_apps),
        ("root-level scripts", collect_root_scripts),
    ]

    for label, collector in collectors:
        try:
            found = collector()
            print(f"  {label}: {len(found)} found")
            all_entries.extend(found)
        except Exception as exc:
            print(f"  {label}: ERROR — {exc}", file=sys.stderr)

    before = len(all_entries)
    all_entries = deduplicate(all_entries)
    deduped = before - len(all_entries)
    if deduped:
        print(f"  Deduplicated: {deduped} duplicates removed")

    md = render_markdown(all_entries)

    out_path = PROJECT_ROOT / "data" / "tool_registry.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    print(f"\nWrote {out_path.relative_to(PROJECT_ROOT)} ({len(all_entries)} tools)")


if __name__ == "__main__":
    main()
