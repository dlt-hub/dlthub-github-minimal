#!/usr/bin/env bash
# One-time setup for a repository created from this GitHub template: connect it to dltHub CI/CD.
# Run from a clone of that repository, logged in with `gh auth login` (admin on the repo):
#
#   DLTHUB_API_KEY=dlt_u_... bash .github/setup.sh
#
# Inputs
#   DLTHUB_API_KEY          dltHub API key (required)
#   DLTHUB_ORGANIZATION_ID  only if the key belongs to more than one organization
#   DLTHUB_CI_API_KEY       optional workspace-scoped key (dlt_sa_...) for CI, from the dashboard.
#                           If unset, DLTHUB_API_KEY itself is stored in GitHub for CI.
#   DLTHUB_SECRETS_JSON     optional runtime secrets stored on the workspace (profile `prod`)
#
# Steps
#   1. `uvx dlthub-init@latest` scaffolds the project files (__deployment__.py, pyproject.toml,
#      uv.lock, .dlt/, .mcp.json) and up-to-date skills (.agents/skills/); existing files are kept
#   2. the repository is read from `gh`; .github/dlthub_setup.py creates the dltHub
#      workspace named after it (suffix -2, -3, ... on a name collision)
#   3. gh: environment `production` (default branch only), secret DLTHUB_API_KEY, variables
#      DLTHUB_WORKSPACE_ID / DLTHUB_ORGANIZATION_ID, ruleset on the default branch
#   4. commits the scaffold and pushes it; the push runs the first production deploy
# Requires: git, gh, uv (uvx). Safe to re-run (reuses the workspace recorded in DLTHUB_WORKSPACE_ID).
set -euo pipefail

[[ -n "${DLTHUB_API_KEY:-}" ]] || { echo "setup failed: set DLTHUB_API_KEY" >&2; exit 2; }
for c in git gh uv; do command -v "$c" >/dev/null || { echo "setup failed: $c not found" >&2; exit 2; }; done
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
export GH_PROMPT_DISABLED=1
gh auth status >/dev/null 2>&1 || { echo "setup failed: run 'gh auth login' first" >&2; exit 2; }
repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" \
  || { echo "setup failed: run from a clone of your GitHub repository" >&2; exit 2; }
branch="$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)"
export GH_REPO="$repo"
env_name=production
echo "Repository: $repo"

echo "[1/4] scaffolding the project (uvx dlthub-init@latest)"
uvx dlthub-init@latest --merge --no-telemetry .

echo "[2/4] dltHub workspace"
existing="$(gh variable get DLTHUB_WORKSPACE_ID --env "$env_name" 2>/dev/null || true)"
info="$(WORKSPACE_NAME="${repo#*/}" EXISTING_WORKSPACE_ID="$existing" \
  uv run --quiet python .github/dlthub_setup.py)"
field() { printf '%s' "$info" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
ws_id="$(field workspace_id)"; org_id="$(field organization_id)"; ws_name="$(field name)"

echo "[3/4] GitHub configuration"
gh api -X PUT "repos/$repo/environments/$env_name" --input - >/dev/null <<'JSON'
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
# only the default branch may deploy (fails harmlessly if the policy already exists)
gh api -X POST "repos/$repo/environments/$env_name/deployment-branch-policies" \
  -f name="$branch" -f type=branch >/dev/null 2>&1 || true
printf '%s' "${DLTHUB_CI_API_KEY:-$DLTHUB_API_KEY}" | gh secret set DLTHUB_API_KEY --env "$env_name"
gh variable set DLTHUB_WORKSPACE_ID --env "$env_name" --body "$ws_id"
gh variable set DLTHUB_ORGANIZATION_ID --env "$env_name" --body "$org_id"

# The default branch changes only through PRs that pass `code-quality`; admins may bypass.
ruleset='{"name":"main","target":"branch","enforcement":"active",
  "conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},
  "bypass_actors":[{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"always"}],
  "rules":[{"type":"deletion"},{"type":"non_fast_forward"},
    {"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},
    {"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,"required_status_checks":[{"context":"code-quality"}]}}]}'
rid="$(gh api "repos/$repo/rulesets" --jq '.[] | select(.name=="main") | .id' | head -n1)"
if [[ -n "$rid" ]]; then
  printf '%s' "$ruleset" | gh api -X PUT "repos/$repo/rulesets/$rid" --input - >/dev/null
else
  printf '%s' "$ruleset" | gh api -X POST "repos/$repo/rulesets" --input - >/dev/null
fi

echo "[4/4] pushing the project (starts the production deploy)"
git add --all
if ! git diff --cached --quiet; then
  git commit --quiet -m "Add dltHub project and CI/CD"
  git push --quiet origin "HEAD:refs/heads/$branch"   # admins bypass the ruleset
else
  gh workflow run deploy.yaml --ref "$branch"           # nothing new: just redeploy
fi

echo
echo "Done. Workspace '$ws_name' (rename it in the dashboard if you like)."
echo "Deploy: https://github.com/$repo/actions"
