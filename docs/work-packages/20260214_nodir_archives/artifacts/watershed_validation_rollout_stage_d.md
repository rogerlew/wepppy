# Watershed Validation and Rollout Gates Stage D (Phase 6a)

Scope: define enforceable validation gates, rollout controls, and rollback/forensics for the watershed-only Phase 6a execution waves.

## Pre-Merge Gates (Per Wave)

| Wave | Minimum Required Automated Tests | Pass/Fail Threshold | Contract Invariants to Assert | Merge Block Condition |
| --- | --- | --- | --- | --- |
| Wave 1 | `tests/nodir/test_state.py`, `tests/nodir/test_thaw_freeze.py`, `tests/nodir/test_resolve.py`, `tests/nodir/test_parquet_sidecars.py`, `tests/nodir/test_parquet_precedence_fs.py`, `tests/tools/test_migrations_parquet_backfill.py`, `tests/query_engine/test_activate.py` | All commands exit `0`; `0 failed`; no new xfail/skip introduced in touched tests | Mixed-state conflict (`409`), invalid archive (`500`), transitional lock (`503`), sidecar parquet precedence unchanged | Any contract regression or migration/query-engine parity break blocks merge |
| Wave 2 | `tests/microservices/test_rq_engine_watershed_routes.py`, `tests/topo/test_peridot_runner_wait.py`, `tests/topo/test_topaz_vrt_read.py`, `tests/test_wepp_top_translator.py`, `tests/nodir/test_state.py`, `tests/nodir/test_thaw_freeze.py`, `tests/nodir/test_resolve.py` | All commands exit `0`; `0 failed` | Producer mutation paths respect thaw/modify/freeze lock/state ordering and canonical NoDir error semantics, including legacy abstraction internals | Any mutation-path lock/state regression blocks merge |
| Wave 3 | `tests/nodir/test_materialize.py`, `tests/microservices/test_rq_engine_export_routes.py`, `tests/microservices/test_browse_dtale.py`, `tests/nodb/mods/test_omni.py`, `tests/nodb/mods/test_swat_interchange.py`, `tests/wepp/test_wepp_run_watershed_interchange_options.py`, `tests/weppcloud/routes/test_rhem_bp.py` | All commands exit `0`; `0 failed` | FS-boundary consumers materialize only when required; mixed/invalid/transitional states return canonical errors | Any archive-form consumer failure with Dir-form pass blocks merge |
| Wave 4 | `tests/microservices/test_browse_routes.py`, `tests/microservices/test_browse_security.py`, `tests/microservices/test_diff_nodir.py`, `tests/nodir/test_archive_fs.py`, `tests/nodir/test_archive_validation.py`, `tests/nodir/test_materialize.py -k "transition_state or missing_state_with_temp_sentinel_returns_503"` | All commands exit `0`; `0 failed` | Browse/files/download remain extraction-free; mixed/invalid/locked semantics match behavior matrix | Any public-surface contract drift blocks merge |

## Post-Merge Gates (Per Wave)

| Wave | Required Regression Checks After Merge | Pass/Fail Threshold | Rollout Gate | Failure Action |
| --- | --- | --- | --- | --- |
| Wave 1 | Re-run Wave 1 pre-merge suite on merge commit; run migration regression set (`tests/tools/test_migrations_runner.py`, `tests/tools/test_migrations_parquet_backfill.py`) | All commands exit `0`; no new failures on merge commit | Promote Wave 1 only if migration outputs and query-engine catalog parity hold | Stop rollout; revert Wave 1 merge commits; keep Wave 2 closed |
| Wave 2 | Re-run Wave 2 pre-merge suite on merge commit; run targeted queue/routing + abstraction internals regression (`tests/microservices/test_rq_engine_watershed_routes.py`, `tests/topo/test_peridot_runner_wait.py`, `tests/topo/test_topaz_vrt_read.py`, `tests/test_wepp_top_translator.py`) | All commands exit `0`; no new failures on merge commit | Promote Wave 2 only if producer mutation paths and abstraction internals pass lock/state probes | Stop rollout; revert Wave 2 merge commits; keep Wave 3 closed |
| Wave 3 | Re-run Wave 3 pre-merge suite on merge commit; run export + mod consumer regression targets in staging | All commands exit `0`; no new archive-only failures | Promote Wave 3 only if archive-form consumers are parity-stable vs Dir-form | Stop rollout; revert Wave 3 merge commits; keep Wave 4 closed |
| Wave 4 | Re-run Wave 4 pre-merge suite on merge commit; run runtime read-surface probes on canary runs | All commands exit `0`; runtime probes return expected status/code pairs | Complete Phase 6a rollout only after behavior-matrix conformance is clean | Stop rollout; revert Wave 4 merge commits; keep Stage D open |

## Executable Test Matrix

| Wave | Gate | Command | Expected Result | Failure Action | Owner |
| --- | --- | --- | --- | --- | --- |
| Wave 1 | Pre-merge NoDir state/thaw gate | `wctl run-pytest tests/nodir/test_state.py tests/nodir/test_thaw_freeze.py tests/nodir/test_resolve.py` | Exit `0`; `0 failed` | Block merge; fix lock/state contract regression | NoDir foundation owner |
| Wave 1 | Pre-merge sidecar/migration gate | `wctl run-pytest tests/nodir/test_parquet_sidecars.py tests/nodir/test_parquet_precedence_fs.py tests/tools/test_migrations_parquet_backfill.py tests/query_engine/test_activate.py` | Exit `0`; `0 failed` | Block merge; fix sidecar/migration parity | Watershed migration owner |
| Wave 1 | Post-merge migration regression | `wctl run-pytest tests/tools/test_migrations_runner.py tests/tools/test_migrations_parquet_backfill.py` | Exit `0`; `0 failed` | Revert Wave 1 merge commits and reopen Wave 1 | Watershed migration owner |
| Wave 2 | Pre-merge route/mutation gate | `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py` | Exit `0`; `0 failed` | Block merge; fix route-to-mutation orchestration | Watershed RQ owner |
| Wave 2 | Pre-merge legacy abstraction internals gate | `wctl run-pytest tests/topo/test_peridot_runner_wait.py tests/topo/test_topaz_vrt_read.py tests/test_wepp_top_translator.py` | Exit `0`; `0 failed` | Block merge; fix peridot/topaz/translator legacy abstraction internals | Watershed abstraction owner |
| Wave 2 | Pre-merge lock/transition gate | `wctl run-pytest tests/nodir/test_state.py tests/nodir/test_thaw_freeze.py tests/nodir/test_resolve.py` | Exit `0`; `0 failed` | Block merge; fix thaw/freeze contract handling | NoDir foundation owner |
| Wave 2 | Post-merge producer regression | `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py tests/topo/test_peridot_runner_wait.py tests/topo/test_topaz_vrt_read.py tests/test_wepp_top_translator.py tests/nodir/test_thaw_freeze.py` | Exit `0`; `0 failed` | Revert Wave 2 merge commits and keep Wave 3 closed | Watershed RQ owner |
| Wave 3 | Pre-merge materialization/export gate | `wctl run-pytest tests/nodir/test_materialize.py tests/microservices/test_rq_engine_export_routes.py tests/microservices/test_browse_dtale.py` | Exit `0`; `0 failed` | Block merge; fix FS-boundary consumer behavior | Export integration owner |
| Wave 3 | Pre-merge mods/WEPP consumer gate | `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_swat_interchange.py tests/wepp/test_wepp_run_watershed_interchange_options.py tests/weppcloud/routes/test_rhem_bp.py` | Exit `0`; `0 failed` | Block merge; fix watershed consumer coupling | Watershed consumer owner |
| Wave 3 | Post-merge consumer regression | `wctl run-pytest tests/nodir/test_materialize.py tests/microservices/test_rq_engine_export_routes.py tests/nodb/mods/test_swat_interchange.py` | Exit `0`; `0 failed` | Revert Wave 3 merge commits and keep Wave 4 closed | Export integration owner |
| Wave 4 | Pre-merge browse/files/download gate | `wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_browse_security.py tests/microservices/test_diff_nodir.py tests/nodir/test_archive_fs.py tests/nodir/test_archive_validation.py` | Exit `0`; `0 failed` | Block merge; fix read-surface contract drift | Browse/NoDir owner |
| Wave 4 | Pre-merge transitional lock gate | `wctl run-pytest tests/nodir/test_materialize.py -k "transition_state or missing_state_with_temp_sentinel_returns_503"` | Exit `0`; selected tests pass | Block merge; fix transitional lock semantics | Browse/NoDir owner |
| Wave 4 | Post-merge no-extraction canary gate | `wctl exec weppcloud bash -lc 'set -euo pipefail; api=http://localhost:8000; browse=http://browse:9009; payload=$(curl -fsS -X POST "$api/tests/api/create-run" -H "Content-Type: application/json" -d "{\"config\":\"dev_unit_1\"}"); RUNID=$(python -c "import json,sys; print(json.loads(sys.argv[1])[\"run\"][\"runid\"])" "$payload"); CONFIG=$(python -c "import json,sys; print(json.loads(sys.argv[1])[\"run\"][\"config\"])" "$payload"); export RUNID; WD=$(python -c "import os; from wepppy.weppcloud.utils.helpers import get_wd; print(get_wd(os.environ[\"RUNID\"]))"); trap "curl -fsS -X DELETE $api/tests/api/run/$RUNID >/dev/null 2>&1" EXIT; before=$(find "$WD/.nodir/cache" -type f 2>/dev/null | wc -l); curl -fsS "$browse/weppcloud/runs/$RUNID/$CONFIG/browse/watershed.nodir/" >/dev/null; curl -fsS "$browse/weppcloud/runs/$RUNID/$CONFIG/files/watershed.nodir/" >/dev/null; curl -fsS "$browse/weppcloud/runs/$RUNID/$CONFIG/download/watershed.nodir" -o /tmp/watershed.nodir >/dev/null; after=$(find "$WD/.nodir/cache" -type f 2>/dev/null | wc -l); test "$before" -eq "$after"'` | Exit `0`; canary run is created/cleaned and cache file count is unchanged (requires `TEST_SUPPORT_ENABLED=true`) | Revert Wave 4 merge commits; treat as P1 contract regression | Browse/NoDir owner |
| All Waves | Docs/contracts touched gate | `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` | Exit `0`; `0 errors`, `0 warnings` | Block merge until docs lint is clean | Docs owner |

## State/Contract Probes

| Probe | Command | Expected Result | Contract Invariant |
| --- | --- | --- | --- |
| Mixed state conflict (`409`) | `wctl run-pytest tests/nodir/test_resolve.py -k mixed_state` | Exit `0`; mixed-state cases pass | Public effective view fails fast on mixed state (`NODIR_MIXED_STATE`) |
| Invalid archive (`500`) | `wctl run-pytest tests/nodir/test_archive_validation.py -k "invalid or rejects"` | Exit `0`; invalid-archive cases pass | Invalid allowlisted archive fails with `NODIR_INVALID_ARCHIVE` |
| Transitional lock (`503`) | `wctl run-pytest tests/nodir/test_materialize.py -k "transition_state or missing_state_with_temp_sentinel_returns_503"` | Exit `0`; selected tests pass | Transition states/sentinels fail fast with `NODIR_LOCKED` |
| No extraction on browse/files/download | `wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_browse_security.py tests/microservices/test_diff_nodir.py` | Exit `0`; no browse/files/download regressions | Browse/files/download remain archive-native (no materialize) |
| Materialization limits/lock contention | `wctl run-pytest tests/nodir/test_materialize.py -k "limit_exceeded or lock_contention"` | Exit `0`; selected tests pass | `NODIR_LIMIT_EXCEEDED` and `NODIR_LOCKED` semantics stay explicit |

## Rollback Playbook

| Wave | Trigger Conditions | Immediate Rollback Action | Data Recovery Action | Re-Entry Criteria |
| --- | --- | --- | --- | --- |
| Wave 1 | Mixed-state creation reappears; migration/query catalog mismatch | Revert Wave 1 merge commits; halt Wave 2 | For affected runs, capture `WD/.nodir/watershed.json`; if run left thawed, execute controlled `freeze(wd, "watershed")` under maintenance lock | Foundation gate suite is green and migration parity is re-validated |
| Wave 2 | Producer mutation regressions; abnormal lock/state transitions; partial abstraction outputs | Revert Wave 2 merge commits; halt Wave 3 | For any thawed/dirty watershed roots, run controlled freeze or restore from last known-good archive | Producer gate suite is green and mutation probes pass on canary |
| Wave 3 | Archive-only export/mod/WEPP-prep failures; materialization lock/limit error spikes | Revert Wave 3 merge commits; halt Wave 4 | Clear stale cache/temp under `WD/.nodir/{cache,tmp}` only after evidence capture; recover affected runs via known-good artifact path | Consumer regression gates are green and parity checks are stable |
| Wave 4 | Browse/files/download status/code drift; serialized-path compatibility regressions | Revert Wave 4 merge commits; keep Stage D open | Restore last known-good read-surface behavior; preserve forensic artifacts for contract gap analysis | Hardening gate suite + canary probes are green with matrix-conformant statuses |

Immediate rollback command pattern (per reverted PR):
- `gh pr view <pr-number> --json mergeCommit`
- `git revert <merge_commit_sha>`
- Run the active wave gate command set before redeploy.

## Forensics Checklist

Collect this evidence before cleanup or rollback completion:
1. Run metadata and state:
- `WD/.nodir/watershed.json` (if present)
- Presence of `WD/watershed`, `WD/watershed.nodir`, `WD/watershed.thaw.tmp`, `WD/watershed.nodir.tmp`
2. Archive fingerprints and integrity:
- `stat WD/watershed.nodir` (`mtime_ns`, `size_bytes`)
- Zip validity check against the failing run artifact
3. Lock/materialization context:
- Materialization cache path snapshot: `WD/.nodir/cache/watershed/*`
- Relevant lock contention/log messages (`NODIR_LOCKED`, `NODIR_LIMIT_EXCEEDED`)
4. Surface-level evidence:
- Exact endpoint path, HTTP status, and error code for failing probes
- Command output from failed gate matrix rows
5. Mutation pipeline context (Wave 2+):
- RQ job IDs and dependency chain metadata for watershed jobs
- Abstraction/post-processing logs (`_peridot.log`, watershed controller logs)

Recommended command bundle (run-scoped):
- `WD=<run_wd> wctl exec weppcloud bash -lc 'ls -la "$WD" "$WD/.nodir"; test -f "$WD/.nodir/watershed.json" && cat "$WD/.nodir/watershed.json"; test -f "$WD/watershed.nodir" && stat "$WD/watershed.nodir"; find "$WD" -maxdepth 2 \( -name "watershed*.tmp" -o -name "watershed" \)'`

## Open Decision Log

No open blockers as of 2026-02-17.

## Phase 9 Contract Transition Addendum (2026-02-18)

This Stage D gate set remains the historical validation baseline for Phase 6a thaw/freeze rollout.

For Phase 9+ rollout, replace thaw/freeze-centric checks with projection lifecycle gates:
- Read session lifecycle checks: acquire/reuse/release/unmount.
- Mutation session lifecycle checks: acquire/mutate/commit/release and acquire/mutate/abort/release.
- Projection lock-contention checks under canonical `503 NODIR_LOCKED` behavior.
- Projection mixed unmanaged directory rejection under canonical `409 NODIR_MIXED_STATE` behavior.

Forensics additions required in Phase 9+ incident response:
- Capture projection metadata under `WD/.nodir/projections/<root>/...`.
- Capture projection lower/upper/work layout state where applicable.
- Correlate projection token/session metadata with RQ job IDs for mutation-session failures.

Cut line:
- Keep existing Phase 6 gate results unchanged.
- Add parallel Phase 9 validation rows rather than rewriting historical Phase 6 gate outcomes.
