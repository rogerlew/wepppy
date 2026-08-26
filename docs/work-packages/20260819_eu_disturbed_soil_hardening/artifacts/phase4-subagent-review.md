# Phase 4 Independent Subagent Review

**Date**: 2026-08-19
**Reviewer**: Herschel (`01a01c0a-5f4b-73c3-97d0-9799b4919a6b`)
**Scope**: Read-only review of the Phase 4 production diff, tests, stubs, and
documentation.
**Final disposition**: No remaining blocker, high, or medium findings.

## Review Findings and Disposition

| Initial severity | Finding | Disposition | Evidence |
| --- | --- | --- | --- |
| High | Diagnostic report serialization could fail on NumPy scalar or non-finite evidence. | **Fixed** | `quality._json_safe` normalizes integral/real scalars and scalar `.item()` values; non-finite values become strings. `test_quality_report_evidence_is_json_safe_for_numpy_scalars` covers the report boundary. |
| High | Required categorical records could pass validation with only two elements and later fail on builder `[2]` indexing. | **Fixed** | `_categorical_short` now requires the full three-element `(pixel, short, long)` record; malformed land-use coverage is fixture-tested before builder indexing. |
| High (first pass) | Malformed `usedom` shape diagnostics were discarded and could fail unstructured. | **Fixed; first-pass snapshot was stale** | The local correction retained `usedom` diagnostics in the shared list, so malformed/missing records reject before indexing. The regression test uses a two-element record. |
| Medium | Ksat validation accepted shapes the serializer could not consume. | **Fixed** | The builder requires a mapping of exact two-element depth/Ksat pairs, normalizes the Ksat member to `float`, and rejects malformed values before serialization. Malformed-pair replay coverage is present. |
| Medium | Final output moves were sequential and could leave a partial commit if finalization failed. | **Fixed** | The accepted report is serialized in staging; all source/destination files are preflighted; newly moved files are removed if an `OSError` occurs during commit. Accepted/rejected staging tests cover the transaction boundary. |
| Medium | Duplicate soil keys were silently first-wins. | **Fixed** | Divergent staged duplicates and conflicting existing destinations become location-scoped `batch.*` diagnostics, write a rejected `soil_quality.json`, and raise `ESDACSoilBatchError` before output commit. Duplicate-key report coverage is present. |
| Medium | Production worker/staging/report seams and finite serialized rows lacked coverage. | **Fixed** | The accepted batch test invokes the real worker, fixture replay checks every numeric horizon row for finiteness, and tests cover malformed source/Ksat, NumPy evidence, duplicate keys, and accepted/rejected staging. |
| Medium (second pass) | Validated STU numeric strings were passed unchanged into arithmetic-heavy horizon construction. | **Fixed** | Required STU fields are converted to built-in floats after validation and before `Horizon`; numeric-string replay coverage is present. |

## Final Verification

- Focused EU hardening suite: `30 passed, 2 warnings` using
  `tests/eu/soils/test_esdac_quality_contract.py`,
  `test_esdac_quality_fixture.py`, `test_esdac_soil_build.py`, and
  `test_invalid_soil_search.py`.
- The reviewer independently reported all `tests/eu/soils` passing (`31
  passed`).
- `wctl check-test-stubs`: passed.
- `wctl run-stubtest wepppy.eu.soils.soil_build`: passed.
- `wctl doc-lint --path docs/work-packages/20260819_eu_disturbed_soil_hardening`:
  passed.
- Changed-file broad-exception enforcement and `git diff --check`: passed.

The repository-wide test gate remains separately environment-blocked by the
known Docker Compose CLI incompatibility recorded in the tracker; it is not a
Phase 4 code or review finding.
