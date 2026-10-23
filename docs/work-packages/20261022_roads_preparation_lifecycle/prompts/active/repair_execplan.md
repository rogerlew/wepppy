# Implement Roads replacement and current-result lifecycle

## Purpose / Big Picture


A user who prepares Roads again must never see prior results attached to the new
segments. Replace the prepared segment set, invalidate previous Roads results
upstream, and restore availability only after a fresh successful run. Existing
baseline WEPP results stay usable. This package delivers wired runtime behavior,
not a scaffold. No new dashboard detachment layer is included.

## Progress


- [x] (2026-10-22) Scaffold package and inspect current producers/consumers.
- [x] Ratify concrete publication boundary with two independent reviews; checkpoint `1270c209f`.
- [x] Implement lifecycle, retention, shared admission and regression coverage.
- [x] Validate real isolated project transitions, seven live HTTP readers, Chromium browse and canonical archive/restore.
- [ ] Run final gates/reviews, commit and close.

## Surprises & Discoveries


prepare_segments currently clears last_run_summary only after it writes geometry.
The run output workspace is deleted at fresh execution. Consumers also inspect
files directly, so clearing NoDb alone cannot enforce invalidation. RQ already
has a Roads runtime lock; direct parameter/upload mutations must participate in
the lifecycle boundary too. Summary metadata does not itself establish currentness.

Review exposed valid workspace symlinks, existing D-Tale sessions, module toggles,
and read-only restore permissions as additional uses of the same admission boundary.
History materializes owned file links before replacement. Archive coordination is
unconditional so first-time Roads creation cannot race a whole-project archive.

## Decision Log


2026-10-22 / Roger approved replacement plus invalidation and fresh run, explicitly
rejecting stable-ID reconciliation and beta compatibility. User then requested
work-package execution. Prior permission for scoped commits persists.
2026-10-22 / Codex scopes this package to upstream lifecycle implementation; GL
layer D1–D4 remain open and are not silently decided here.

## Outcomes & Retrospective


Runtime implementation is wired. Isolated UM1 runs and re-preparation passed: 34 profiles, 911 baseline files and 46 original Parquets unchanged. Canonical archive/restore preserved the current set, history and lock inode. Seven live HTTP readers passed current -> writer busy -> reprepared -> fresh run transitions; historical downloads and Chromium browse passed. Final broad gates and independent review closure remain in progress.

## Context and Orientation


Producer: wepppy/nodb/mods/roads/roads.py, prepare_segments, run_roads_wepp,
set_params, set_uploaded_geojson and _clear_stale_run_state_locked. Existing RQ
single-flight logic is in wepppy/rq/roads_rq.py. Report links are built in
wepppy/weppcloud/routes/nodb_api/roads_bp.py; direct reports and GL can bypass
those links. Query source resolution is in wepppy/query_engine/core.py and native
execution uses executor.py. Browse/download runs in the separate browse service.
Canonical authority is docs/schemas/roads-preparation-lifecycle-contract.md,
with output-scope and segment-summary contracts reconciled at the checkpoint.

## Plan of Work


Milestone 1 enumerates all direct readers and defines the smallest shared current-
result admission and retained-history boundary. Record exact fields/paths, absence,
legacy, empty and malformed behavior in the canonical contract. Obtain independent
correctness and security contract reviews and commit that checkpoint before code.

Milestone 2 invalidates before any accepted mutation overwrites prepared geometry
or run inputs, retains prior output as explicit history, and publishes current
readiness only after fresh run artifacts validate. Reuse existing run locks/cache
mechanisms. Ensure direct controller and queued work cannot publish late old results.
Wire shared admission into report, dashboard, query and download boundaries,
including stale catalogs. Preserve ordinary historical browsing and baseline.

Milestone 3 adds direct filesystem/consumer tests and runs focused wctl suites.
Use the archive-restored isolated UM1 validation project or a fresh canonical
archive restore to exercise a real preparation and fresh Roads run; do not touch
/wc1/runs/cl/clogging-starch. Read generated files and semantic values, verify
baseline hashes, failure/retry, HTTP downloads/query admission and archive restore.

Milestone 4 completes independent correctness/security reviews and full pytest
via wctl. Use the installed Chromium path
/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers for browser tests.
Check docs, stubs and changed broad exceptions. Run RQ graph checks if queue edges
change. Commit only task files; update tracker/PROJECT_TRACKER and move this plan
to completed with wctl doc-mv after actual acceptance.

## Concrete Steps


Work from /workdir/wepppy on the existing branch. Follow nearest AGENTS, NoDb,
query-engine, web/browse and tests instructions. Use wctl for container execution
and pytest. Focus first on tests/nodb/mods/test_roads_controller.py and new lifecycle
regressions, then affected query/browse/report modules. Retain concise receipts
under artifacts, including exact revisions, hashes, runtime identity and commands.

## Validation and Acceptance


Successful run -> prepare again -> every current-result consumer unavailable ->
fresh successful run -> only new results available. Prove this with surviving
old files, reused segment IDs, empty/no-output state, legacy beta files, failed
preparation/run, concurrent mutation/late completion, cache reload and archive.
No old data is silently promoted. No baseline file changes. Historical evidence
is visible and archivable. Tests that mock the changed publication boundary are
insufficient. No production deployment or original-run repair claim.

## Idempotence and Recovery


Invalidation must be safe to retry; interrupted work stays unavailable. Preserve
prior artifacts in visible history without overwriting existing history. Fresh
prepare/run is the recovery, not identity migration or old-output regeneration.
Reject aliased paths and use existing permissions. Keep lifecycle failures explicit.

## Artifacts and Notes


The contract decision, independent reviews, focused/broad gate receipts and real
project consumer evidence live under this package's artifacts directory. Closed
prior Roads packages remain immutable history.

## Interfaces and Dependencies


Keep public Roads method names, output paths, authorization and baseline behavior.
No new dependency/service/native release or queue topology. Any additive current-
publication/retention artifact must be specified and independently reviewed before
implementation, with archive and reader behavior verified.
