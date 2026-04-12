# Session State — Gaudi

## Last Updated
2026-04-12 (Phase 3 polish complete — attribution + inference + RFC cleanup)

## Current Status
Alpha (v0.1.1). Python-only architecture linter.
~124 implemented rules, 23 scoped to specific schools, ~101 universal.
**Phase 0:** 8/8 reference exemplars complete.
**Phase 1:** Engine complete (Rule.philosophy_scope + gaudi.toml filtering).
**Phase 2:** 8/9 detector precision fixes shipped.
**Phase 3:** CLI polish shipped — attribution in output, philosophy
inference command, RFC file archived to docs/.

Test suite: **743 passed**. Ruff clean.

---

## What Changed This Session

Two sessions of work: Phase 2 detector precision fixes (PRs #173-#177)
and Phase 3 CLI polish (PRs #178-#180).

### Phase 2 — Detector precision (PRs #173-#177)

8 of 9 documented false positives resolved across 4 rule PRs:

| PR | Rules | Fix |
|---|---|---|
| #173 | DOM-001, STAB-001 | Manager awareness; chain-terminal methods |
| #174 | DOM-001, DJ-SEC-001, SEC-003 | Generic Manager types; test-placeholder detection |
| #175 | SCHEMA-001, SEC-001 | Reference-data exemption; security-sensitive models only |
| #176 | SMELL-007, SMELL-023 | Init-injected dep exemption; Protocol awareness |

Convention exemplar: 39 → 25 findings (14 false positives eliminated).
Classical exemplar: SMELL-007 + SMELL-023 false positives gone.

### Phase 3 — CLI polish (PRs #178-#180)

| PR | Feature |
|---|---|
| #178 | **Philosophy attribution** — scoped rules show `(classical, convention)` in all output formats (text, JSON, GitHub, Markdown). Universal rules show no tag. |
| #179 | **`gaudi philosophy` command** — infers school from project dependencies and structure. Analyzes pyproject.toml/requirements.txt for framework signals (django→convention, numpy→data-oriented, etc.) and project structure (models.py+admin.py, Protocol classes, shell scripts). Outputs ranked schools with evidence. |
| #180 | **RFC file archived** — moved `gaudi-architectural-philosophies.md` from repo root to `docs/`. |

---

## Phase Roadmap

### Phase 0 — reference exemplars (COMPLETE)
### Phase 1 — engine change (COMPLETE)
### Phase 2 — detector precision (COMPLETE)
### Phase 3 — CLI polish (COMPLETE)

- [x] Attribution in output (#178)
- [x] `gaudi philosophy` inference (#179)
- [x] RFC file archived (#180)
- [ ] Website audit (deferred — needs Nathan's Django site)

### Phase 4 — next candidates

- **Website audit**: run `gaudi check` against Nathan's real Django
  website, categorize findings, surface audit gaps
- **Severity overrides wiring**: gaudi.toml `[gaudi.rules]` section
  is loaded but not applied to engine findings
- **noqa support**: inline `# noqa: RULE-ID` comments to suppress
  specific findings
- **Rule documentation**: auto-generated docs page per rule with
  examples, fixtures, and philosophy scope

---

## Things To Know Before Next Session

1. **PRs merged this session (8 total):**
   #173-#177 (Phase 2), #178-#180 (Phase 3)

2. **Python environment**: Oversteward conda env's pip resolves to
   ai-assistants. Use `conda run -n Oversteward python -m pip install`
   for packages. Editable install refreshed this session.

3. **Philosophy attribution is live.** Running `gaudi check` now shows
   `(classical, convention)` for scoped rules. The `gaudi philosophy`
   command can recommend a school for any Python project.

4. **The RFC file** now lives at `docs/gaudi-architectural-philosophies.md`.
   The repo root is clean (no untracked files).

5. **No open PRs.** All work is merged to main.

---

## Test Suite / Build Status

- `ruff check .` — clean
- `ruff format --check .` — clean
- `pytest --tb=short -q` — **743 passed**
- CI: every PR merged green without `--admin`

---

## Commits Landed (this session, in order)

```
d3c843b docs: move RFC file to docs/ (#180)
f92f4d7 feat(cli): gaudi philosophy command for school inference (#179)
0e08dbb feat(cli): philosophy attribution in findings output (#178)
260f375 chore(session): update SESSION_STATE for Phase 2 completion (8/9) (#177)
687b3d2 fix(rules): SMELL-007 injected-dep exemption + SMELL-023 Protocol awareness (#176)
502cab5 fix(rules): SCHEMA-001 reference-data exemption + SEC-001 sensitive-models-only (#175)
26252ad fix(rules): DOM-001 generic Manager + DJ-SEC-001/SEC-003 test placeholders (#174)
9bade4b fix(rules): DOM-001 Manager awareness + STAB-001 chain-terminal handling (#173)
```

Branch tip: `main`. No open PRs. No uncommitted changes.
