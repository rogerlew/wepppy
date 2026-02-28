# Phase 3 Migration Summary

- Generated: 2026-02-27 07:09Z
- Scope: Phase 3 `.nodir` rollback canary + bulk execution evidence.
- Runtime note: migration commands were executed via `wctl exec weppcloud` using `/opt/venv/bin/python` because host/system `python3` lacked `jsonpickle`.
- Audit refresh note: canary and bulk logs were rerun into truncated JSONL artifacts at closeout to avoid appended duplicate records from prior retries.

## Audit Status Counts

- Canary dry-run (`phase3_canary_dry_run_audit.jsonl`): {'already_directory': 12}
- Canary apply (`phase3_canary_apply_audit.jsonl`): {'readonly_required': 12}
- Bulk dry-run (`phase3_bulk_dry_run_audit.jsonl`): {'already_directory': 3892, 'nodir_error': 2, 'would_restore': 38}
- Bulk apply (`phase3_bulk_apply_audit.jsonl`): {'already_directory': 52, 'readonly_required': 3880}

## Bulk Apply Outcome

- restored: 0
- already_directory: 52
- failures: 3880
- quarantined: 3880
- successful (restored + already_directory): 52

## Restore Verification

- restored records checked: 0
- restored verification violations: 0
- verification rule: for `status=restored`, `<wd>/<root>/` must exist and `<wd>/<root>.nodir` must not exist.

## Observed Blocker

- Bulk apply failures were dominated by `readonly_required`; migration apply requires `WD/READONLY` before mutation and most scanned runs were not in maintenance-readonly mode.
- Bulk dry-run found `would_restore` entries, showing convertible archive-form roots exist but were not mutated due readonly gate in apply mode.

## Quarantine Artifact

- See `phase3_quarantined_runs.md` for failure quarantine disposition linked to `phase3_bulk_apply_audit.jsonl`.
