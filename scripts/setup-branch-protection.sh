#!/usr/bin/env bash
# ABOUTME: Configures GitHub branch protection rules for the main branch.
# ABOUTME: Requires the `gh` CLI authenticated with admin access.

set -euo pipefail

REPO="NathanKrupa/gaudi"
BRANCH="main"

echo "Configuring branch protection for $REPO ($BRANCH)..."

gh api \
  --method PUT \
  "repos/$REPO/branches/$BRANCH/protection" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "security", "test (3.10)", "test (3.11)", "test (3.12)", "test (3.13)"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": false,
  "required_conversation_resolution": true
}
EOF

echo "Branch protection configured successfully."
echo ""
echo "Rules applied:"
echo "  - PRs required (1 approving review)"
echo "  - Stale reviews dismissed on new pushes"
echo "  - All CI checks must pass (lint, security, test matrix)"
echo "  - Status checks must be up-to-date before merge"
echo "  - Force pushes and branch deletion blocked"
echo "  - Conversations must be resolved before merge"
