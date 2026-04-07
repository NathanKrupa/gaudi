# Gaudí Test Fixture Corpus

## Purpose

Every rule in Gaudí needs proof that it works — proof it catches what it should, and proof it leaves clean code alone. This document defines the structure, conventions, and workflow for the **test fixture corpus**: a body of deliberately crafted code samples used to validate every rule in the engine.

The principle is simple: **if a rule has no fixture, it has no evidence.**

---

## Directory Structure

```
tests/
└── fixtures/
    ├── python/
    │   ├── PY-001/
    │   │   ├── fail_god_class.py
    │   │   ├── fail_god_class_boundary.py
    │   │   ├── pass_clean_class.py
    │   │   └── expected.json
    │   ├── PY-002/
    │   │   ├── fail_circular_import.py
    │   │   ├── fail_circular_import_indirect.py
    │   │   ├── pass_clean_imports.py
    │   │   └── expected.json
    │   └── ...
    ├── python314/
    │   ├── PY314-001/
    │   │   ├── fail_deprecated_usage.py
    │   │   ├── pass_modern_usage.py
    │   │   └── expected.json
    │   └── ...
    ├── gauntlet/
    │   ├── python_gauntlet_01.py
    │   ├── python_gauntlet_01_expected.json
    │   ├── python_gauntlet_02.py
    │   ├── python_gauntlet_02_expected.json
    │   └── ...
    └── README.md  (symlink or copy of this file)
```

### Key directories

| Directory | Contents |
|---|---|
| `fixtures/<language>/<RULE-ID>/` | Per-rule pass/fail files and expected output |
| `fixtures/gauntlet/` | Multi-violation composite files that stress-test the engine |

---

## Fixture Types

### 1. Fail Files (`fail_*.py`)

Code that **must** trigger the rule. Each file should contain exactly one category of violation (though it may contain multiple instances of that violation).

Naming pattern: `fail_<description>.py`

Examples:
- `fail_god_class.py` — a class with too many methods/responsibilities
- `fail_god_class_boundary.py` — a class at exactly threshold + 1 (edge case)
- `fail_circular_import_indirect.py` — a three-module circular dependency

### 2. Pass Files (`pass_*.py`)

Code that **must not** trigger the rule. This is equally important — a rule that fires on clean code is worse than no rule at all.

Naming pattern: `pass_<description>.py`

Examples:
- `pass_clean_class.py` — a well-structured class just under any thresholds
- `pass_clean_imports.py` — correct, acyclic import structure

### 3. Boundary Files

A special case of fail/pass files that sit right at a rule's threshold. If a rule triggers at > 10 methods, you need:
- `pass_boundary_10_methods.py` — exactly 10 methods (should pass)
- `fail_boundary_11_methods.py` — exactly 11 methods (should fail)

### 4. Multi-file Fixtures (`fail_*/`, `pass_*/`)

Some rules are inherently cross-file: alembic head divergence, layering rules,
circular imports, and most architecture rules can only be exercised by a small
project tree, not a single file. For these, a fixture is a **directory** rather
than a `.py` file.

```
ALM-OPS-001/
├── fail_branched_heads/
│   └── alembic/versions/
│       ├── 001_a.py
│       └── 001_b.py
├── pass_linear_chain/
│   └── alembic/versions/
│       ├── 001_a.py
│       └── 002_c.py
└── expected.json
```

When the runner executes a directory fixture, it copies the directory's
**contents** (not the directory itself) into the temp project root, preserving
subdirectories. So `fail_branched_heads/alembic/versions/001_a.py` lands at
`<tmp>/alembic/versions/001_a.py` exactly as a real project would lay it out.

The `expected.json` key for a directory fixture is the directory name (with or
without a trailing slash). Findings are matched the same way as single-file
fixtures — by severity, optional line, and message substring — and the runner
already tolerates findings arriving in any order.

A single rule directory may freely mix single-file and multi-file fixtures.

### 5. Expected Output (`expected.json`)

Each rule directory contains an `expected.json` that declares the findings the engine should produce for each fixture file. This is the **assertion source** for automated tests.

```json
{
  "rule_id": "PY-001",
  "fixtures": {
    "fail_god_class.py": {
      "expected_findings": [
        {
          "severity": "warning",
          "line": 5,
          "message_contains": "exceeds maximum method count"
        }
      ]
    },
    "fail_god_class_boundary.py": {
      "expected_findings": [
        {
          "severity": "warning",
          "line": 3,
          "message_contains": "exceeds maximum method count"
        }
      ]
    },
    "pass_clean_class.py": {
      "expected_findings": []
    }
  }
}
```

### 6. Gauntlet Files

Composite files containing **multiple violations across multiple rules**. These verify:
- Rules do not interfere with each other
- The engine reports **all** findings, not just the first
- Finding locations remain accurate when violations are stacked
- Performance remains acceptable under load

Each gauntlet file has a companion `*_expected.json` with findings from all applicable rules.

---

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Rule directory | `<RULE-ID>/` | `PY-001/`, `PY314-003/` |
| Fail fixture (file) | `fail_<snake_case_description>.py` | `fail_god_class.py` |
| Pass fixture (file) | `pass_<snake_case_description>.py` | `pass_clean_class.py` |
| Fail fixture (multi-file) | `fail_<snake_case_description>/` | `fail_branched_heads/` |
| Pass fixture (multi-file) | `pass_<snake_case_description>/` | `pass_linear_chain/` |
| Boundary fixture | `fail_boundary_<detail>.py` / `pass_boundary_<detail>.py` | `fail_boundary_11_methods.py` |
| Expected output | `expected.json` | — |
| Gauntlet file | `<language>_gauntlet_<nn>.py` | `python_gauntlet_01.py` |
| Gauntlet expected | `<language>_gauntlet_<nn>_expected.json` | `python_gauntlet_01_expected.json` |

---

## Workflow: Rule-Driven TDD

Adding a new rule follows this sequence:

```
1. Write the fixture FIRST
   ├── Create the rule directory: tests/fixtures/<lang>/<RULE-ID>/
   ├── Write fail_*.py with the violation
   ├── Write pass_*.py with clean code
   └── Write expected.json with anticipated findings

2. Run the test suite — confirm the new fixtures FAIL
   (The rule doesn't exist yet, so no findings are produced)

3. Implement the rule

4. Run the test suite — confirm the new fixtures PASS
   (The rule now produces exactly the expected findings)

5. Add a case to an existing gauntlet file (or create a new one)
   └── Update the gauntlet's expected.json
```

This is red-green-refactor applied to architectural analysis. The fixture is the specification; the rule is the implementation.

---

## Test Runner Integration

The test suite should include a parametrized test that:

1. Discovers all rule directories under `tests/fixtures/`
2. For each rule directory, loads `expected.json`
3. Runs the engine against each fixture file with only that rule enabled
4. Asserts that actual findings match expected findings (count, severity, approximate line, message substring)

Pseudocode:

```python
@pytest.mark.parametrize("rule_dir", discover_fixture_dirs())
def test_rule_fixtures(rule_dir):
    expected = load_expected(rule_dir / "expected.json")
    rule_id = expected["rule_id"]

    for filename, spec in expected["fixtures"].items():
        filepath = rule_dir / filename
        findings = engine.analyze(filepath, rules=[rule_id])

        assert len(findings) == len(spec["expected_findings"])
        for finding, expectation in zip(findings, spec["expected_findings"]):
            assert finding.severity == expectation["severity"]
            assert expectation["message_contains"] in finding.message
            if "line" in expectation:
                assert finding.line == expectation["line"]
```

---

## Coverage Tracking

Maintain a simple coverage table (can be auto-generated by CI):

| Rule ID | Fail Fixtures | Pass Fixtures | Boundary | In Gauntlet |
|---|---|---|---|---|
| PY-001 | 2 | 1 | ✓ | ✓ |
| PY-002 | 2 | 1 | — | ✓ |
| PY314-001 | 1 | 1 | — | — |

**Minimum per rule:** 1 fail file, 1 pass file, 1 expected.json. Boundary and gauntlet coverage are strongly recommended but not blocking.

---

## Principles

1. **Fixtures are specifications.** If you can't write the broken code, you don't understand the rule well enough to implement it.
2. **False positives are worse than false negatives.** Every rule needs pass files. A noisy linter gets disabled.
3. **Edge cases are where trust is built.** Boundary files prove the rule is precise, not approximate.
4. **Gauntlets prove the system.** Individual rule tests prove components; gauntlets prove the engine.
5. **The fixture comes first.** Always. No exceptions.
