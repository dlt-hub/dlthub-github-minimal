"""dltHub side of .github/setup.sh: ensure the production workspace and its secrets.

Env in:  DLTHUB_API_KEY, WORKSPACE_NAME (the GitHub repo name),
         optional DLTHUB_ORGANIZATION_ID (required if the key belongs to several orgs),
         optional EXISTING_WORKSPACE_ID (from a previous run: reused if it still exists),
         optional DLTHUB_SECRETS_JSON (runtime secrets, profile `prod`).
Stdout:  one JSON line {"workspace_id", "organization_id", "name"}; logs go to stderr.
Name collisions: `name`, then `name-2`, `name-3`, ... Rename it later in the dashboard.
"""
import json
import os
import sys

import dlthub_sdk

PROFILE = "prod"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def pick_org(rt) -> str:
    if os.environ.get("DLTHUB_ORGANIZATION_ID"):
        return os.environ["DLTHUB_ORGANIZATION_ID"]
    orgs = list(rt.organizations.list())
    if len(orgs) != 1:
        sys.exit(f"found {len(orgs)} organizations; set DLTHUB_ORGANIZATION_ID")
    return orgs[0].id


def unique_name(base: str, taken: set[str]) -> str:
    name, i = base, 1
    while name in taken:
        i += 1
        name = f"{base}-{i}"
    return name


with dlthub_sdk.connect(token=os.environ["DLTHUB_API_KEY"]) as rt:
    org_id = pick_org(rt)
    ws = None
    if os.environ.get("EXISTING_WORKSPACE_ID"):
        try:
            ws = rt.workspaces.get(id=os.environ["EXISTING_WORKSPACE_ID"])
            ws = None if ws.archived_at else ws
        except dlthub_sdk.NotFound:
            ws = None
    if ws is None:
        taken = {w.name for w in rt.workspaces.list(organization_id=org_id)}
        name = unique_name(os.environ["WORKSPACE_NAME"], taken)
        ws = rt.workspaces.create(
            name=name, description="Deployed by GitHub Actions", organization_id=org_id
        )
        log(f"created workspace {name}")
    else:
        log(f"reusing workspace {ws.name}")
    secrets = json.loads(os.environ.get("DLTHUB_SECRETS_JSON") or "{}")
    if secrets:
        rt.workspaces.get(id=ws.id).variables.apply(profile=PROFILE, secrets=secrets)
        log(f"stored {len(secrets)} secret(s) in profile {PROFILE}")
    print(json.dumps({"workspace_id": ws.id, "organization_id": org_id, "name": ws.name}))
