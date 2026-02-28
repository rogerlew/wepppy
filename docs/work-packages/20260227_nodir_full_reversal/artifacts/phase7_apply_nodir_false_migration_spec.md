# Phase 7 Migration Spec: `apply_nodir=false` Runs with Root Resources

- Generated: 2026-02-27
- Purpose: define the follow-on bulk migration contract for moving in-scope WD-root resources to canonical directory paths.
- In-scope population: runs where `nodb.apply_nodir == false` and at least one in-scope root resource exists.
- Out-of-scope population: `apply_nodir=true` runs.

## 1. Eligibility and Exclusions

A run is eligible when all are true:
1. Run is a NoDir-era run or mixed-era run with in-scope root resources.
2. `apply_nodir` resolves to `false`.
3. One or more of these resources exist at WD root:
   - `landuse.parquet`
   - `soils.parquet`
   - `climate.*.parquet`
   - `watershed.*.parquet`
   - `wepp_cli_pds_mean_metric.csv`

A run is excluded when any are true:
1. `apply_nodir` resolves to `true`.
2. Run cannot enter maintenance mode (lock unavailable, active mutation, or operational policy exclusion).
3. Run already has zero in-scope root resources.

## 2. Mapping Contract

| Source (WD root) | Target (canonical directory) |
| --- | --- |
| `landuse.parquet` | `landuse/landuse.parquet` |
| `soils.parquet` | `soils/soils.parquet` |
| `climate.<name>.parquet` | `climate/<name>.parquet` |
| `watershed.<name>.parquet` | `watershed/<name>.parquet` |
| `wepp_cli_pds_mean_metric.csv` | `climate/wepp_cli_pds_mean_metric.csv` |

## 3. Bulk Migration Workflow

### Stage A: Inventory (dry-run only)

Per run:
1. Resolve `apply_nodir` and eligibility.
2. Discover root resources via fixed glob set:
   - `WD/landuse.parquet`
   - `WD/soils.parquet`
   - `WD/climate.*.parquet`
   - `WD/watershed.*.parquet`
   - `WD/wepp_cli_pds_mean_metric.csv`
3. Emit dry-run records for each discovered source file with planned target path.
4. Emit skipped record for ineligible runs.

### Stage B: Apply (locked maintenance mode)

Per eligible run:
1. Acquire run maintenance lock and block writes.
2. For each source file, derive target path from mapping table.
3. Ensure target parent directory exists.
4. Compare source and target state:
   - target missing: atomic move source -> target.
   - target exists + same SHA-256: keep target, delete root source.
   - target exists + different SHA-256: record conflict, keep both untouched, mark run failed.
5. Refresh query catalog entries for moved parquet resources.
6. Verify postconditions:
   - no in-scope root resources remain,
   - canonical targets exist,
   - moved parquets open successfully.
7. Release maintenance lock.

### Stage C: Post-run validation

For each migrated run, assert all true:
1. No file from the root in-scope set remains.
2. Every migrated source has canonical target present.
3. Query-engine catalog resolves canonical paths only.
4. Status is `ok` or explicit `conflict_requires_manual_resolution` (no silent partial success).

## 4. Conflict Policy

Conflicts are non-destructive and operator-visible:
1. Never overwrite an existing target when hashes differ.
2. Record both hashes and paths.
3. Keep source and target untouched for manual resolution.
4. Mark run terminal state as `conflict_requires_manual_resolution`.

## 5. Required Audit Record Schema

Each per-file action record must include:
- `runid`
- `apply_nodir`
- `source_relpath`
- `target_relpath`
- `action` (`planned`, `moved`, `dedup_deleted_source`, `conflict`, `skipped`)
- `status` (`dry_run`, `ok`, `conflict`, `error`, `skipped`)
- `source_sha256` (nullable)
- `target_sha256` (nullable)
- `message`
- `timestamp_utc`

Each run-level summary record must include:
- `runid`
- `eligible`
- `files_discovered`
- `files_moved`
- `files_dedup_deleted`
- `files_conflict`
- `files_error`
- `final_status`
- `timestamp_utc`

## 6. Idempotence and Restart Contract

- Re-running dry-run produces same planned mappings for unchanged runs.
- Re-running apply after successful migration is no-op.
- Conflict runs remain conflict until manually resolved.
- Partial failures are resumable at per-file granularity using audit records.

## 7. Safety and Rollback Expectations

- Migration uses move/remove operations only for in-scope files.
- No mutation of file content unless hashes are computed.
- On run-level fatal error, leave remaining source files untouched.
- Rollback of migration code does not roll back moved files; use audit logs for targeted restore if needed.

## 8. Success Criteria for Follow-On Bulk Phase

1. Every eligible (`apply_nodir=false`) run has zero in-scope root resources.
2. Canonical targets exist for all migrated resources.
3. No unresolved conflicts are hidden; all conflicts are explicitly logged.
4. Validation scans are reproducible from audit logs.

## 9. Phase 7 Runtime Refactor Dependency

Phase 7 runtime refactor must fail fast when these root resources are present. This migration spec is the approved path to make `apply_nodir=false` runs compliant before/after fail-fast rollout.
