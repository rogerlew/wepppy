# QA Review Findings - Disturbed BD Override + Rosetta WC/FC Recompute

**Reviewer role**: `qa_reviewer`  
**Reviewer agent id**: `019d46bc-3da2-7412-9e72-b97a6c7787ca`  
**Review date**: 2026-04-01

## Summary
- Findings reported: `3 medium`
- Findings resolved: `3/3`
- Residual medium/high risk at closure: `none`

## Findings and Disposition

### QA-1: Non-empty non-numeric `bd` text accepted as no-op
- Severity: Medium
- Reviewer evidence:
  - Parser allowed text like `none` to bypass validation instead of hard-failing non-numeric content.
- Resolution:
  - Tightened parser in `wepppy/wepp/soils/utils/wepp_soil_util.py`:
    - only `None`/blank string are valid no-op values.
    - any non-empty non-numeric value now raises `ValueError`.
- Validation:
  - `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1` -> pass
- Status: Resolved

### QA-2: New Soils persisted flag lacked explicit NoDb round-trip test
- Severity: Medium
- Reviewer evidence:
  - Route test validated assignment on stub object only; no `soils.nodb` persistence round-trip.
- Resolution:
  - Added `test_rosetta_bd_toggle_round_trips_through_soils_nodb` in `tests/nodb/test_soils_gridded_root_creation.py`.
- Validation:
  - `wctl run-pytest tests/nodb/test_soils_gridded_root_creation.py --maxfail=1` -> pass
- Status: Resolved

### QA-3: 7778 disturbed converter forwarding branch lacked regression coverage
- Severity: Medium
- Reviewer evidence:
  - New forwarding behavior existed in code, but tests covered only over9000 path.
- Resolution:
  - Added 7778 forwarding tests in:
    - `tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py`
    - `tests/nodb/mods/disturbed/test_modify_soils_mofe.py`
- Validation:
  - `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1` -> pass
- Status: Resolved

## Closure Validation Snapshot
- Targeted rerun after QA fixes:
  - `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py tests/wepp/soils/utils/test_wepp_soil_util.py tests/microservices/test_rq_engine_wepp_routes.py tests/nodb/test_soils_gridded_root_creation.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `154 passed`
- Route pair rerun:
  - `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` -> `23 passed`
- Full closure gate:
  - `wctl run-pytest tests --maxfail=1` -> `2952 passed, 36 skipped`
