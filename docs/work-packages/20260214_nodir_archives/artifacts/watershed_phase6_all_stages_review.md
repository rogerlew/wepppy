# Watershed Phase 6 All-Stages Review (A-D)

Review date: 2026-02-17
Scope: Stage A touchpoints, Stage B mutation surface, Stage C execution waves, Stage D validation/rollout gates, and alignment with NoDir contracts.

## Findings (Severity-Ordered)

1. **High**: Stage B mutation classification for `build_channels_rq`, `set_outlet_rq`, and `build_subcatchments_rq` conflicted with the behavior-matrix watershed RQ contract (`materialize(root)+freeze` for archive form).
  - Status: closed; Stage B rows now explicitly align to `materialize(root)+freeze`.
2. **High**: Wave 4 post-merge no-extraction canary gate was template-driven (`RUNID`/`CONFIG`/`WD`/auth placeholders), so it was not executable as written across environments.
  - Status: closed; Stage D now uses a test-support-backed create-run/delete-run workflow with concrete executable command.
3. **Medium**: Wave 4 cross-surface failure ownership (`browse` + `dtale` + `gdalinfo`) was ambiguous.
  - Status: closed; single accountable owner set to `Browse/NoDir owner` in Stage D gate rows.
4. **Medium**: Stage B included `test_run_rq`, but Stage A/Stage C naming did not explicitly call out this direct/smoke mutation path, making traceability indirect.
  - Status: closed in prior pass (Stage A and Stage C labels now include `test_run_rq`).
5. **Medium**: Stage D had no command explicitly isolating legacy abstraction internals (`_topaz_abstract_watershed`, peridot post-processing) as first-class checks.
  - Status: closed; Stage D now contains an explicit Wave 2 legacy abstraction internals gate command.
6. **Low**: Stage D forensic command bundle had `find` precedence ambiguity that could under/over-report artifacts.
  - Status: closed in prior pass.

## Cross-Stage Coverage Matrix

| Touchpoint | Stage A Status | Stage C Wave | Stage D Gate | Coverage Result | Gap |
| --- | --- | --- | --- | --- | --- |
| Browse HTML handler | archive-ready | Wave 4 | W4 pre: browse/files/download + transitional lock; W4 post: no-extraction canary | Pass | None |
| Core WEPP watershed input prep | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| D-Tale bridge | archive-ready | Wave 4 | W4 pre: browse/files/download + transitional lock; W4 post: no-extraction canary | Pass | None |
| Download API | archive-ready | Wave 4 | W4 pre: browse/files/download + transitional lock; W4 post: no-extraction canary | Pass | None |
| DuckDB watershed query helpers | archive-ready | Wave 1 | W1 pre: state/thaw + sidecar/migration; W1 post: migration regression | Pass | None |
| ERMiT export | blocked | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Partial | Stage A blocker remains open until assigned wave work completes |
| Files JSON API | archive-ready | Wave 4 | W4 pre: browse/files/download + transitional lock; W4 post: no-extraction canary | Pass | None |
| GDAL info endpoint | archive-ready | Wave 4 | W4 pre: browse/files/download + transitional lock; W4 post: no-extraction canary | Pass | None |
| GeoPackage export | archive-ready | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Legacy TOPAZ abstraction writes | thaw-required | Wave 2 | W2 pre: route/mutation + legacy abstraction internals + lock/transition; W2 post: producer regression | Pass | None |
| Network reads from `wat_dir` | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| OMNI scenario clone (`watershed` root handling) | archive-ready | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Parquet-backed watershed summaries | archive-ready | Wave 1 | W1 pre: state/thaw + sidecar/migration; W1 post: migration regression | Pass | None |
| Path-CE data loader | archive-ready | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Peridot post-processing outputs | thaw-required | Wave 2 | W2 pre: route/mutation + legacy abstraction internals + lock/transition; W2 post: producer regression | Pass | None |
| Peridot watershed migration | blocked | Wave 1 | W1 pre: state/thaw + sidecar/migration; W1 post: migration regression | Partial | Stage A blocker remains open until assigned wave work completes |
| Prep-details export | archive-ready | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Project bootstrap orchestration | thaw-required | Wave 2 | W2 pre: route/mutation + legacy abstraction internals + lock/transition; W2 post: producer regression | Partial | Direct/smoke `test_run_rq` path is covered indirectly via Wave 2 route gates |
| Query-engine watershed cataloging | thaw-required | Wave 1 | W1 pre: state/thaw + sidecar/migration; W1 post: migration regression | Pass | None |
| RHEM hillslope prep | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| RQ-engine watershed routes | thaw-required | Wave 2 | W2 pre: route/mutation + legacy abstraction internals + lock/transition; W2 post: producer regression | Pass | None |
| SWAT downstream topology mapping | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Salvage flowpath utility | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Slope path helpers | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Structure persistence and `_structure` serialization | blocked | Wave 4 | W4 pre: browse/files/download + transitional lock; W4 post: no-extraction canary | Partial | Stage A blocker remains open until assigned wave work completes |
| WEPP watershed prep/run queue flow | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |
| Watershed RQ mutation jobs | thaw-required | Wave 2 | W2 pre: route/mutation + legacy abstraction internals + lock/transition; W2 post: producer regression | Pass | None |
| Watershed abstraction engine (`WatershedAbstraction`) | thaw-required | Wave 2 | W2 pre: route/mutation + legacy abstraction internals + lock/transition; W2 post: producer regression | Pass | None |
| Watershed abstraction orchestration | thaw-required | Wave 2 | W2 pre: route/mutation + legacy abstraction internals + lock/transition; W2 post: producer regression | Pass | None |
| Watershed controller bootstrap (`wat_dir` mkdir) | blocked | Wave 1 | W1 pre: state/thaw + sidecar/migration; W1 post: migration regression | Partial | Stage A blocker remains open until assigned wave work completes |
| Watershed migration utility | archive-ready | Wave 1 | W1 pre: state/thaw + sidecar/migration; W1 post: migration regression | Pass | None |
| WinWEPP export | thaw-required | Wave 3 | W3 pre: materialization/export + mods/WEPP; W3 post: consumer regression | Pass | None |

## Contract Conformance Check

| Contract Invariant | Stage Mapping | Evidence | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| Mixed-state effective view must fail fast with `409 NODIR_MIXED_STATE`. | Stage B read-path rules; Stage D probes. | `nodir_behavior_matrix.md` mixed-state rules; Stage D `test_resolve.py -k mixed_state`. | Pass | Matrix and gates align on `409`. |
| Invalid allowlisted archive must fail with `500 NODIR_INVALID_ARCHIVE` for archive-as-directory operations. | Stage B read-path rules; Stage D probes. | `nodir_behavior_matrix.md`; Stage D `test_archive_validation.py -k "invalid or rejects"`. | Pass | Error contract is explicit and test-gated. |
| Transitional states/sentinels must fail fast with `503 NODIR_LOCKED`. | Stage B orchestration and read-path notes; Stage D probes. | `nodir-thaw-freeze-contract.md` + `nodir_materialization_contract.md`; Stage D transitional lock gate. | Pass | Lock semantics are consistently mapped. |
| Browse/files/download must remain extraction-free. | Stage B read-path classification; Stage D Wave 4 gates. | `nodir_behavior_matrix.md` + Stage D browse/files/download test rows. | Pass | Read surfaces stay native. |
| Archive-form root mutation must use maintenance lock + thaw/modify/freeze sequence. | Stage B canonical mutation table; Stage C Wave 2. | `nodir-thaw-freeze-contract.md`; Stage B lock/state columns. | Pass | Mutation contract is documented and wave-owned. |
| Public request surfaces must not perform thaw/freeze cleanup. | Stage B orchestration rollback notes; Stage D forensics/rollback rules. | `nodir-thaw-freeze-contract.md` transitional sentinel rules. | Pass | Cleanup remains maintenance-only. |
| Parquet sidecars remain WD-level and should not be extracted from `.nodir`. | Stage A archive-ready parquet touchpoints; Stage B read-path table; Stage D Wave 1 gates. | `nodir-contract-spec.md` sidecar mapping; Stage D sidecar tests. | Pass | Sidecar-first policy is consistent across stages. |
| Watershed RQ group archive-form behavior must be consistent between behavior matrix and mutation-surface classification. | Stage B mutation table; Stage C Wave 2; behavior matrix backend tools section. | `nodir_behavior_matrix.md` watershed RQ group row and Stage B entries for `build_channels`/`set_outlet`/`build_subcatchments`. | Pass | Stage B entries now align explicitly to `materialize(root)+freeze`. |
| Wave 4 post-merge gate must be executable in a standardized way. | Stage D executable matrix + open decisions. | Stage D Wave 4 canary command using `tests/api/create-run` bootstrap and cleanup. | Pass | Canonical canary input/auth source is standardized through the test-support flow. |

## Gate Executability Check

| Gate Command | Exists | Executable As Written | Wave | Action Needed |
| --- | --- | --- | --- | --- |
| `wctl run-pytest tests/nodir/test_state.py tests/nodir/test_thaw_freeze.py tests/nodir/test_resolve.py` | Yes | Yes | Wave 1 | None. |
| `wctl run-pytest tests/nodir/test_parquet_sidecars.py tests/nodir/test_parquet_precedence_fs.py tests/tools/test_migrations_parquet_backfill.py tests/query_engine/test_activate.py` | Yes | Yes | Wave 1 | None. |
| `wctl run-pytest tests/tools/test_migrations_runner.py tests/tools/test_migrations_parquet_backfill.py` | Yes | Yes | Wave 1 | None. |
| `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py` | Yes | Yes | Wave 2 | None. |
| `wctl run-pytest tests/topo/test_peridot_runner_wait.py tests/topo/test_topaz_vrt_read.py tests/test_wepp_top_translator.py` | Yes | Yes | Wave 2 | None. |
| `wctl run-pytest tests/nodir/test_state.py tests/nodir/test_thaw_freeze.py tests/nodir/test_resolve.py` | Yes | Yes | Wave 2 | None. |
| `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py tests/topo/test_peridot_runner_wait.py tests/topo/test_topaz_vrt_read.py tests/test_wepp_top_translator.py tests/nodir/test_thaw_freeze.py` | Yes | Yes | Wave 2 | None. |
| `wctl run-pytest tests/nodir/test_materialize.py tests/microservices/test_rq_engine_export_routes.py tests/microservices/test_browse_dtale.py` | Yes | Yes | Wave 3 | None. |
| `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_swat_interchange.py tests/wepp/test_wepp_run_watershed_interchange_options.py tests/weppcloud/routes/test_rhem_bp.py` | Yes | Yes | Wave 3 | Add salvage-flowpath-specific coverage if parity issues appear. |
| `wctl run-pytest tests/nodir/test_materialize.py tests/microservices/test_rq_engine_export_routes.py tests/nodb/mods/test_swat_interchange.py` | Yes | Yes | Wave 3 | None. |
| `wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_browse_security.py tests/microservices/test_diff_nodir.py tests/nodir/test_archive_fs.py tests/nodir/test_archive_validation.py` | Yes | Yes | Wave 4 | None. |
| `wctl run-pytest tests/nodir/test_materialize.py -k "transition_state or missing_state_with_temp_sentinel_returns_503"` | Yes | Yes | Wave 4 | None. |
| `wctl exec weppcloud bash -lc '<create-run + browse/files/download no-extraction probe + delete-run>'` | Yes | Yes | Wave 4 | None. |
| `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` | Yes | Yes | All Waves | None. |

## Rollback/Forensics Sufficiency

- Wave-level rollback rows exist for Waves 1-4 and include explicit stop/revert actions.
- Stage D forensic checklist captures required root state artifacts (`.json`, `.tmp`, archive fingerprint, gate output, and RQ chain context).
- Coverage is sufficient for operational triage and execution; Wave 4 canary inputs and ownership are now explicit and executable.

## Blocking Gaps

No open blocking gaps for the Phase 6a A-D planning package.

## Recommended Doc Fixes (Minimal)

Applied in this review:
1. Stage B: watershed RQ subgroup entries (`build_channels_rq`, `set_outlet_rq`, `build_subcatchments_rq`) are now explicitly aligned to behavior-matrix archive-form mutation contract (`materialize(root)+freeze`).
2. Stage D: Wave 2 now includes a dedicated legacy abstraction internals gate command (`peridot`/`topaz`/translator tests).
3. Stage D: Wave 4 no-extraction canary gate is now executable as written using standardized `tests/api/create-run` bootstrap and cleanup.
4. Stage D: Wave 4 cross-surface failure ownership is now single-owner (`Browse/NoDir owner`).

No additional blocking doc fixes are required before Phase 6a execution.

## Phase 6a Execution Completion (2026-02-17)

Implemented wave outcomes:
- Wave 1: constructor mixed-state blocker removed (`Watershed.__init__` no eager `wat_dir` creation).
- Wave 2: watershed RQ mutation owners now execute under shared root mutation orchestration (`mutate_root` in `project_rq.py`).
- Wave 3: watershed producer/consumer gate bundle revalidated for NoDir materialization/export interactions.
- Wave 4: serialized-path cleanup completed for `_structure` persistence (`wepppy/nodb/core/watershed.py`) and route preflight/hardening verified.

Execution evidence:
- `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py tests/topo/test_peridot_runner_wait.py tests/topo/test_topaz_vrt_read.py tests/test_wepp_top_translator.py` -> `34 passed`.
- `wctl run-pytest tests/nodir/test_materialize.py tests/microservices/test_rq_engine_export_routes.py tests/nodb/mods/test_swat_interchange.py` -> `28 passed`.
- `wctl run-pytest tests/nodir` -> `90 passed`.

Final watershed Phase 6a verdict:
- `complete`: yes.
- `validated`: yes (wave-targeted gates passed with canonical NoDir status/code expectations preserved).

## Phase 9 Contract Transition Addendum (2026-02-18)

This all-stages review remains valid for Phase 6a execution and validation under the thaw/freeze-era contract.

Superseded assumptions for Phase 9+ work:
- Stage B mutation lifecycle wording (`thaw/modify/freeze`) is replaced by projection mutation-session lifecycle (`acquire -> callback -> commit|abort -> release`).
- Stage C wave sequencing must now include projection utility delivery before broad consumer migration.
- Stage D validation should include projection metadata and projection lifecycle failure probes in addition to canonical status-code checks.

Historical integrity note:
- Coverage findings, severity ordering, and completion verdicts in this document should remain unchanged as the historical Phase 6a record.
