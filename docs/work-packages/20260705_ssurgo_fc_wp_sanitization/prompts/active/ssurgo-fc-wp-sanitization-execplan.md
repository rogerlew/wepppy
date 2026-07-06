# Sanitize SSURGO FC/WP Values and Requeue Affected Runs

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

WEPPcloud users should be able to rerun the affected NASA ROSES batch without WEPP hillslope jobs crashing on soil files containing `nan` or sentinel negative field-capacity and wilting-point values. Field capacity (`fc`) and wilting point (`wp`) are water-content fractions used by WEPP to initialize and update soil water. After this change, SSURGO-derived soils with bad source water contents are repaired with Rosetta estimates when possible, and any invalid values that survive to the generic serializer fail explicitly before a WEPP binary sees them.

## Progress

- [x] (2026-07-06 05:11 UTC) Investigated production failure signature and affected runids.
- [x] (2026-07-06 05:11 UTC) Confirmed WEPP source consumes `thetd2` after reading soil files.
- [x] (2026-07-06 05:11 UTC) Identified `RedisPrep.remove_timestamp()` as the safe invalidation primitive.
- [x] (2026-07-06 05:11 UTC) Created work package, tracker, and ADR draft.
- [x] (2026-07-06 05:35 UTC) Implemented SSURGO `fc`/`wp` sanitizer.
- [x] (2026-07-06 05:35 UTC) Implemented `WeppSoilUtil` `fc`/`wp` enforcement and 9002 appended-value validation.
- [x] (2026-07-06 05:35 UTC) Added affected-mukey and 9002 conversion tests.
- [x] (2026-07-06 05:35 UTC) Updated durable SSURGO docs.
- [x] (2026-07-06 05:35 UTC) Ran targeted tests and recorded results.
- [x] (2026-07-06 05:35 UTC) Provided production invalidation command, gated on deployment.
- [x] (2026-07-06 05:52 UTC) Confirmed sanitizer deployed to wepp1 `rq-worker-batch`.
- [x] (2026-07-06 05:40 UTC) Ran production invalidation dry-run on wepp1 without timestamp deletion.
- [x] (2026-07-06 06:05 UTC) Dispositioned subagent review findings with edge-case tests and hardened invalidation runbook.
- [x] (2026-07-06 05:55 UTC) Executed production invalidation on wepp1 after deployment and confirmed target timestamps were removed.

## Surprises & Discoveries

- Observation: WEPP source does not merely read and discard `thetd2`; it aggregates `thetd2` into `thetd1`, and later routines use `thetd1`/`thetfc` in water-balance calculations.
  Evidence: `/workdir/wepp-forest_260430_baseline/src/input.for` reads `thetd2`; `/workdir/wepp-forest_260430_baseline/src/tilage.for` transfers `thetd1` into `thetdr`/`thetfc`.
- Observation: `wepppy.all_your_base.isfloat()` returns true for `nan`, so horizon code that checks only `isfloat()` can still serialize non-finite values.
  Evidence: `isfloat()` only attempts `float(f)` and does not call `math.isfinite()`.
- Observation: Batch retry eligibility is timestamp-based.
  Evidence: `wepppy/nodb/batch_runner.py` queues enabled tasks when the corresponding `RedisPrep` timestamp is missing; `RedisPrep.remove_timestamp()` deletes the timestamp and persists `redisprep.dump`.

## Decision Log

- Decision: Keep the global `isfloat()` behavior unchanged and add local finite/physical guards for `fc`/`wp`.
  Rationale: Changing `isfloat()` globally could change unrelated callers. The failing path is narrower and needs explicit water-content semantics.
  Date/Author: 2026-07-06 / Codex
- Decision: Valid `fc`/`wp` must satisfy `0 <= wp <= fc <= 1` and both values must be finite.
  Rationale: The values are volumetric water-content fractions in WEPP soil files. This rejects `nan`, `inf`, sentinel negatives such as `-9.9`, impossible values above saturation fraction, and inverted pairs.
  Date/Author: 2026-07-06 / Codex
- Decision: For production rerun, invalidate `build_soils` plus downstream WEPP and OMNI timestamps, not whole run directories.
  Rationale: This preserves diagnostics and forces rebuilt soil inputs before hillslope rerun.
  Date/Author: 2026-07-06 / Codex

## Outcomes & Retrospective

Local implementation is complete. The sanitizer now repairs invalid SSURGO-generated `fc`/`wp` pairs using Rosetta, and `WeppSoilUtil` repairs invalid legacy values during conversion while rejecting invalid values at final serialization. Targeted tests passed in the project Docker environment. Subagent review findings were dispositioned by adding edge-case tests and strengthening the production invalidation runbook. Production invalidation was executed on wepp1 after deployed-code and active-job preflight gates passed; the postcheck confirmed all target timestamps were missing for the 39 affected runids.

## Context and Orientation

`wepppy/soils/ssurgo/ssurgo.py` builds WEPP 7778 soil files from SSURGO map unit keys, called mukeys. A `Horizon` wraps one SSURGO horizon row and computes WEPP-ready fields. `field_cap` and `wilt_pt` are written as the legacy `fc wp` columns in 7778 soil rows.

`wepppy/wepp/soils/utils/wepp_soil_util.py` parses existing `.sol` files, migrates them between WEPP soil versions, and serializes them. For datver 9002 and later, it writes the legacy 7778-style row and appends van Genuchten/Rosetta parameters, including appended `wp` and `fc`. Both the legacy columns and appended values must be finite.

The production failure was observed under `/wc1/batch/nasa-roses-202606-psbs/`. Failed hillslope runs used `wepp_260606_hill` and returned `-8` with a Fortran floating-point exception. Affected rows had values like `-9.9 nan` in the legacy `fc wp` columns.

## Plan of Work

First, add narrow helper functions in `ssurgo.py` to coerce candidate water-content values to finite floats, validate the pair, and recover invalid pairs from Rosetta. Horizon construction should still prefer SSURGO `wthirdbar_r` and `wfifteenbar_r` adjusted for rock content when the resulting pair is physically valid. If either value is invalid, recompute both `field_cap` and `wilt_pt` from the already selected Rosetta model and record a build note explaining the replacement.

Second, add matching helper functions in `wepp_soil_util.py`. Use them in `_compute_rosetta_wp_fc()`, in `to7778()` when deciding whether to repair parsed source values, and in `__str__()` before writing each horizon row. For datver 9002 and later, validate the appended Rosetta `wp`/`fc` prediction before formatting it.

Third, add tests. The SSURGO test should use affected production mukeys, including `1385512`, `2711215`, and `78280`, in a hermetic fixture that injects invalid `wthirdbar_r`/`wfifteenbar_r` values and a fake Rosetta3 predictor. It should assert generated 7778 soil rows contain finite `fc`/`wp` and no `nan`. The `WeppSoilUtil` tests should assert invalid legacy `fc`/`wp` values are not serialized, and that converting an affected-mukey-style soil to 9002 produces finite legacy and appended values.

Fourth, update `wepppy/soils/ssurgo/ssurgo.md`, `docs/adrs/README.md`, this ExecPlan, and the package tracker. Run targeted tests through `wctl run-pytest`.

Finally, provide the wepp1 invalidation command. It must remove `build_soils`, `run_wepp_hillslopes`, `run_wepp_watershed`, and `run_omni_scenarios` timestamps for the 39 affected runids after the fixed code is deployed to worker containers.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Patch `wepppy/soils/ssurgo/ssurgo.py`.
2. Patch `wepppy/wepp/soils/utils/wepp_soil_util.py`.
3. Add `tests/soils/test_ssurgo_fc_wp_sanitization.py` and extend `tests/wepp/soils/utils/test_wepp_soil_util.py`.
4. Patch docs and ADR index.
5. Run:

       wctl run-pytest tests/soils/test_ssurgo_fc_wp_sanitization.py tests/wepp/soils/utils/test_wepp_soil_util.py

   Observed 2026-07-06:

       64 passed, 2 warnings in 11.02s

6. Before production invalidation, confirm deployed code on wepp1 includes the sanitizer. Then execute a timestamp invalidation script inside the worker container using the affected runid list.

## Validation and Acceptance

The targeted tests must pass. The SSURGO affected-mukey test must fail before the sanitizer because it would serialize `nan` or a sentinel negative value, and pass after the sanitizer by showing finite `fc`/`wp` values. The 9002 conversion test must show the legacy columns and appended Rosetta values are finite, with no `nan`, `inf`, or `-9.9` in serialized soil rows.

Production acceptance requires the affected runids to become retry-eligible after timestamp invalidation and to rebuild soils before rerunning WEPP hillslopes. The invalidation step is complete: fixed code was confirmed in `rq-worker-batch`, live timestamp deletion checked 39 runids with none missing, and postcheck found no remaining target timestamps. The batch rerun and rebuilt-output verification remain the next operational step.

## Idempotence and Recovery

The code and test edits are additive and can be reapplied normally by git. The production invalidation script is idempotent: removing an already missing task timestamp leaves the run retry-eligible. Do not delete run directories. If invalidation is performed too early, deploy the fix and rerun the same invalidation script to ensure `build_soils` remains missing.

## Artifacts and Notes

Affected runids discovered during triage:

    OR,WA-101 OR,WA-99 OR-11 OR-13 OR-15 OR-154 OR-16 OR-160 OR-17 OR-184 OR-185 OR-19 OR-194 OR-195 OR-20 OR-202 OR-206 OR-21 OR-25 OR-26 OR-28 OR-30 OR-33 OR-48 OR-5 OR-6 OR-7 OR-8 WA-156 WA-174 WA-25 WA-36 WA-37 WA-38 WA-39 WA-77 WA-78 WA-80 WA-82

Representative affected mukeys from bounded production probes include `1385512`, `2711215`, and `78280`.

Production invalidation requires three steps. First prove the deployed sanitizer from `rq-worker-batch`, because that is the container family that executes the batch rerun. Second prove there are no active `batch` queue jobs for the batch or affected runids. Third run the JSONL-emitting timestamp script with `DRY_RUN=True`, save the artifact, inspect it, then rerun with `DRY_RUN=False` only after the artifact is satisfactory.

    ARTIFACT_DIR="docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts"
    mkdir -p "$ARTIFACT_DIR"
    STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
    ARTIFACT="$ARTIFACT_DIR/wepp1-invalidation-dry-run-${STAMP}.jsonl"
    ssh wepp1 'cd /workdir/wepppy && wctl docker compose exec -T rq-worker-batch bash -lc "cd /workdir/wepppy && /opt/venv/bin/python -"' <<'PY' | tee "$ARTIFACT"
    from datetime import datetime, timezone
    import json
    from pathlib import Path

    from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

    DRY_RUN = True
    BATCH_RUNS = Path("/wc1/batch/nasa-roses-202606-psbs/runs")
    RUNIDS = [
        "OR,WA-101", "OR,WA-99", "OR-11", "OR-13", "OR-15", "OR-154",
        "OR-16", "OR-160", "OR-17", "OR-184", "OR-185", "OR-19",
        "OR-194", "OR-195", "OR-20", "OR-202", "OR-206", "OR-21",
        "OR-25", "OR-26", "OR-28", "OR-30", "OR-33", "OR-48", "OR-5",
        "OR-6", "OR-7", "OR-8", "WA-156", "WA-174", "WA-25", "WA-36",
        "WA-37", "WA-38", "WA-39", "WA-77", "WA-78", "WA-80", "WA-82",
    ]
    TASKS = [
        TaskEnum.build_soils,
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
        TaskEnum.run_omni_scenarios,
        TaskEnum.run_geneva,
        TaskEnum.run_path_cost_effective,
    ]

    checked = 0
    missing = 0
    for runid in RUNIDS:
        wd = BATCH_RUNS / runid
        if not wd.is_dir():
            missing += 1
            print(json.dumps({"event": "missing_run", "runid": runid, "wd": str(wd), "dry_run": DRY_RUN, "ts_utc": datetime.now(timezone.utc).isoformat()}, sort_keys=True))
            continue
        prep = RedisPrep.getInstance(str(wd))
        before = {str(task): prep[str(task)] for task in TASKS}
        if not DRY_RUN:
            for task in TASKS:
                prep.remove_timestamp(task)
        after = {str(task): prep[str(task)] for task in TASKS}
        checked += 1
        print(json.dumps({"event": "timestamp_invalidation", "runid": runid, "wd": str(wd), "dry_run": DRY_RUN, "before": before, "after": after, "ts_utc": datetime.now(timezone.utc).isoformat()}, sort_keys=True))

    print(json.dumps({"event": "summary", "checked": checked, "missing": missing, "dry_run": DRY_RUN, "ts_utc": datetime.now(timezone.utc).isoformat()}, sort_keys=True))
    PY
    test "${PIPESTATUS[0]}" -eq 0

Set `DRY_RUN = False` only after fixed worker code is deployed, active-job preflight is clean, and the dry-run artifact confirms the intended runids and prior timestamp values. The artifact is the rollback/audit source for restoring deleted timestamp values if needed.

Dry-run evidence from 2026-07-06:

    checked=39 missing=0 DRY_RUN=True

The dry-run showed `build_soils` still timestamped and the downstream WEPP/OMNI task timestamps already missing for the affected runids.

Live invalidation evidence from 2026-07-06:

    deployed proof artifact: docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts/wepp1-deployed-sanitizer-proof-20260706T055236Z.json
    active-job preflight artifact: docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts/wepp1-active-batch-jobs-20260706T055256Z.json
    dry-run artifact: docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts/wepp1-invalidation-dry-run-20260706T055321Z.jsonl
    live artifact: docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts/wepp1-invalidation-live-20260706T055437Z.jsonl
    postcheck artifact: docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts/wepp1-invalidation-postcheck-20260706T055514Z.json

The live invalidation checked 39 runids, found none missing, and removed target timestamps for `build_soils`, `run_wepp_hillslopes`, `run_wepp_watershed`, `run_omni_scenarios`, `run_geneva`, and `run_path_ce`. The postcheck reported `checked=39`, `missing=[]`, `non_null=[]`, and `ok=true`.

## Interfaces and Dependencies

No new external dependencies are allowed. Use the existing `rosetta.Rosetta2` and `rosetta.Rosetta3` classes already imported by SSURGO and imported lazily by `WeppSoilUtil`.

Required local helper behavior:

    _is_finite_float(value) -> bool
    _as_finite_float(value, name=...) -> float
    _is_valid_fc_wp(field_cap, wilt_pt) -> bool
    _require_valid_fc_wp(field_cap, wilt_pt, context=...) -> tuple[float, float]

Names may differ if the implementation keeps the same semantics.

## Revision Notes

2026-07-06: Initial ExecPlan created from production investigation and user request. The plan records the sanitizer scope, test requirements, and production invalidation gate.

2026-07-06: Updated after local implementation and targeted validation. The plan now records passing tests and the exact production invalidation script.

2026-07-06: Updated after wepp1 dry-run. The command now uses `/opt/venv/bin/python` inside `rq-worker`, because plain `python` did not load the application dependencies in that container.

2026-07-06: Updated after subagent review. The invalidation procedure now uses `rq-worker-batch`, requires deployed-code and active-job preflight gates, emits JSONL for audit/rollback, and includes optional `run_geneva` and `run_path_cost_effective` downstream timestamps while still excluding `run_omni_contrasts`.

2026-07-06: Updated after production invalidation. wepp1 deployed-code proof and active-job preflight passed, live invalidation checked 39 runids with none missing, and postcheck confirmed all target timestamps were removed.
