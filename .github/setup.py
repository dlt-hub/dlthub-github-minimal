# /// script
# requires-python = ">=3.10"
# dependencies = ["dlthub-client>=0.27.7,<1", "httpx"]
# ///
"""One-time setup: connect a repository created from this template to dltHub CI/CD.

    uv run --env-file .env .github/setup.py

Env: DLTHUB_API_KEY (required): a user-level key, belonging to a single organization.
"""
import json
import os
import subprocess
import sys

import dlthub_sdk
import httpx

KEY = os.environ.get("DLTHUB_API_KEY") or sys.exit("setup failed: set DLTHUB_API_KEY")


def run(*cmd: str, input: str | None = None, check: bool = True) -> str:
    r = subprocess.run(cmd, input=input, text=True, capture_output=True)
    if check and r.returncode:
        sys.exit(f"setup failed: {' '.join(cmd[:3])}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip() if r.returncode == 0 else ""


def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def check_tools():
    for tool in ("git", "gh", "uvx"):
        run(tool, "--version")


def main():
    check_tools()
        
    repo = run("gh", "repo", "view", "--json", "nameWithOwner,defaultBranchRef")
    repo = json.loads(repo)
    slug, branch = repo["nameWithOwner"], repo["defaultBranchRef"]["name"]
    os.environ["GH_REPO"] = slug
    print(f"Repository: {slug}")

    step("scaffolding the project (uvx dlthub-init)")
    subprocess.run(["uvx", "dlthub-init@latest", "--merge", "--no-telemetry", "."], check=True)

    step("dltHub workspace")
    with dlthub_sdk.connect(token=KEY) as rt:
        orgs = list(rt.organizations.list())
        if len(orgs) != 1:
            sys.exit(f"setup failed: the key belongs to {len(orgs)} organizations; expected exactly 1")
        org_id = orgs[0].id
        taken = {w.name for w in rt.workspaces.list(organization_id=org_id)}
        base = slug.split("/")[1]
        name, i = base, 1
        while name in taken:  # rename it later in the dashboard
            i += 1
            name = f"{base}-{i}"
        ws = rt.workspaces.create(name=name, description="Deployed by GitHub Actions", organization_id=org_id)
        print(f"created workspace {name}")

    # Workspace-scoped key for CI (no SDK method yet: plain REST call). `owner` is refused; 365 days is the max.
    resp = httpx.post(
        f"{dlthub_sdk._DEFAULT_BASE_URL.rstrip('/')}/api/v1/workspaces/{ws.id}/api-keys",
        headers={"Authorization": f"Bearer {KEY}"},
        json={"name": f"github-actions-{name}", "role": "developer", "expires_in_days": 365},
        timeout=30,
    )
    if resp.is_error:
        sys.exit(f"setup failed: could not create a workspace API key: HTTP {resp.status_code} {resp.text[:200]}")
    ci_key = resp.json()["key"]
    print("created a workspace API key for CI (developer, 365 days)")

    step("GitHub configuration")
    run("gh", "secret", "set", "DLTHUB_API_KEY", input=ci_key)
    run("gh", "variable", "set", "DLTHUB_WORKSPACE_ID", "--body", ws.id)
    run("gh", "variable", "set", "DLTHUB_ORGANIZATION_ID", "--body", org_id)

    step("pushing the project (starts the production deploy)")
    run("git", "add", "--all")
    run("git", "commit", "--quiet", "-m", "Add dltHub project and CI/CD")
    run("git", "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}")

    print(f"\nDone. Workspace '{name}' (rename it in the dashboard if you like).")
    print(f"Deploy: https://github.com/{slug}/actions")


if __name__ == "__main__":
    main()
