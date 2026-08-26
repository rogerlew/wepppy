# Runtime Station Drift Review Disposition

**Date**: 2026-08-05 23:19 UTC
**Change**: Preserve runtime-resolved batch climate stations during base-project drift checks
**Reviewer**: Independent reviewer agent `/root/batch_runtime_station_review`
**Author/disposition owner**: Codex

## Scope

The review covered the complete change against `origin/master`, with emphasis on:

- semantic equivalence between a base `null`/`FindClosestAtRuntime` station policy and a leaf's resolved station/`Closest` state;
- parity between read-only retry classification and worker-side resync;
- current, legacy, and raw-integer `ClimateStationMode` serialization;
- fail-closed handling of malformed or foreign serialized enums;
- preservation of explicit base station-policy drift; and
- regression coverage, documentation, queue/security scope, and timestamp invalidation.

## Findings and Dispositions

### Medium: Serialized enum constructor was not validated

**Finding**: The first implementation accepted any `py/reduce` constructor when its tuple contained `-1` or `0`. A foreign or malformed enum could therefore suppress station drift.

**Disposition**: Resolved. The parser now requires the exact current `wepppy.nodb.core.climate.ClimateStationMode` constructor for the current two-element representation, or the exact legacy `wepppy.nodb.climate.ClimateStationMode` constructor for the legacy five-element representation. It also validates constructor keys, tuple structure, integer type, and legacy null trailing fields. Unknown structures fail closed as drift.

**Regression evidence**: `test_classify_batch_run_state_rejects_foreign_runtime_station_mode`.

### Medium: Legacy five-element jsonpickle representation was rejected

**Finding**: Legacy persisted NoDb files use a five-element `py/reduce` and the old module path. Requiring the current two-element form would leave legacy runtime-resolved leaves falsely stale.

**Disposition**: Resolved. The parser accepts the verified legacy shape in addition to the current shape and deliberate raw-integer compatibility.

**Regression evidence**: `test_classify_batch_run_state_accepts_compatible_runtime_station_modes`, parameterized for `legacy` and `raw`, plus the current-format lifecycle test.

## Post-Fix Confirmation

The same reviewer confirmed both medium findings resolved and reported no new findings. The reviewer also confirmed that classifier and resync share the same comparison helper, explicit base station changes remain drift, and the patch does not alter authentication, locking, queue topology, or error contracts.

Residual risk is low. Mixed current/legacy base-leaf representations are handled because each side is decoded independently, although every mixed pair is not separately parameterized. Unknown future jsonpickle representations intentionally fail closed as drift.

## Validation

- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`: 29 passed.
- `wctl run-pytest tests --maxfail=1`: 5,839 passed, 61 skipped.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`: passed, net delta `+0`.
- Batch Runner work-package and README documentation lint: passed before final disposition edits and rerun at handoff.
- `git diff --check`: passed before final disposition edits and rerun at handoff.

## Final Disposition

Accepted after fixes. No unresolved review findings remain. Production deployment and recovery execution remain separate operator actions.
