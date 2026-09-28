# WRT-01 independent contract correctness review

Reviewer: independent Codex correctness agent. Date: 2026-09-28.
Disposition: **approved for implementation; no blocking findings**.
Scope: preimplementation contract only; runtime conformance remains unverified.

Reviewed WRT-01 in `docs/schemas/wepp-run-input-contract.md`, ADR-0076,
the package/checkpoint/active plan, empirical assessment, all four enqueue
functions in `wepppy/rq/wepp_rq_pipeline.py`, the matching RQ entry points,
controller properties, and owned watershed run-file generators/templates.

## Correctness and compatibility

- The integer formula is equivalent to the operator-approved 0.05 seconds per
  hillslope-year. It yields 97,200 seconds for 1,000 years and 1,908 hillslopes,
  preserves the 43,200-second floor and preserves larger pipeline allowances.
- All four continuous paths are identified. Requiring validation before their
  first enqueue prevents invalid workload from leaving partial child graphs.
  Unrelated stage allowances and dependency edges remain unchanged.
- Preparation uses the same climate years used by `_make_watershed_run` and the
  watershed hill count. No-prep uses checked-out input instead of stale NoDb
  counts, consistent with the existing bootstrap no-prep contract.
- `watershed.template` places the hill count after the optional master-pass
  filename and simulation years at the end. Legacy and modern prompt layouts
  differ; the contract explicitly supports both. Optional output sections and
  modern prompt additions mean total record count is not a fixed constant.
- The real `climate.is_single_storm` property includes SingleStorm,
  UserDefinedSingleStorm and SingleStormBatch. Their unchanged allowances and
  exemption from continuous workload validation are coherent.
- Additive child metadata can coexist with `_enqueue`'s existing fork-failure
  lineage and callback. Missing lineage is an ordinary supported state.
- No NoDb migration, prepared-file rewrite or existing-job timeout mutation is
  required. Positive platform alarm-range validation makes overlarge budgets
  explicit instead of truncating them.

## Implementation acceptance reminders

Exercise generated legacy and modern run files, including both owned pass
families (`.pass.dat` and `.hbp`), variable output sections, stale controller
settings, malformed/missing bounded input, exact rounding boundaries and alarm
overflow. Check real RQ serialization, all four dependency trees, preserved fork
metadata/callback and no-prep input hashes. Unit-only queue doubles cannot prove
the persisted timeout. These are conformance checks, not additional contract
requirements or requests to broaden scope.

Subprocess cleanup remains a separately documented limitation. This review does
not authorize production retries or rollout; retaining that separation is
consistent with the operator's bounded timeout request.
