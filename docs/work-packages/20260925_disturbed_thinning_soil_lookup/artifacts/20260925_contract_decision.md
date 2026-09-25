# Contract decision checkpoint

Base implementation: `2b0c3e30d5856f74069530b422e2541cc7820f06`.

Operator approval on 2026-09-25 UTC: "scaffold and execute work-package to fix
this please. it should match to any landuse that starts with \"thinning\" . the
work-package should also check mulch". This authorizes the bounded implementation
and necessary checkpoint commits; production deployment/rebuild is excluded.

Canonical delta: new `docs/schemas/disturbed-treatment-soil-lookup-contract.md`
and ADR-0073 require prefix resolution in both single/MOFE soil generation.
Existing MOFE management and Omni thinning UI contracts retain their scopes;
soil lookup rules do not change their cover/eligibility obligations.

Classification: confirmed lookup defect plus explicit prefix behavior ratified
by operator. Compatibility: no schema mutation; generated thinning parameter
values change to existing effective row. Mulch's three supported suffixes retain
burned base parameterization. None/empty/unrecognized strings stay unchanged.
Security impact none. Numerical regression risk medium; use real artifact tests.

Regression evidence planned: failing thinning source/mapped/prepared soil tests,
all supported mulch vegetation/severity/level combinations, formats 9002/9005,
prefix boundaries, existing disturbed suites and broad pytest. Contract reviews
and their dispositions must be recorded before the standalone ancestor commit.

## Review disposition and caller inventory

Both independent reviewers identified additional shared-helper callers:
RUSLE `normalize_disturbed_family` (custom CSV key identity), Disturbed PMET,
and Treatments soil selection. Disposition: do not change that helper. Apply
the same prefix rule directly in `Disturbed.modify_soil` and
`Disturbed._modify_mofe_soils_impl`. Their lookup selection is the only runtime
delta. Preserve existing helper tests and run RUSLE/PMET/Treatments regressions.
No RUSLE contract change is needed because its behavior remains identical.

## State and evidence matrix

| State | Expected behavior and evidence |
| --- | --- |
| Absent/None class | Shared helper unchanged; existing missing-row behavior |
| Empty class | Same missing-row behavior; no prefix match |
| Populated thinning | Effective thinning row reaches converted/combined/prepared soils |
| Legacy thinning/custom prefix | Same prefix match; original artifact identity retained |
| Supported mulch | Burned base row preserved for all 27 vegetation/severity/level combinations |
| Unsupported string/embedded thinning/case mismatch | No new match; existing resolution retained |
| Malformed non-string | Existing error behavior, no coercion or new validation |
| Working/failed/completed scenario | No lifecycle change; rebuild required for existing artifacts |
| Existing generated soil key | Existing reuse behavior; no automatic repair claim |
| Archived/restored run | No format/path change; restored stale bytes require supported rebuild |
| Browse/download/report | Existing inventory and access unchanged; old reports stay stale until rerun |

Artifact release gate: local tests directly read generated and prepared soils;
isolated actual-project validation must use supported fork/archive initialization.
Canonical archive/restore byte checks are part of local validation. Deployment/
recovery and fresh report/browse evidence are separate operator gates.
