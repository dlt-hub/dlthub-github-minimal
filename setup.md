# Setup: connect this repository to dltHub (CI/CD)

For an agent or a human. Goal: run `.github/setup.sh` once, from a clone of the repository
created from the GitHub template. It scaffolds the project with `uvx dlthub-init@latest` (project files and up-to-date skills),
creates a dltHub workspace named after the repo, configures GitHub, and pushes, which starts the
first production deploy. After that: merging to the default
branch deploys. Do not improvise other steps.

## 1. Requirements

Check each with `<tool> --version`; install what is missing, then open a new terminal.

| Tool | macOS / Linux | Windows (use Git Bash or WSL) |
|---|---|---|
| git | `brew install git` / `sudo apt install git` | `winget install Git.Git` |
| gh | `brew install gh` / https://cli.github.com | `winget install GitHub.cli` |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

Then `gh auth login` (you need admin rights on the repository: it creates an environment, secrets,
variables and a ruleset). Windows: run in Git Bash/WSL, and make sure `setup.sh` has LF endings
(`git config core.autocrlf input` before cloning).

## 2. Ask the user for

| Name | What |
|---|---|
| `DLTHUB_API_KEY` | dltHub API key (user-level, starts with `dlt_u_`) |
| `DLTHUB_ORGANIZATION_ID` | only if the key belongs to several organizations (the organization needs a region/dataplane) |
| `DLTHUB_CI_API_KEY` | optional: workspace-scoped key (`dlt_sa_...`) from the dashboard, stored for CI instead of the user key |
| `DLTHUB_SECRETS_JSON` | optional: runtime secrets as a JSON object |

Never invent or print them. Safest: put them in a `.env` file (never commit it, and agents should not read it) and load it into the current shell without displaying it:

```bash
# .env
DLTHUB_API_KEY='dlt_u_...'
DLTHUB_SECRETS_JSON='{"DESTINATION__WAREHOUSE__CREDENTIALS__AWS_SECRET_ACCESS_KEY":"..."}'  # optional
```

```bash
set -a; . ./.env; set +a
```

Or export them directly with single quotes: `export DLTHUB_API_KEY='dlt_u_...'`.

## 3. Run (from the repository root)

```bash
bash .github/setup.sh
```

The script first runs `uvx dlthub-init@latest` (existing files are kept), then commits and pushes the result to the default branch. The repository is read from `gh`; the workspace is named after it (`-2`, `-3`, ... on a name
collision; it can be renamed in the dashboard). Success ends with `Done.`

## 4. Troubleshoot

| Message | Fix |
|---|---|
| `set DLTHUB_API_KEY` | export it in the same shell |
| `gh/git/uv not found` | step 1 |
| `run 'gh auth login'` / `run from a clone` | authenticate; run inside the cloned repository |
| `found N organizations` | export `DLTHUB_ORGANIZATION_ID` |
| `403` / `Resource not accessible` | you lack admin on the repo |
| `could not create the branch ruleset` (warning) | rulesets need a public repo or a paid plan; setup continues without branch protection |
| `Organization region must be set` (HTTP 409) | your organization has no region yet. Create a first workspace in the dltHub dashboard (this is where you pick a region), then start over |
| Re-running | not supported: start from scratch (new directory, new GitHub repo, new workspace) |

## 5. Afterwards

1. Check `https://github.com/<owner>/<repo>/actions` is green.
2. If `DLTHUB_CI_API_KEY` was not set, CI uses the user-level key: do not revoke it. Otherwise it can be revoked.
3. Optionally delete `setup.md` and `.github/setup.sh`, `.github/dlthub_setup.py`.
