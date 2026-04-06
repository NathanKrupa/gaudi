# Migrating from Master Todo to PR-Structured Workflow

A guide for converting projects that track work via a master todo list
into projects where **pull requests are the task board**.

---

## The Core Idea

A PR is not just a code review mechanism. It is a **unit of planned work**
that declares scope, collects evidence, and closes with verification.

| Master Todo concept | PR equivalent |
|---|---|
| Task description | PR title + body |
| Subtasks / checklist | Commits within the PR |
| "In progress" | Open / draft PR |
| "Done" | Merged PR |
| "Blocked" | PR with failing checks or unresolved comments |
| Task priority | PR labels or milestone |
| Task assignment | PR assignee / CODEOWNERS |

The PR list **is** the project's living task board. `gh pr list` replaces
checking a todo file.

---

## Migration Steps

### 1. Set Up Branch Protection (5 minutes)

Enforce that all changes flow through PRs:

```bash
gh api repos/OWNER/REPO/branches/main/protection -X PUT --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "test"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0
  },
  "restrictions": null
}
EOF
```

Key settings:
- **`enforce_admins: true`** -- no `--admin` bypass, even for repo owners
- **`strict: true`** -- branch must be up to date before merge
- Adjust `contexts` to match your CI job names

### 2. Add PR Template (5 minutes)

Create `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## Summary

<!-- What does this PR do? 1-3 bullet points. -->

## Motivation

<!-- Why is this change needed? Link to issue if applicable. -->

## Test plan

<!-- How did you verify this works? -->
```

This ensures every PR has a scope declaration and verification plan.

### 3. Add CODEOWNERS (2 minutes)

Create `.github/CODEOWNERS`:

```
# Default owner
* @your-username

# Sensitive paths require explicit review
.github/ @your-username
```

### 4. Add Contributing Guide (10 minutes)

Document the workflow in `CONTRIBUTING.md`:

```markdown
## Workflow

1. Create a branch: `git checkout -b feat/short-description`
2. Open a draft PR with scope description
3. Do the work, commit, push
4. Mark PR as ready when scope is complete
5. Wait for CI, then merge
```

### 5. Convert Existing Todo Items to Issues/PRs (varies)

For each item in your master todo:

1. **Create a GitHub issue** with the task description
2. **When starting work**, create a branch and draft PR referencing the issue
3. **When done**, mark the PR ready and merge
4. The issue auto-closes via "Fixes #N" in the PR body

For items that are pure planning (not actionable yet), use GitHub Issues
with labels like `planning` or `future`.

### 6. Add CI Instructions to CLAUDE.md (if using Claude Code)

```markdown
## PR Workflow

**Scope check before starting work:** Before writing code, state:
(a) the branch name, (b) the PR title, (c) 1-3 bullet scope description.
If scope grows beyond the original description, stop and split.

**Never commit directly to main.** Branch protection enforces this.
**Never use `--admin` to bypass CI.** Wait for checks.
**One PR = one logical change.**
```

---

## The Discipline Rule

The single rule that prevents scope drift:

> **Define the PR before doing the work, not after.**

Write the PR description first. It is a contract. If your implementation
outgrows the contract, you have found a scope problem -- split the PR,
don't expand it.

This is the same principle as TDD: write the test (PR scope) before the
implementation (commits). If the implementation outgrows the test, the
scope was wrong.

---

## Verification

After migration, these should be true:

- [ ] `git push origin main` is rejected (branch protection)
- [ ] Every merged PR has a summary and test plan (template)
- [ ] `gh pr list --state merged` shows your project history as discrete units
- [ ] No PR changes more than one logical concern
- [ ] CI passes before every merge (no `--admin` bypass)

---

## Tools

| Need | Tool |
|---|---|
| List open work | `gh pr list` |
| List completed work | `gh pr list --state merged` |
| Check CI status | `gh pr checks N` |
| Create scoped work | `gh pr create --draft --title "..." --body "..."` |
| Enforce structure | Branch protection + PR template |
| Detect missing scaffolding | Gaudi rules OPS-003, OPS-004, OPS-005 |
