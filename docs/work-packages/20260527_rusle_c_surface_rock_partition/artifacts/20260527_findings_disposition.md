# Findings Disposition - RUSLE C Surface-Rock Partition Package

**Date**: 2026-05-27 21:51 UTC  
**Input review artifact**: `artifacts/20260527_independent_review.md`

## Disposition Summary

- High findings resolved at planning-contract level: 1/1
- Medium findings resolved at planning-contract level: 2/2
- Low findings resolved: 2/2
- Remaining open review findings: 0

## Disposition Details

| Finding | Severity | Disposition | Evidence of Update |
|---|---|---|---|
| Boundary/error-path contract coverage for `rock_fraction_of_rap_bare` not explicit | High | **Accepted and resolved in planning docs**. Added explicit acceptance and planned regression matrix for `<0`, `>1`, non-numeric non-`auto`, and `auto` with/without `cfvo`, plus canonical RQ error handling requirement. | `package.md` Success Criteria; active ExecPlan "Validation and Acceptance" section |
| `schema_defaults_routes` coverage not explicit in validation commands | Medium | **Accepted and resolved**. Added explicit route-schema test target in scope and planned validation commands. | `package.md` Included tests list; active ExecPlan validation commands include `tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `auto` fallback semantics not pinned | Medium | **Accepted and resolved**. Pinned fallback contract: `auto` resolves to `0.0` when top-horizon `cfvo` unavailable, with explicit manifest fallback reason/provenance requirement. | `package.md` Success Criteria; active ExecPlan acceptance behavior and test matrix |
| Inconsistent WIP counters in `PROJECT_TRACKER.md` | Low | **Accepted and fixed**. Reconciled top-level WIP counter to match active package count. | `PROJECT_TRACKER.md` "Current WIP: 7 packages" and "Current WIP Count: 7 packages" |
| Package tracker handoff state stale / ADR visibility missing | Low | **Accepted and fixed**. Updated tracker phase, done items, timeline, disposition table, and explicit ADR link in quick status. | `tracker.md` Quick Status, Task Board, Timeline, and Review Findings Disposition sections |

## Notes

These dispositions tighten the implementation contract and test plan without changing runtime behavior yet. Post-implementation independent review remains required to assess code-level regressions and correctness.

## Post-Implementation Review Disposition (2026-05-27 22:41 UTC)

**Input review artifact**:
`artifacts/20260527_post_implementation_independent_review.md`

### Summary

- High findings resolved in code: 1/1
- Medium findings resolved in code: 1/1
- Remaining open high/medium findings: 0

### Disposition Details

| Finding | Severity | Disposition | Evidence of Update |
|---|---|---|---|
| Schema enum advertised non-runtime token (`\"0.0_to_1.0_numeric\"`) for `rock_fraction_of_rap_bare` | High | **Resolved in code + tests**. Replaced placeholder enum with structured `one_of` contract: `{\"type\": \"string\", \"enum\": [\"auto\"]}` or `{\"type\": \"number\", \"minimum\": 0.0, \"maximum\": 1.0}`. | `wepppy/microservices/rq_engine/schema_defaults_routes.py`; `tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `compute_observed_rap_fg_pct` ndarray handling not broadcast-safe | Medium | **Resolved in code + tests**. Added explicit scalar-or-broadcastable coercion and index-aligned masking; added regression for ndarray rock-fraction inputs. | `wepppy/nodb/mods/rusle/c_formula.py`; `tests/nodb/mods/test_rusle_c_formula.py` |

### Verification After Disposition

- `wctl run-pytest tests/nodb/mods/test_rusle_c_formula.py tests/nodb/mods/test_rusle_c_integration.py tests/nodb/mods/test_rusle_controller.py tests/microservices/test_rq_engine_schema_defaults_routes.py tests/microservices/test_rq_engine_rusle_routes.py --maxfail=1`
