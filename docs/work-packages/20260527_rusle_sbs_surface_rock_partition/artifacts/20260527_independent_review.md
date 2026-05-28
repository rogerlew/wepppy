# Independent Review - RUSLE `scenario_sbs` Surface-Rock Partition Integration

**Date**: 2026-05-27 UTC  
**Reviewer**: Codex (independent implementation pass)  
**Scope**: Runtime math/proxy behavior, UI/API contract wiring, regression coverage, and manifest provenance.

## Summary

The implementation aligns with the package contract: `scenario_sbs` now supports RAP-independent surface-rock partitioning through `rock_fraction_of_sbs_bare` with `auto` proxy defaulting (`cosurffrags -> cfvo -> 0.0`). End-to-end option propagation and mode-specific UI/API behavior are covered by targeted tests.

## Findings

### High

- None.

### Medium

- None.

### Low

1. `build-rusle` payload currently preserves `rock_fraction_of_sbs_bare` as string when passed as JSON string, mirroring existing route behavior for other fields. This is acceptable because NoDb parsing enforces numeric/`auto`, but route-level numeric coercion could be considered in a future cleanup for consistency.

## Coverage Check

- Runtime/controller path coverage includes:
  - `tests/nodb/mods/test_rusle_c_formula.py`
  - `tests/nodb/mods/test_rusle_c_integration.py`
  - `tests/nodb/mods/test_rusle_controller.py`
- API contract coverage includes:
  - `tests/microservices/test_rq_engine_rusle_routes.py`
  - `tests/microservices/test_rq_engine_schema_defaults_routes.py`
- UI/controller payload coverage includes:
  - `wepppy/weppcloud/controllers_js/__tests__/rusle.test.js`

## Validation Evidence

- `wctl run-pytest tests/nodb/mods/test_rusle_c_formula.py tests/nodb/mods/test_rusle_c_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_rusle_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-npm test -- controllers_js/__tests__/rusle.test.js`
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`

All commands passed in this execution pass.
