# Phase 8 Validation Log

- Date: 2026-02-28
- Scope: validation state for Phase 8 through Phase 7 closeout execution.

## Targeted Migration Tests

1. `wctl run-pytest tests/tools/test_migrations_unroll_root_resources_batch.py --maxfail=1`
   - Result: `PASS` (`26 passed`, `0 failed`, `2 warnings`)

## Required Validation Gates (Final Run)

1. `wctl run-pytest tests --maxfail=1`
   - Result: `PASS` (`2159 passed`, `29 skipped`, `0 failed`, `153 warnings`)
2. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
   - Result: `PASS` (`70` changed Python files scanned, net broad-catch delta `-26`)
3. `python3 tools/code_quality_observability.py --base-ref origin/master`
   - Result: `PASS` (observe-only; wrote `code-quality-report.json` and `code-quality-summary.md`)
4. `wctl check-rq-graph`
   - Result: `PASS` (`RQ dependency graph artifacts are up to date`)
5. `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal`
   - Result: `PASS` (`44 files validated, 0 errors, 0 warnings`)
6. `wctl doc-lint --path docs/schemas`
   - Result: `PASS` (`8 files validated, 0 errors, 0 warnings`)
7. `wctl doc-lint --path PROJECT_TRACKER.md`
   - Result: `PASS` (`1 file validated, 0 errors, 0 warnings`)

## Phase Command Execution

1. Forest dry-run command
   - Exit: `1`
   - Outcome: inventory produced, with explicit run-level config-resolution errors and predicted conflicts logged.
2. Forest apply command (initial)
   - Exit: `1`
   - Outcome: bulk migration progressed; convergence fixes applied for idempotent no-op handling on disappearing sources.
3. Forest apply command (convergence rerun)
   - Exit: `0`
   - Outcome: no run/file errors; only explicit conflict runs remain.
4. Wepp1 dry-run command
   - Exit: `1`
   - Outcome: completed against wepp1 container roots (`/wc1/runs,/wc1/batch`) with full inventory (`6993` discovered, `252` eligible, `11` predicted conflicts); `460` runs reported config-resolution errors.
5. Wepp1 apply command (approved gate artifact)
   - Exit: `1`
   - Outcome: completed against wepp1 container roots (`/wc1/runs,/wc1/batch`) with explicit non-destructive outcomes (`2` conflicts, `3` config-resolution run errors, `0` moves, `0` dedup deletes); artifacts copied from container `/tmp` into package `phase8_wepp1_apply_*` files.
6. Wepp1 reconciliation dry-run command (post-apply, same roots)
   - Exit: `1`
   - Outcome: current-snapshot reconciliation captured `1858` discovered runs, `2` eligible runs, `2` predicted conflicts, and `3` run errors, confirming Phase 6 apply operated on the current `/wc1` tree rather than the earlier Phase 4 snapshot.
7. Phase 7 closeout package doc-lint rerun
   - Exit: `0`
   - Outcome: package docs validate clean after closeout updates (`44` files validated, `0` errors, `0` warnings).

## Subagent Closure Validation

- `reviewer` final unresolved counts: `high=0`, `medium=0`
- `test_guardian` final unresolved counts: `high=0`, `medium=0`

Mandatory subagent closure condition is satisfied.
