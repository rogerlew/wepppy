# SSURGO FC/WP Sanitization

**Status**: Open (2026-07-05)  
**Timezone**: UTC

## Overview
NASA ROSES batch runs under `/wc1/batch/nasa-roses-202606-psbs/` produced WEPP soil files containing non-finite or sentinel field-capacity and wilting-point values such as `-9.9` and `nan`. WEPP hillslope execution then failed with SIGFPE after reading those values. This package hardens SSURGO soil generation and WEPP soil serialization so invalid `fc`/`wp` values are replaced by valid Rosetta estimates at the SSURGO boundary or rejected before serialization.

## Objectives
- Prevent SSURGO-generated 7778 soil files from containing non-finite or physically invalid `field_cap`/`wilt_pt` values.
- Enforce the same `fc`/`wp` validity rules in `WeppSoilUtil` before 7778/900x serialization.
- Add regression tests using affected production mukeys and a 9002 conversion path.
- Document how to invalidate affected production batch runids so they queue for a rebuild after the fixed code is deployed.

## Scope

### Included
- `wepppy/soils/ssurgo/ssurgo.py` finite and physical validity checks for field capacity and wilting point.
- `wepppy/wepp/soils/utils/wepp_soil_util.py` serializer enforcement and Rosetta recomputation validation.
- Regression tests under `tests/soils/` and `tests/wepp/soils/utils/`.
- Durable docs and ADR updates for the changed fallback rule.
- Operator runbook notes for redis timestamp invalidation of affected batch runids.

### Explicitly Out of Scope
- Changing the global `isfloat()` contract.
- Replacing Rosetta or changing the WEPP Fortran binary.
- Automatically invalidating production runs before the fixed code is deployed to the worker environment.

## Implementation Fidelity and Evidence
- **Fidelity target**: faithful extraction of existing SSURGO-to-WEPP behavior with an added invalid-value guard.
- **Authoritative source path(s)**: `wepppy/soils/ssurgo/ssurgo.py`, `wepppy/wepp/soils/utils/wepp_soil_util.py`, `/workdir/wepp-forest_260430_baseline/src/input.for`.
- **Cutover proof required**: affected mukey fixtures build finite 7778 soils and `WeppSoilUtil.to9002()`/`str()` serializes finite legacy and appended Rosetta values.
- **Acceptance evidence type**: both fixture-output tests and production run invalidation procedure.

## Stakeholders
- **Primary**: WEPPcloud operators and batch users.
- **Reviewers**: WEPPpy maintainers.
- **Security Reviewer**: N/A.
- **Informed**: NASA ROSES batch operators.

## Success Criteria
- [x] SSURGO horizon construction replaces invalid SSURGO-derived `fc`/`wp` with valid Rosetta estimates and records build notes.
- [x] `WeppSoilUtil` rejects or recomputes invalid `fc`/`wp` rather than serializing `nan`, `inf`, sentinel negatives, or `wp > fc`.
- [x] Regression tests cover affected mukeys and 9002 conversion.
- [x] Documentation and ADR describe the fallback rule, evidence, risks, and rollback.
- [x] Production invalidation command is documented and gated on deployment of the fix.

## Parameterization ADR Gate
- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR link(s)**: `docs/adrs/ADR-0012-ssurgo-fc-wp-sanitization.md`
- **Decision provenance captured**: yes

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites
- Existing Rosetta dependency available in worker containers.
- Batch rerun uses `RedisPrep` task timestamps to determine retry eligibility.

### Blocks
- Safe rerun of affected NASA ROSES batch runids.

## Related Packages
- **Related**: `docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/`
- **Related**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/`

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate
- **Security impact triage**: none
- **Dedicated security review required**: no
- **Triage rationale**: Internal soil parameter validation and operator runbook only; no auth, route, secret, or external input surface changes.
- **Security review artifact**: N/A

## Hardening and Callus Softening
- **Failure signature(s)**: `wepp_260606_hill` returns `-8`/SIGFPE with Fortran backtrace through `src/input.for` while reading soil hydraulic values; affected `.sol` files contain `-9.9 nan` in legacy `fc wp` columns.
- **Related prior hardening efforts**: `docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/`
- **Health signals**: affected mukey soil files contain no `nan`, `inf`, or sentinel negative `fc`/`wp`; affected batch runids become retry-eligible and complete WEPP hillslope tasks after deployment.
- **Danger signals**: silent fallback hides broad upstream data corruption; serializer starts accepting invalid Rosetta predictions.
- **Observation window**: next NASA ROSES batch rerun.
- **Temporary calluses introduced**: none.
- **Callus softening hypothesis**: N/A.

## References
- `wepppy/soils/ssurgo/ssurgo.py` - SSURGO horizon construction and 7778 soil serialization.
- `wepppy/wepp/soils/utils/wepp_soil_util.py` - WEPP soil parsing, migration, and 900x serialization.
- `wepppy/nodb/batch_runner.py` - batch retry eligibility based on missing `RedisPrep` task timestamps.
- `/workdir/wepp-forest_260430_baseline/src/input.for` - WEPP reads `thetd2` from soil files and aggregates into `thetd1`.
- `/wc1/batch/nasa-roses-202606-psbs/` - production batch with affected runids.

## Deliverables
- `wepppy/soils/ssurgo/ssurgo.py` local finite/physical `fc`/`wp` sanitizer.
- `wepppy/wepp/soils/utils/wepp_soil_util.py` conversion repair and serialization enforcement.
- `tests/soils/test_ssurgo_fc_wp_sanitization.py` affected-mukey regression coverage.
- `tests/wepp/soils/utils/test_wepp_soil_util.py` 9002 conversion and invalid serialization coverage.
- `docs/adrs/ADR-0012-ssurgo-fc-wp-sanitization.md` parameterization ADR.
- `docs/work-packages/20260705_ssurgo_fc_wp_sanitization/tracker.md` production invalidation runbook.
- `docs/work-packages/20260705_ssurgo_fc_wp_sanitization/artifacts/README.md` audit artifact convention.

## Follow-up Work
- Deploy sanitizer to wepp1 before invalidating affected production runids.
- Execute the dry-run and live invalidation procedure after deployment.
