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
if [ -d "$wt/src" ]; then
    pp='$PWD/src'
else
    pp='$PWD'
fi
printf 'export PYTHONPATH="%s"\n' "$pp" >"$wt/.envrc"

cat <<EOF

  Worktree:  $wt
  Branch:    $branch  (from $base)

  Start Claude Code IN that directory, with the shared venv + isolated source:

      cd "$wt"
      export PYTHONPATH="$(eval echo "$pp")"
      # launch Claude Code here

  (direnv users: a .envrc was written — run 'direnv allow'.)
  (uv repos: run tools as .venv/bin/<tool> in the worktree — not 'uv run',
   which may re-sync the shared venv.)

  When done: open a PR from '$branch', then  git worktree remove "$wt"
EOF
