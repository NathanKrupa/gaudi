# Session State — Gaudi

## Last Updated
2026-04-05

## Current Status
Alpha (v0.1.0). Python pack has 42 rules across 3 modules. All other language packs are stubs.
On branch `feat/pypi-rename` (renamed package from `gaudi` to `gaudi-linter` for PyPI).

## What Happened This Session
- Added supply chain security hardening for open-source contributions:
  - `.github/dependabot.yml` — weekly pip + GitHub Actions vulnerability scanning
  - `.github/PULL_REQUEST_TEMPLATE.md` — security review checklist for all PRs
  - `.pre-commit-config.yaml` — ruff, bandit, detect-secrets, large file blocker
  - `.secrets.baseline` — clean baseline for detect-secrets hook
  - `scripts/setup-branch-protection.sh` — one-shot `gh` CLI script for branch protection
- Attempted to harden ci.yml (split into lint/security/test jobs, add bandit + pip-audit + coverage), update CONTRIBUTING.md (security policy), and add dev deps (bandit, pip-audit, pre-commit) to pyproject.toml — these were reverted by the user. The new standalone files above remain.

## Known Blockers
1. ci.yml, CONTRIBUTING.md, pyproject.toml still need security hardening applied (reverted changes need to be re-integrated on the user's terms)
2. Branch protection script exists but hasn't been run yet
3. No negative test cases
4. Library rules use regex on raw text (false positive risk)

## Next Steps
- Re-apply CI hardening, CONTRIBUTING.md security policy, and dev deps when ready
- Run `bash scripts/setup-branch-protection.sh` to activate branch protection
- Merge feat/pypi-rename → main
- Add negative test cases
- Add per-rule documentation
