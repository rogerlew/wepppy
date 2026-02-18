# Phase 7 Operational Runbook

## Purpose

Operational procedure for Phase 7 rollout:
- bulk NoDir migration crawler execution;
- new-run default NoDir behavior;
- rollback and incident handling;
- forensics, including admin raw `.nodir` download workflow;
- JSONL audit log interpretation.

## Rollout Controls

### New-Run Default NoDir Toggle

- Runtime toggle: `WEPP_NODIR_DEFAULT_NEW_RUNS`
- Default behavior when unset: enabled.
- Disable immediately:

```bash
export WEPP_NODIR_DEFAULT_NEW_RUNS=0
# restart weppcloud/rq-engine services so new create flows pick up the env change
```

When enabled, new-run creation flows write:
- `WD/.nodir/default_archive_roots.json`

`mutate_root(s)` uses that marker to freeze configured roots after successful mutation callbacks.

Important: this toggle controls new marker creation only. Existing run markers remain active until removed or renamed.

### Bulk Crawler Command

Reference invocation (all allowlisted roots):

```bash
cd /workdir/wepppy
python -m wepppy.tools.migrations.nodir_bulk \
  --runs-root /wc1/runs \
  --root watershed --root soils --root landuse --root climate \
  --audit-log /wc1/runs/_ops/nodir_bulk_$(date -u +%Y%m%dT%H%M%SZ).jsonl \
  --verbose
```

Dry-run preview:

```bash
python -m wepppy.tools.migrations.nodir_bulk \
  --runs-root /wc1/runs \
  --root watershed --root soils --root landuse --root climate \
  --dry-run \
  --audit-log /wc1/runs/_ops/nodir_bulk_dryrun.jsonl
```

Resume behavior:
- default: enabled (completed run/root pairs in prior audit log are skipped).
- disable resume: add `--no-resume`.

## Safety Gates Enforced by Crawler

For non-dry-run mutation:
- requires `WD/READONLY`;
- fails fast if run has active NoDb locks (`lock_statuses(runid)`);
- fails fast if root maintenance lock cannot be acquired (`NODIR_LOCKED`);
- records canonical NoDir errors from `resolve(..., view="effective")`.

No mutation is attempted for run/root pairs that fail safety gates.

## Rollback Procedure

### Immediate Rollback (Stop Further Migration)

1. Disable new-run defaults:

```bash
export WEPP_NODIR_DEFAULT_NEW_RUNS=0
# restart services
```

2. Stop crawler executions (cron/manual jobs).
3. For already-created runs in rollback scope, disable per-run auto-archive marker:

```bash
RUN_WD=/wc1/runs/<prefix>/<runid>

if [ -f "$RUN_WD/.nodir/default_archive_roots.json" ]; then
  mkdir -p "$RUN_WD/.nodir/rollback"
  mv "$RUN_WD/.nodir/default_archive_roots.json" \
    "$RUN_WD/.nodir/rollback/default_archive_roots.$(date -u +%Y%m%dT%H%M%SZ).json"
fi
```

4. Preserve current audit logs; do not truncate.

### Functional Rollback for Affected Runs

For a run/root that must return to directory form while avoiding persistent mixed state:

```bash
RUN_WD=/wc1/runs/<prefix>/<runid>
ROOT=<root>
export RUN_WD ROOT

cd /workdir/wepppy
python - <<'PY'
from datetime import datetime, timezone
import os
from pathlib import Path

from wepppy.nodir.thaw_freeze import thaw

run_wd = Path(os.environ["RUN_WD"])
root = os.environ["ROOT"]

thaw(str(run_wd), root)

archive = run_wd / f"{root}.nodir"
if archive.exists():
    rollback_dir = run_wd / "archives"
    rollback_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive.rename(rollback_dir / f"{root}.nodir.rollback.{stamp}")
PY
```

Notes:
- run/root must not be actively locked.
- disable or rename `WD/.nodir/default_archive_roots.json` before re-running root mutations, otherwise marker-driven auto-freeze can re-archive dir-form roots.
- after thaw, move the canonical archive path out of `<root>.nodir` (for example to `archives/`) so public surfaces do not remain in mixed-state conflict.
- this rollback is root-scoped; perform only on affected roots.
- capture forensics before mutation (see section below).

### Code Rollback

If required, revert Phase 7 merge commit(s) and redeploy.

After rollback:
- rerun targeted gates for browse/files/download and nodir migration tests;
- verify no stale `WD/<root>.nodir.tmp` or `WD/<root>.thaw.tmp` artifacts remain.

## Forensics Procedure

Collect these artifacts before cleanup or retries:

```bash
RUN_WD=/wc1/runs/<prefix>/<runid>
ROOT=<root>

ls -la "$RUN_WD"/{READONLY,${ROOT},${ROOT}.nodir,${ROOT}.nodir.tmp,${ROOT}.thaw.tmp} 2>/dev/null
stat "$RUN_WD/${ROOT}.nodir" 2>/dev/null
cat "$RUN_WD/.nodir/${ROOT}.json" 2>/dev/null
```

Also capture:
- relevant crawler JSONL lines for `runid + root`;
- current run lock state (`lock_statuses(runid)` via Python shell);
- request/worker logs around failure timestamp.

### Admin Raw `.nodir` Download Workflow

For invalid archive forensics, admin may download raw bytes directly:

- URL pattern:
  - `/weppcloud/runs/<runid>/<config>/download/<root>.nodir`

Contract behavior:
- admin: `200` raw bytes allowed even for invalid allowlisted archive.
- non-admin: `500 NODIR_INVALID_ARCHIVE` (invalid archive) or `409 NODIR_MIXED_STATE` (mixed state).

Recommended steps:
1. authenticate as admin;
2. download raw archive bytes;
3. inspect offline with zip tooling;
4. preserve original file checksum in incident notes.

## JSONL Audit Log Interpretation

### Record Shape

One JSON object per line, keyed by run/root.

Common fields:
- `ts` UTC timestamp
- `runid`
- `wd`
- `root`
- `dry_run`
- `status`
- `message`
- `duration_ms`
- optional: `code`, `http_status`, `active_locks`, `details`

### Status Meanings

Completion statuses (resume treats as complete):
- `archived`
- `already_archive`
- `missing_root`

Non-terminal or informational:
- `would_archive` (dry-run)
- `resume_skipped`

Failure statuses:
- `readonly_required`
- `active_run_locked`
- `root_lock_failed`
- `nodir_error`
- `exception`

### Triage Rules

- `readonly_required`:
  - set `WD/READONLY`, rerun crawler.
- `active_run_locked`:
  - wait for active job completion; rerun.
- `root_lock_failed` (`NODIR_LOCKED`):
  - root currently in transition or lock contention; rerun later.
- `nodir_error`:
  - use `code` (`NODIR_MIXED_STATE`, `NODIR_INVALID_ARCHIVE`, etc.) to follow contract-specific recovery.
- `exception`:
  - treat as unexpected failure, collect full forensics bundle.

## Post-Rollout Verification

After each migration wave:
1. run browse/files/download probes against migrated run(s);
2. spot-check JSONL for unexpected failure-status spikes;
3. verify no mixed-state leakage (`WD/<root>/` and `WD/<root>.nodir` both present outside known transitional windows);
4. keep audit logs under retained ops path for incident replay.

