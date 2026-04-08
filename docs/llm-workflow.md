# LLM-collaborative workflow

Gaudi's rules are mostly judgment calls — architecture, thresholds, naming,
design smells. They are *not* the kind of finding that should be auto-fixed by
a bot opening dozens of PRs. The right unit of work is not "apply patch N" but
"developer and LLM agree on what to do about finding N."

Gaudi gives you two outputs designed for that workflow:

1. **GitHub Actions annotations** — show findings inline on PRs.
2. **`gaudi report`** — generate a Markdown briefing for an LLM conversation.

## 1. GitHub Actions annotations

Add `--format github` to `gaudi check` and the output becomes
[GitHub Actions workflow commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-error-message).
Each finding becomes an inline annotation on the relevant file/line in the
PR's *Files changed* view, with severity mapped to GitHub's three levels:

| Gaudi severity | GitHub annotation |
|----------------|-------------------|
| `error`        | `::error`         |
| `warn`         | `::warning`       |
| `info`         | `::notice`        |

### Sample workflow

Drop the following into `.github/workflows/gaudi.yml` of any Python repo:

```yaml
name: Gaudi

on:
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: read

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install Gaudi
        run: pip install gaudi-linter

      - name: Architecture check
        run: gaudi check . --format github
```

That's it. No bot account, no PR-creation permissions, no patch generation.
Findings appear exactly where reviewers already look.

If you want CI to *fail* on errors (rather than just annotate), add a second
step that runs the same check with `--severity error --exit-code`. Keep it
separate so the annotation step always runs even when the gating step fails.

## 2. `gaudi report` for LLM conversations

`gaudi report` generates a Markdown briefing designed to be the opening move
in a chat with an LLM:

```bash
gaudi report . --output gaudi-report.md
```

The report is grouped **by file**, not by rule, because the natural unit of an
LLM conversation is "let's look at this file together" — not "let's fix all
instances of rule X across the repo."

Each finding includes:

- Rule code, severity, category
- A clickable link to the offending file and line
- A code snippet with surrounding context
- The rule's recommendation
- A pre-written **"Discuss with LLM"** prompt the developer can paste straight
  into Claude, ChatGPT, or any other assistant

A typical loop looks like:

1. Run `gaudi report .` locally (or download the artifact from CI).
2. Open the report next to your editor.
3. For each finding you care about, copy the discussion prompt into your
   assistant of choice and ask it to propose a fix — *without* applying it
   yet, so you see the diff first.
4. Decide what to do. Apply the fix, or mark it `# noqa: gaudi(<CODE>)` if you
   judge that the rule doesn't apply here.

## Why no auto-PRs

The obvious "scan and open a PR per finding" workflow is deliberately not
implemented. Two reasons:

1. **Blast radius.** A tool that opens dozens of PRs against someone else's
   repo is antisocial, and most Gaudi rules have no deterministic fix — only a
   judgment call.
2. **Wrong abstraction.** Gaudi is an LLM-adjacent tool. The interesting unit
   of work is the conversation, not the patch. The annotations and the report
   make that conversation cheap to start; that's the contribution.
