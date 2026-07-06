# Tracker - SSURGO FC/WP Sanitization

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-07-06 05:11 UTC  
**Current phase**: Invalid-soil logging follow-up complete locally; production rerun pending redeploy
**Last updated**: 2026-07-06 15:47 UTC
**Next milestone**: Deploy the invalid-soil logging fix, then re-run `nasa-roses-202606-psbs` so affected runids queue with rebuilt soils
**Security impact**: none  
**Dedicated security review**: no  
**Security artifact**: N/A

## Task Board

### Ready / Backlog
- [ ] Deploy the invalid-soil logging fix to wepp1 worker containers.
- [ ] Re-run `nasa-roses-202606-psbs` and verify affected runids rebuild soils before WEPP hillslopes.

### In Progress
- None.

### Blocked
- None.

### Done
- [x] Created work package, tracker, active ExecPlan, and parameterization ADR draft (2026-07-06 05:11 UTC).
- [x] Confirmed WEPP source consumes `thetd2` after read via `thetd1` and later water-balance routines (2026-07-06 05:11 UTC).
- [x] Identified batch invalidation primitive as `RedisPrep.remove_timestamp(TaskEnum...)` for `build_soils` and downstream tasks (2026-07-06 05:11 UTC).
- [x] Implemented SSURGO and `WeppSoilUtil` finite/physical `fc`/`wp` guards (2026-07-06 05:35 UTC).
- [x] Added affected-mukey and 9002 conversion regression tests (2026-07-06 05:35 UTC).
- [x] Updated SSURGO docs and ADR index (2026-07-06 05:35 UTC).
- [x] Ran targeted tests through `wctl run-pytest` with 64 passed after review disposition (2026-07-06 06:15 UTC).
- [x] Ran production invalidation dry-run on wepp1; checked 39 runids, missing 0, `DRY_RUN=True` (2026-07-06 05:40 UTC).
- [x] Dispositioned subagent review findings with edge-case tests and hardened invalidation runbook (2026-07-06 06:05 UTC).
- [x] Captured deployed sanitizer proof from `rq-worker-batch` on wepp1 (artifact `wepp1-deployed-sanitizer-proof-20260706T055236Z.json`).
- [x] Confirmed active-job zero preflight for affected batch runids (artifact `wepp1-active-batch-jobs-20260706T055256Z.json`).
- [x] Executed live production invalidation on wepp1; checked 39 runids, missing 0, `DRY_RUN=False` (artifact `wepp1-invalidation-live-20260706T055437Z.jsonl`).
- [x] Ran post-invalidation read-back check; checked 39 runids, no missing runs, no remaining target timestamps (artifact `wepp1-invalidation-postcheck-20260706T055514Z.json`).
- [x] Hardened `SurgoSoilCollection.logInvalidSoils()` for worker-failure `None` entries after Omni scenario rerun exposed `AttributeError: 'NoneType' object has no attribute 'write_log'` (2026-07-06 15:47 UTC).

## Timeline

- **2026-07-06 05:11 UTC** - Package created after production triage of NASA ROSES batch WEPP SIGFPE failures.
- **2026-07-06 05:35 UTC** - Local implementation, docs, ADR, and targeted tests completed; production invalidation remains gated on deployment.
- **2026-07-06 05:40 UTC** - wepp1 invalidation dry-run succeeded with `/opt/venv/bin/python`; live invalidation not executed.
- **2026-07-06 06:05 UTC** - Subagent review disposition added rollback/audit artifacts, `rq-worker-batch` preflight gates, optional downstream timestamps, and edge-case tests.
- **2026-07-06 05:55 UTC** - wepp1 live invalidation executed from `rq-worker-batch`; postcheck confirmed all target timestamps are missing for the 39 affected runids.
- **2026-07-06 15:47 UTC** - Post-invalidation rerun path exposed invalid-soil diagnostic crash in Omni scenario soils build; local hardening now writes placeholder mukey logs for failed workers and preserves partial-success behavior.

## Decisions Log

### 2026-07-06 05:11 UTC: Sanitize at SSURGO boundary and enforce at serializer boundary
**Context**: Production SSURGO-generated `.sol` files contained `-9.9 nan` in legacy `fc wp` fields. `isfloat()` accepts `nan`, so existing checks treated non-finite values as numeric.

**Options considered**:
1. Change global `isfloat()` to reject non-finite values - too broad for one incident because callers may rely on conversion semantics.
2. Only fix SSURGO horizon generation - insufficient because existing `.sol` files and conversions can still pass through `WeppSoilUtil`.
3. Add local finite/physical guards in both SSURGO generation and WEPP soil serialization - smallest scoped fix with two defensive boundaries.

**Decision**: Add local finite and physical `fc`/`wp` validation at both boundaries.

**Impact**: SSURGO can recover invalid source water contents via Rosetta; generic serialization fails explicitly if invalid values reach it.

### 2026-07-06 05:11 UTC: Invalidate production via RedisPrep timestamps
**Context**: `batch_runner.run_batch_member()` queues tasks when `prep[TaskEnum.*] is None`. `RedisPrep.remove_timestamp()` deletes task completion timestamps and persists `redisprep.dump`.

**Options considered**:
1. Delete affected run directories - too destructive and loses diagnostics.
2. Remove only WEPP hillslope timestamps - reruns with already-generated bad soils.
3. Remove `build_soils`, `run_wepp_hillslopes`, `run_wepp_watershed`, and `run_omni_scenarios` timestamps - rebuilds bad artifacts and downstream outputs.

**Decision**: After deployment, remove timestamps for `build_soils` and downstream tasks for the 39 affected runids.

**Impact**: Re-running the batch queues only the affected runids and rebuilds soils before WEPP.

### 2026-07-06 15:47 UTC: Preserve partial-success soils build when invalid-soil logging sees failed workers
**Context**: `SurgoSoilCollection.makeWeppSoils()` records worker exceptions as `invalidSoils[mukey] = None`. The rerun path reached `logInvalidSoils()`, which iterated values and called `write_log()` unconditionally.

**Options considered**:
1. Re-raise the worker failure from `makeWeppSoils()` - broadens behavior and would stop partial-success builds that currently substitute invalid dominant mukeys when possible.
2. Drop `None` invalid-soil entries silently - avoids the crash but loses per-mukey diagnostics.
3. Write a deterministic placeholder `<mukey>.log` for `None` entries and keep detailed `WeppSoil.write_log()` output for invalid object entries.

**Decision**: Add placeholder invalid-soil logs for failed-worker `None` entries.

**Impact**: The soils build can continue to the existing dominant-soil fallback logic while preserving an on-disk diagnostic for the failed mukey.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Rosetta returns invalid values for an affected horizon | Medium | Low | Validate Rosetta output and raise `ValueError` with horizon context | Open |
| Production invalidation runs before fixed code is deployed | High | Medium | Require `rq-worker-batch` sanitizer proof and active-job zero preflight before live mutation | Closed |
| Guard rejects unusual but intentionally supplied soils | Medium | Low | Use broad physical fraction range `0 <= wp <= fc <= 1` and targeted tests | Open |
| Placeholder invalid-soil logs hide worker tracebacks | Medium | Low | Placeholder text points operators to worker exception logs; parent loop still logs traceback with mukey context | Open |

## Hardening Signal Log

- **Baseline health signals**: 39 NASA ROSES runids failed WEPP hillslopes; representative failing `.sol` rows contained `-9.9 nan`.
- **Post-change health signals**: targeted tests pass; deployed sanitizer proof passed; live invalidation postcheck passed; invalid-soil logging regression passed; production rerun remains pending after redeploy.
- **Danger signals observed**: existing `isfloat()` accepted `nan`; WEPP Fortran consumed `thetd2` after read instead of discarding it.
- **Temporary callus register**: none.
- **Softening experiments**: N/A.

## Verification Checklist

### Code Quality
- [x] Targeted tests passing (`wctl run-pytest tests/soils/test_ssurgo_fc_wp_sanitization.py tests/wepp/soils/utils/test_wepp_soil_util.py`).
- [x] Invalid-soil logging follow-up tests passing (`wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_gridded_root_creation.py tests/soils/test_ssurgo_fc_wp_sanitization.py --maxfail=1`).
- [ ] Broader tests considered (`wctl run-pytest tests --maxfail=1`).

### Security
- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security review not required.

### Documentation
- [x] SSURGO docs updated.
- [x] Work package created.
- [x] Parameterization ADR added.
- [x] ADR captures decision provenance.

### Testing
- [x] Unit test coverage for SSURGO sanitizer.
- [x] Unit/integration test coverage for `WeppSoilUtil` enforcement and 9002 conversion.
- [x] Affected mukeys covered by fixture tests.
- [x] Edge cases for `inf`, `fc > 1`, `wp > fc`, negative `wp`, and invalid Rosetta predictions covered.

### Deployment
- [x] Production invalidation procedure documented.
- [x] Invalidation executed only after fixed code is deployed.

## Progress Notes

### 2026-07-06 05:11 UTC: Package scaffold and incident findings
**Agent/Contributor**: Codex

**Work completed**:
- Created the package scaffold and ADR draft.
- Recorded production triage findings: `wepp_260606_hill` SIGFPE, `-9.9 nan` in generated soil files, affected runids, and WEPP source consumption of `thetd2`.
- Recorded timestamp-based invalidation approach for batch reruns.

**Blockers encountered**:
- Production invalidation should not be executed until the fixed code is deployed to wepp1 workers.

**Next steps**:
- Implement sanitizer and serializer enforcement.
- Add affected-mukey and 9002 conversion tests.
- Run targeted tests and update this tracker with results.

**Test results**: Pending.

### 2026-07-06 05:35 UTC: Implementation and targeted validation
**Agent/Contributor**: Codex

**Work completed**:
- Added local finite/physical `fc`/`wp` guards to `wepppy/soils/ssurgo/ssurgo.py`.
- Added `WeppSoilUtil` conversion repair and serialization enforcement in `wepppy/wepp/soils/utils/wepp_soil_util.py`.
- Added affected-mukey tests for `1385512`, `2711215`, and `78280`, plus a 9002 conversion regression.
- Updated SSURGO docs, ADR-0012, and the ADR index.
- Documented the timestamp invalidation procedure below.

**Blockers encountered**:
- Production invalidation remains blocked until the fixed code is deployed to wepp1 worker containers.

**Next steps**:
- Deploy this change to wepp1.
- Run the invalidation script with `DRY_RUN = True`, inspect output, then rerun with `DRY_RUN = False`.
- Re-run the NASA ROSES batch so missing task timestamps queue the affected runids.

**Test results**: `PATH=/home/workdir/wepppy/.venv/bin:$PATH wctl run-pytest tests/soils/test_ssurgo_fc_wp_sanitization.py tests/wepp/soils/utils/test_wepp_soil_util.py` passed: 57 passed, 2 warnings.

### 2026-07-06 06:05 UTC: Subagent review disposition
**Agent/Contributor**: Codex

**Work completed**:
- Correctness reviewer reported no blocking issues and suggested explicit edge-case coverage; added tests for non-finite/out-of-range/inverted pairs and invalid Rosetta predictions.
- Test guardian reported no in-scope test/stub issues; `wctl check-test-stubs` passed.
- Ops/security reviewer findings were accepted. The runbook now requires deployed-code proof from `rq-worker-batch`, active-job zero evidence, JSONL audit artifacts, and optional downstream timestamp invalidation for `run_geneva` and `run_path_cost_effective`.

**Blockers encountered**:
- Full-suite validation remains outside this package's current closeout because the subagent observed an unrelated OpenAPI size-budget failure in `tests/microservices/test_rq_engine_openapi_contract.py`.

**Next steps**:
- Deploy to wepp1.
- Save preflight and dry-run artifacts under `docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts/`.
- Run live invalidation only after preflight gates pass.

**Test results**: `PATH=/home/workdir/wepppy/.venv/bin:$PATH wctl run-pytest tests/soils/test_ssurgo_fc_wp_sanitization.py tests/wepp/soils/utils/test_wepp_soil_util.py` passed: 64 passed, 2 warnings.

### 2026-07-06 05:56 UTC: Production invalidation executed
**Agent/Contributor**: Codex

**Work completed**:
- Verified wepp1 was running deployed commit `b54861c5a` and that `rq-engine`, `rq-worker`, `rq-worker-batch`, and `weppcloud` were up.
- Captured deployed sanitizer proof from `rq-worker-batch`.
- Confirmed there were no active `batch` queue jobs for `nasa-roses-202606-psbs` or the 39 affected runids.
- Executed live timestamp invalidation for `build_soils`, `run_wepp_hillslopes`, `run_wepp_watershed`, `run_omni_scenarios`, `run_geneva`, and `run_path_ce`.
- Ran a postcheck that found no remaining target timestamps for the affected runids.

**Blockers encountered**:
- None.

**Next steps**:
- Re-run `nasa-roses-202606-psbs` so the affected runids queue and rebuild soils before WEPP hillslopes.

**Test results**: Production read-back check passed: 39 checked, 0 missing, 0 non-null target timestamps.

### 2026-07-06 15:47 UTC: Invalid-soil logging follow-up
**Agent/Contributor**: Codex

**Work completed**:
- Captured follow-up failure signature: `AttributeError: 'NoneType' object has no attribute 'write_log'` in `SurgoSoilCollection.logInvalidSoils()` during an Omni scenario soils rebuild.
- Confirmed the data model intentionally stores failed workers as `invalidSoils[mukey] = None`.
- Updated `logInvalidSoils()` to write a placeholder `<mukey>.log` for failed-worker `None` entries while preserving `WeppSoil.write_log()` for invalid object entries.
- Added unit coverage for a mixed invalid-soil set containing both a failed worker and a real invalid soil object.
- Updated SSURGO docs to describe parent-loop worker exception logging and placeholder invalid logs.

**Blockers encountered**:
- None locally. Production still needs this follow-up deployed before rerunning the affected batch path.

**Next steps**:
- Deploy the invalid-soil logging fix to wepp1 worker containers.
- Re-run `nasa-roses-202606-psbs` and confirm failed-worker invalid mukeys no longer abort at diagnostic logging.

**Test results**: `wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_gridded_root_creation.py tests/soils/test_ssurgo_fc_wp_sanitization.py --maxfail=1` passed: 23 passed, 2 warnings.

## Production Invalidation Procedure

Run this only after the sanitizer is deployed to wepp1 worker containers. These steps remove task timestamps for affected runids, which makes `batch_runner.run_batch_member()` queue the enabled tasks again on rerun. They intentionally do not delete run directories.

First, prove the batch worker container has the deployed sanitizer:

```bash
ssh wepp1 'cd /workdir/wepppy && wctl docker compose exec -T rq-worker-batch bash -lc "cd /workdir/wepppy && /opt/venv/bin/python -"' <<'PY'
import inspect
import json

import wepppy.soils.ssurgo.ssurgo as ssurgo
from wepppy.wepp.soils.utils import wepp_soil_util

checks = {
    "ssurgo_file": ssurgo.__file__,
    "wepp_soil_util_file": wepp_soil_util.__file__,
    "ssurgo_has_fc_wp_guard": hasattr(ssurgo, "_valid_fc_wp_pair"),
    "wepp_soil_util_has_fc_wp_guard": hasattr(wepp_soil_util, "_valid_wp_fc_pair"),
    "ssurgo_horizon_uses_guard": "_valid_fc_wp_pair" in inspect.getsource(ssurgo.Horizon.__init__),
    "serializer_uses_guard": "_require_valid_wp_fc_pair" in inspect.getsource(wepp_soil_util.WeppSoilUtil.__str__),
}
print(json.dumps(checks, indent=2, sort_keys=True))
if not all(value for key, value in checks.items() if key.endswith("_guard") or key.endswith("_uses_guard")):
    raise SystemExit("sanitizer deployment proof failed")
PY
```

Second, prove no active batch jobs can race timestamp mutation:

```bash
ssh wepp1 'cd /workdir/wepppy && wctl docker compose exec -T rq-worker-batch bash -lc "cd /workdir/wepppy && /opt/venv/bin/python -"' <<'PY'
import json

import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_listings import list_active_jobs

BATCH_NAME = "nasa-roses-202606-psbs"
RUNIDS = {
    "OR,WA-101", "OR,WA-99", "OR-11", "OR-13", "OR-15", "OR-154",
    "OR-16", "OR-160", "OR-17", "OR-184", "OR-185", "OR-19",
    "OR-194", "OR-195", "OR-20", "OR-202", "OR-206", "OR-21",
    "OR-25", "OR-26", "OR-28", "OR-30", "OR-33", "OR-48", "OR-5",
    "OR-6", "OR-7", "OR-8", "WA-156", "WA-174", "WA-25", "WA-36",
    "WA-37", "WA-38", "WA-39", "WA-77", "WA-78", "WA-80", "WA-82",
}

with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
    active = list_active_jobs(redis_conn, queue_names=("batch",))

hits = [
    job for job in active
    if job.get("runid") in RUNIDS
    or job.get("runid") == BATCH_NAME
    or BATCH_NAME in str(job.get("description") or "")
]
print(json.dumps(hits, indent=2, sort_keys=True))
if hits:
    raise SystemExit("active batch jobs block invalidation")
print("active_batch_jobs_for_affected_runs=0")
PY
```

Finally, run the timestamp invalidation script. `DRY_RUN=True` does not remove timestamps, but `RedisPrep.getInstance()` may still materialize harmless Redis/dump load state, so treat it as non-destructive rather than no-write. Save both dry-run and live output as JSONL artifacts.

```bash
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
        print(json.dumps({
            "event": "missing_run",
            "runid": runid,
            "wd": str(wd),
            "dry_run": DRY_RUN,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
        }, sort_keys=True))
        continue
    prep = RedisPrep.getInstance(str(wd))
    before = {str(task): prep[str(task)] for task in TASKS}
    if not DRY_RUN:
        for task in TASKS:
            prep.remove_timestamp(task)
    after = {str(task): prep[str(task)] for task in TASKS}
    checked += 1
    print(json.dumps({
        "event": "timestamp_invalidation",
        "runid": runid,
        "wd": str(wd),
        "dry_run": DRY_RUN,
        "before": before,
        "after": after,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }, sort_keys=True))

print(json.dumps({
    "event": "summary",
    "checked": checked,
    "missing": missing,
    "dry_run": DRY_RUN,
    "ts_utc": datetime.now(timezone.utc).isoformat(),
}, sort_keys=True))
PY
test "${PIPESTATUS[0]}" -eq 0
```

The dry-run on 2026-07-06 checked all 39 runids with none missing. At that time `build_soils` had timestamps and `run_wepp_hillslopes`, `run_wepp_watershed`, and `run_omni_scenarios` were already missing for the affected runids.

The live invalidation on 2026-07-06 checked all 39 runids with none missing and `DRY_RUN=False`. The postcheck reported `checked=39`, `missing=[]`, `non_null=[]`, and `ok=true`. The affected runids are now retry-eligible for soil rebuild and downstream derived work. `run_omni_contrasts` is intentionally excluded because batch completion excludes it and contrast rerun is a separate decision.
