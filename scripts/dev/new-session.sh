#!/usr/bin/env bash
# ABOUTME: Create an isolated session worktree so parallel agents never share the main tree.
# ABOUTME: Canonical (OverSteward shared/scripts/dev/); self-adapting — deployed byte-identical to every repo.
set -euo pipefail

name="${1:-}"
if [ -z "$name" ]; then
    echo "usage: scripts/dev/new-session.sh <name> [base-ref]" >&2
    echo "  creates .claude/worktrees/<name> on branch session/<name>" >&2
    echo "  base-ref defaults to origin/staging if it exists, else the default branch" >&2
    exit 2
fi

# Must run from the PRIMARY worktree (linked worktrees nest under .git/worktrees/).
git_dir="$(git rev-parse --git-dir 2>/dev/null || true)"
case "$git_dir" in
    "") echo "Not inside a git repository." >&2; exit 1 ;;
    *worktrees/*) echo "Run this from the main worktree, not a linked one." >&2; exit 1 ;;
esac

root="$(git rev-parse --show-toplevel)"

# A shallow clone causes "refusing to merge unrelated histories" on back-merge
# and grafted/orphan branches that aren't worth repairing. Unshallow first.
if [ "$(git -C "$root" rev-parse --is-shallow-repository)" = "true" ]; then
    echo "Shallow checkout detected — unshallowing (git fetch --unshallow)..." >&2
    git -C "$root" fetch --unshallow --quiet
fi
git -C "$root" fetch origin --quiet

# Base ref: explicit arg wins; else origin/staging if it exists (GS/AG model);
# else the remote's default branch (main/master for trunk-only repos).
base="${2:-}"
if [ -z "$base" ]; then
    if git -C "$root" rev-parse --verify --quiet origin/staging >/dev/null; then
        base="origin/staging"
    else
        default="$(git -C "$root" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/@@')"
        base="${default:-origin/main}"
    fi
fi

wt="$root/.claude/worktrees/$name"
branch="session/$name"
if [ -e "$wt" ]; then
    echo "Worktree already exists: $wt" >&2
    exit 1
fi

# git worktree add is not a branch checkout/switch, so the guard hook allows it;
# the override prefix is belt-and-braces.
CLAUDE_ALLOW_MAIN_GIT=1 git -C "$root" worktree add "$wt" -b "$branch" "$base"

# Share the single venv (deps live there). PYTHONPATH makes the project import
# resolve to THIS worktree's source, overriding the editable install's .pth that
# points at the main tree — verified: editable installs are path-based here
# (pip and uv alike), so PYTHONPATH wins. src/ layout → src; flat/Django → root.
if [ -d "$root/.venv" ]; then
    ln -sfn "$root/.venv" "$wt/.venv"
fi
# Two forms of the same path, because the consumers expand at different times.
# .envrc gets the literal '$PWD/src' — direnv expands it inside the worktree.
# The printed instruction is copy-pasted by a human whose shell is elsewhere, so
# it must carry the worktree-absolute path already resolved.
if [ -d "$wt/src" ]; then
    pp='$PWD/src'
    pp_display="$wt/src"
else
    pp='$PWD'
    pp_display="$wt"
fi
{
    printf 'export PYTHONPATH="%s"\n' "$pp"
    # PYTHONPATH isolates THIS worktree's imports and does nothing for the
    # PRIMARY checkout, which is the half that actually breaks: `uv run` syncs
    # the project environment before running anything, and that sync rebinds the
    # SHARED venv's editable install to whichever tree invoked it. One `uv run`
    # here leaves the primary — and every sibling worktree on this symlink —
    # importing this branch's source. UV_NO_SYNC turns the sync off, so ordinary
    # work never has to reach for the guard's override.
    if [ -L "$wt/.venv" ]; then
        printf 'export UV_NO_SYNC=1\n'
    fi
} >"$wt/.envrc"

# The banner is one heredoc, so the shared-venv paragraph is built here and
# expanded empty when this worktree owns its venv outright.
shared_venv_note=""
if [ -L "$wt/.venv" ]; then
    shared_venv_note="  (shared .venv: this worktree borrows another tree's environment. Bare
   'uv run' would re-sync it and rebind it here, so the guard_shared_venv hook
   refuses it — prefer .venv/bin/<tool>, which never syncs. The .envrc above
   exports UV_NO_SYNC=1; without direnv, export it yourself.)"
fi

cat <<EOF

  Worktree:  $wt
  Branch:    $branch  (from $base)

  Start Claude Code IN that directory, with the shared venv + isolated source:

      cd "$wt"
      export PYTHONPATH="$pp_display"
      # launch Claude Code here

  Then CONFIRM the package resolves to this worktree, not the primary tree —
  without it every gate silently validates the wrong source:

      python scripts/dev/check_worktree_imports.py <your-package>

  (direnv users: a .envrc was written — run 'direnv allow'.)
$shared_venv_note

  When done: open a PR from '$branch', then tear down THROUGH the doctor —
  a shared venv or a docker compose project may have captured this path, and
  removing it blind breaks every checkout on that venv. The doctor also drops
  the test database this worktree owns, which nothing else will:

      scripts/dev/worktree_doctor.py teardown "$wt"
EOF
