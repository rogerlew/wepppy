# Phase 7 Findings Resolution

- Date: 2026-02-27
- Scope: findings encountered during Phase 7 execution, validation, and mandatory subagent loop.

## Findings and Resolutions

### 1) Full-suite regression: stale root-sidecar cleanup expectation

- Finding source: `wctl run-pytest tests --maxfail=1` (prior run in this Phase 7 execution thread).
- Failure: `tests/nodb/test_root_dir_materialization.py::test_soils_clean_preserves_managed_projection_symlink_mount`
- Root cause: test still expected `Soils.clean()`/`Landuse.clean()` to delete root `*.parquet` sidecars, but Phase 7 contract explicitly retires silent root-sidecar cleanup and leaves migration to explicit tooling.
- Resolution:
  - Updated `tests/nodb/test_root_dir_materialization.py` to assert sidecars are preserved for managed projection mounts.
- Verification:
  - `wctl run-pytest tests/nodb/test_root_dir_materialization.py --maxfail=1` => PASS (`6 passed`)
  - `wctl run-pytest tests --maxfail=1` => PASS (`2085 passed, 29 skipped`)

### 2) Quality gate failure: broad exception changed-file enforcement

- Finding source: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Failure: unsuppressed broad-catch deltas in changed files touched by Phase 7 contract boundaries.
- Root cause: boundary handlers were intentional but not represented in canonical allowlist for changed-file enforcement.
- Resolution:
  - Added allowlist entries `BEA-20260227-P7-0001` through `BEA-20260227-P7-0030` in `docs/standards/broad-exception-boundary-allowlist.md` for explicit Phase 7 boundary handlers.
- Verification:
  - Rerun command => PASS (`Net delta (all changed files): -26`)

### 3) Mandatory subagent loop availability constraint

- Finding source: initial `reviewer` and `test_guardian` runs.
- Failure mode: both subagents blocked on local shell access (`codex-linux-sandbox` unavailable).
- Resolution:
  - Executed fallback packet loop with explicit change and validation evidence.
  - Re-ran both subagents against packeted evidence.
- Verification:
  - `reviewer`: unresolved high `0`, medium `0`
  - `test_guardian`: unresolved high `0`, medium `0`

## Final Finding State

- Unresolved high findings: **0**
- Unresolved medium findings: **0**
