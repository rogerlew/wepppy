# WEPPcloud Bootstrap
> Use Git to override WEPP and SWAT+ input files, then run those inputs on WEPPcloud compute.
> **See also:** `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md` for the broader job API and polling model.

## Overview
Bootstrap gives each run its own Git repository so you can:
- edit model input files locally,
- save those edits as commits,
- push commits back to the run, and
- run WEPP/SWAT+ in WEPPcloud against a selected commit.

This is useful when you need precise control of input files while still using:
- WEPPcloud run orchestration,
- interchange generation, and
- interactive reports and dashboards.

Bootstrap is designed to keep changes:
- auditable (commit history),
- reproducible (checkout by commit SHA), and
- recoverable (return to earlier snapshots).

## Square-One Git Model
If Git is new to you, use this mental model:

- A **repository** is a folder with history.
- A **commit** is a saved snapshot of files at a point in time.
- Your **local clone** is where you edit files on your machine.
- The **remote** is the run repository on WEPPcloud.
- **Push** sends your local commits to WEPPcloud.
- **Pull** gets commits from WEPPcloud to your local clone.

For Bootstrap, think of it as:
1. Edit inputs locally.
2. Commit locally.
3. Push to the run.
4. In WEPPcloud, choose the commit and run.

## What Bootstrap Tracks
Bootstrap tracks only model input folders:
- `wepp/runs/`
- `swat/TxtInOut/`

Everything else in the run directory is outside Bootstrap history.

## Preconditions
Bootstrap requires:
- a non-anonymous run tied to a user account,
- run-level Bootstrap enabled,
- Git installed on your local machine,
- network access to the WEPPcloud host.

Admin/Root can disable Bootstrap for a run at any time.

## First-Time Setup
1. Open the run in WEPPcloud.
2. In the Bootstrap panel, click **Enable Bootstrap**.
3. Click **Mint Token**.
4. Copy and run the **Clone Command** shown in the panel.

Example format:
```bash
git clone https://<user_id>:<jwt>@<host>/git/<prefix>/<runid>/.git
```

The token (`<jwt>`) is your temporary password for Git HTTP auth.

## Daily Workflow (Recommended)
Use this loop each time you update inputs.

1. Go to your local clone:
```bash
cd <your-bootstrap-clone>
```

2. Sync before editing:
```bash
git pull --rebase
```

3. Edit input files under:
- `wepp/runs/`
- `swat/TxtInOut/`

4. Review changes:
```bash
git status
```

5. Commit:
```bash
git add wepp/runs swat/TxtInOut
git commit -m "Describe the input change"
```

6. Push:
```bash
git push
```

7. In WEPPcloud:
- click **Refresh Commits**,
- choose the commit,
- click **Checkout**,
- run using the **No Prep** buttons.

## Run Behavior: No-Prep vs Standard Pipelines
Bootstrap introduces two run styles:

- **Bootstrap No-Prep routes** (from Bootstrap panel run buttons):
  - run against the currently checked out commit,
  - do not regenerate inputs,
  - do not auto-commit.

- **Standard WEPP/SWAT workflows** (outside Bootstrap no-prep actions):
  - may switch to `main`,
  - can regenerate inputs,
  - can auto-commit rebuilt inputs into Bootstrap history.

If your goal is "run exactly what I pushed", use Bootstrap no-prep run buttons.

## What You Can and Cannot Do
### Supported
- Edit and push text input files in tracked folders.
- Create many commits and switch among them.
- Mint new tokens whenever needed.
- Collaborate with others (with normal Git pull/push discipline).

### Blocked by Server Validation
- Modifying `.run` files.
- Writing outside allowed folders.
- Renaming or copying tracked files in a push.
- Deleting tracked input files.
- Pushing symlinks or submodules.
- Pushing binary files.
- Pushing files larger than 50 MB.
- Force-push/non-fast-forward updates.
- Ref deletion pushes.

## Token and Access Model
- Tokens are scoped to user + run + host.
- Token lifetime is 6 months.
- If token expires, mint a new one and update remote URL.
- If admin/root disables Bootstrap for the run, Git access is denied.

Refresh remote URL in an existing clone:
```bash
git remote set-url origin https://<user_id>:<new_jwt>@<host>/git/<prefix>/<runid>/.git
```

## Security Hygiene
- Treat the clone URL as a secret (it contains credentials).
- Do not paste tokenized URLs into tickets/chat/email.
- Rotate by minting a new token if exposed.

## Collaboration Model
When multiple users push to the same run:
- always pull before push,
- keep commits small and focused,
- use clear commit messages,
- resolve conflicts locally before pushing.

## Troubleshooting
### Push rejected immediately
Likely a validation rule was violated.
- Read the exact `git push` error text.
- Check path, file type, and size.
- Revert prohibited changes (especially `.run` edits, renames, deletes).

### Authentication failed / 401
- Token may be expired or run access disabled.
- Mint a new token.
- Update `origin` URL with the new token.

### Non-fast-forward rejection
- Your local branch is behind remote.
- Run:
```bash
git pull --rebase
git push
```

### Commit does not appear in WEPPcloud list
- Click **Refresh Commits**.
- Ensure you pushed the branch/history shown in Bootstrap (main history view).

## Quick Command Reference
```bash
# one-time clone
git clone https://<user_id>:<jwt>@<host>/git/<prefix>/<runid>/.git

# daily sync
git pull --rebase

# inspect changes
git status
git diff

# commit + push
git add wepp/runs swat/TxtInOut
git commit -m "input update"
git push

# rotate token in existing clone
git remote set-url origin https://<user_id>:<new_jwt>@<host>/git/<prefix>/<runid>/.git
```
