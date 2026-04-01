# Code Review Findings - Disturbed BD Override + Rosetta WC/FC Recompute

**Reviewer role**: `reviewer`  
**Reviewer agent id**: `019d46bc-3d65-7e21-95e8-bd43c43c1d06`  
**Review date**: 2026-04-01

## Summary
- Findings reported: `1 high`, `1 medium`
- Findings resolved: `2/2`
- Residual high/medium risk at closure: `none`

## Findings and Disposition

### CR-1: Stub/type contract drift for changed public APIs
- Severity: High
- Reviewer evidence:
  - Runtime changes in `wepppy/wepp/soils/utils/wepp_soil_util.py` were not reflected in `wepppy/wepp/soils/utils/wepp_soil_util.pyi`.
  - Runtime property addition in `wepppy/nodb/core/soils.py` was not reflected in `wepppy/nodb/core/soils.pyi`.
  - Reviewer repro called out failing stubtests.
- Resolution:
  - Updated `wepppy/wepp/soils/utils/wepp_soil_util.pyi` with constants and new method parameters.
  - Updated `wepppy/nodb/core/soils.pyi` with `rosetta_wc_fc_from_disturbed_bd_override` getter/setter.
- Validation:
  - `wctl run-stubtest wepppy.wepp.soils.utils.wepp_soil_util` -> pass
  - `wctl run-stubtest wepppy.nodb.core.soils` -> pass
  - `wctl check-test-stubs` -> pass
- Status: Resolved

### CR-2: Positional compatibility risk in `to_over9000` signature
- Severity: Medium
- Reviewer evidence:
  - New parameter insertion before `version` could break positional callers by shifting meaning of existing arguments.
- Resolution:
  - Reordered signature to preserve existing positional contract:
    - `version` remains before new optional toggle parameter.
  - Continued to pass new toggle using keyword arguments at call sites.
- Validation:
  - `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1` -> pass
  - `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1` -> pass
- Status: Resolved

## Additional Reviewer Coverage Suggestions (non-blocking)
- Add explicit 7778 recompute success-path coverage.
- Keep endpoint coverage for all WEPP run/prep endpoints.

Disposition:
- Added 7778 forwarding tests in disturbed single-OFE and MOFE suites.
- Added route persistence test covering `run-wepp`, `run-wepp-watershed`, and `prep-wepp-watershed`.

## Closure Validation Snapshot
- `wctl run-pytest tests --maxfail=1` -> `2952 passed, 36 skipped`
- `wctl run-npm lint` -> pass
- `wctl run-npm test -- wepp` -> pass
