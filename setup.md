# Setup: connect this repository to dltHub (CI/CD)

Instructions for an agent (or a human). Goal: run `setup.py` once. It
creates a new GitHub repository from the template, copies it locally, scaffolds the project (`uvx dlthub-init@latest`),
creates a dltHub workspace named after the repo, creates a workspace-scoped API key for CI,
configures GitHub, and pushes, which starts the first production deploy. Afterwards, merging to
`main` deploys. Follow the steps in order; do not improvise.

This minimal setup works on a free GitHub plan (private or public): it uses repository-level secrets and variables, with no environments, rulesets or branch protection.

Setup is meant to run **once, from scratch** (new GitHub repo, new workspace). Do not clone the template yourself: the script does it.

## 1. Requirements

Check each with `<tool> --version`; install what is missing, then open a new terminal.

| Tool | macOS / Linux | Windows |
|---|---|---|
| git | `brew install git` / `sudo apt install git` | `winget install Git.Git` |
| gh | `brew install gh` / https://cli.github.com | `winget install GitHub.cli` |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

Then run `gh auth login`. You need admin rights on the repository (setup creates a secret and
variables).

## 2. Get a dltHub API key (setup only)

Ask the user to:

1. Log in to the dltHub dashboard. If the organization has no workspace yet, create one first
   (this is where you pick a region), then delete it or leave it.
2. Create a **user-level** API key (starts with `dlt_u_`) named `github-setup-key`. It is only
   needed during setup and can be revoked afterwards (step 6).
3. Put the key in a `.env` file in the current directory. The user does this, not the agent, so the key
   never appears in the chat or shell history:

   ```bash
   # .env
   DLTHUB_API_KEY='dlt_u_...'
   ```

Agents: never read, print or invent these values. `.env` is git-ignored by the scaffold.

## 3. Run (from the directory containing `.env`)

```bash
uv run --env-file .env https://raw.githubusercontent.com/dlt-hub/dlthub-github-minimal/main/.github/setup.py [repo-name]    # add --public for a public repo
```

Where the template is copied depends on the current directory (a lone `.env` does not count):

- **Empty directory**: copied to `.`; the GitHub repo is named after the directory.
- **Non-empty directory**: ask the user for a repository name and pass it as `[repo-name]`; copied to `./<repo-name>`.

Setup creates the repository (private by default), then runs `uvx dlthub-init@latest`, creates the workspace (named after the repo), creates a
workspace-scoped CI key and stores it as the `DLTHUB_API_KEY` repository secret, sets the
`DLTHUB_WORKSPACE_ID` / `DLTHUB_ORGANIZATION_ID` variables, then commits and pushes to the
default branch. Success ends with `Done.`

## 4. Verify

Check that `https://github.com/<owner>/<repo>/actions` shows a green run.

## 5. Troubleshoot

| Message | Fix |
|---|---|
| `set DLTHUB_API_KEY` | run the command from step 3 (it loads `.env`) |
| `gh/git/uv not found` | step 1 |
| `gh auth status` fails | run `gh auth login` |
| `the key belongs to N organizations` | setup supports exactly one organization: use a key from an account with a single organization |
| `Organization region must be set` (HTTP 409) | the organization has no region yet: create a first workspace in the dashboard (pick a region), then start over |
| `403` / `Resource not accessible` | you lack admin rights on the repository |
| `could not create a workspace API key` | check that your key belongs to the organization and has permission to create keys |
| Re-running fails | not supported: start from scratch |

## 6. Cleanup

1. Delete the `.env` file from disk: `rm .env`.
2. Revoke `github-setup-key` in the dltHub dashboard. CI does not use it.
3. The CI key expires after 365 days: renew it then (create a workspace key in the dashboard and
   run `gh secret set DLTHUB_API_KEY`).
4. Optionally delete `setup.md`, `.github/setup.py` from the new repository.
