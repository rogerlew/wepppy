# Correctness and User-Experience Review - Staley M3 Soils

## Metadata

- **Package**: `docs/work-packages/20260908_staley_m3_soils/`
- **Reviewer**: independent Codex correctness reviewer (`soil_correctness_review`).
- **Date**: 2026-09-09 UTC.
- **Scope reviewed**: `soil_thickness.py`, its focused tests, `run_study.py`,
  offline contract, study protocol, ADR-0053, and generated evaluation-v2/v3 tables.
- **Commit context**: uncommitted package changes over
  `e8bef992ecb4bccf57d3a40ceab49e2e4b21ee97`.
- **Canonical contracts**: [promoted offline contract](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/m3_soil_thickness.md), sections
  "Component intervals", "Components, map units and catchments", and
  "Additive artifacts and boundary behavior";
  [protocol](study_protocol.md), "Comparisons and screens";
  [ADR-0053](../../../adrs/ADR-0053-staley-m3-offline-soil-thickness.md).
- **Related QA/security artifacts**: [security review](20260909_security_review.md)
  and package validation are separate closeout gates; this review does not
  replace them.

## User Outcome

- **User goal**: evaluate raw SSURGO cumulative thickness against the original
  STATSGO predictor on the fixed terrain panel without modifying live projects.
- **Success presented as**: inspectable component/map-unit/catchment tables,
  thickness and fractional-support rasters, source hashes, and labeled paired
  M3 probabilities/thresholds. Partial estimates remain diagnostics.
- **Failures that may reach the user**: explicit file, SQLite, schema, raster,
  source-key, or numerical errors; rejected scientific observations return
  unavailable values and reason codes.
- **Partial-state behavior**: invalid inputs checked before output creation
  leave no output folder. A later failure can leave an incomplete folder
  without a success manifest. Retry requires a new output directory.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Source absent / live soils never built | Yes, as an unavailable state | Explicit missing-source failure; no creation or acquisition | `test_readonly_boundaries`; absent SQLite path stays absent |
| Database empty or without canonical schema | No for evaluation | Explicit `ValueError` | `test_readonly_boundaries` covers zero-byte/schema-empty/table-empty cases |
| Populated source and complete catchment | Yes | Weighted mean, S=cm/254, complete coverage and full outputs | `test_generated_pipeline_full_partial_unknown_water`; 58 cm weighting fixture |
| Individual component lacks horizons | Yes, unavailable component | Preserve omitted support in the full denominator | `test_weights_partial_substitution_and_units`; public subset; direct fractional-support pipeline probe |
| Partial coverage, nonsoil, unknown MUKEY and outside-survey cells | Yes | Distinct reasons, diagnostic mean, unavailable full S | Direct four-cell probe: 60% valid soil in one cell plus nonsoil/unknown/outside cells yields 30 cm, coverage 0.15, partial status |
| Supported legacy/custom cache with canonical columns | Yes | Read canonical columns without requiring descriptive extras | Synthetic SQLite lacks optional `compkind`; real public subset passes the same adapter |
| Legacy H or undeclared L/V master | Yes, unavailable strict observation | `ambiguous_material`; all-layer sensitivity remains separate | `test_rejected_intervals`, `test_undeclared_materials`, public H records |
| Empty, shifted or nonbinary catchment mask | No | Explicit rejection before output creation | Direct real-raster probes: `Empty catchment mask`, `Catchment grid mismatch`, invalid-mask-value error |
| Malformed SQLite, source keys, or disguised VRT | No | Explicit bounded rejection | `test_readonly_boundaries`, `test_malformed_source_keys`, `test_disguised_vrt_rejected_before_output` |
| Finite source depths that overflow derived arithmetic/storage | No | Explicit numerical rejection, never successful infinite thickness | `test_nonfinite_arithmetic_and_raster_representation` passes; Float32 rejection precedes output creation |

Input combinations were reviewed separately: both interval policies; contiguous,
duplicate, conflicting, gapped and overlapping intervals; R/Cr material;
valid/missing/negative/overfull percentages; substitutions; and three spatial
support modes. These are bounded coverage claims, not exhaustive enumeration.

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Missing required cache or raster | Expected unsupported evaluation state | File error; no implicit fetch/build | Explicit acquisition/evaluation separation |
| Missing individual horizons, incomplete components or survey coverage | Expected scientific unavailability | Reasons plus partial/unavailable rows | Missing data cannot become zero or full support |
| Malformed schema/key/grid/driver | Exceptional input | Explicit exception before generation where checked | Joining or aggregating such inputs cannot preserve the contract |
| Existing output directory | Expected retry conflict | `FileExistsError`; use a fresh directory | Immutable source snapshots and additive outputs |
| Input changes during generation | Exceptional consistency failure | Error and no success manifest | Output provenance cannot certify changing source data |
| Invalid M3 denominator | Exceptional diagnostic input under fixed F=0.5 | `ValueError` aborts evaluation | Updated protocol explicitly distinguishes invalid diagnostic input from scientific partial support |

## Review Checks

- [x] Canonical intent is named independently of implementation/tests.
- [x] Absent, empty, populated, supported legacy and malformed states are
  reviewed, including derived numerical overflow.
- [x] Input/policy combinations and source/filesystem state are separate.
- [x] Actual SQLite, GeoTIFF and owned Rust aggregation exercise changed
  source/storage boundaries; safety behavior is not replaced by mocks.
- [x] Valid canonical sources remain usable through the restrictions;
  dedicated security review owns the broader security assessment.
- [x] Partial success, retry and success-manifest semantics are explicit.
- [x] Tested errors identify the failing source/schema/grid condition.
- [x] Existing NoDb, UI, RQ and WEPP workflows receive no production wiring.
- [x] No exhaustive-coverage or scientific-validation claim is made.

## Direct Validation

Independent command:

```text
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_soil_thickness.py
32 passed, 2 dependency deprecation warnings, 9.84 seconds

wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_soil_thickness.py -k 'nonfinite or malformed or undeclared or diagnostic or reference_support'
9 passed, 26 deselected, 2 dependency deprecation warnings, 9.06 seconds
```

The second independent run followed the numerical fix. The executing agent
also reported 35 passing tests in the complete final focused module.

Direct `wctl exec -T weppcloud python` probes exercised real SQLite/GeoTIFF/Rust
boundaries for the state matrix. Before correction, a source row with MUKEY=0
produced a raster thickness of 30 cm and support 1 for outside-survey cells
while the catchment table excluded those same cells. Source-key validation now
rejects the malformed source before this divergent output can be generated.

An independent calculation over evaluation-v2's 72 source-comparison rows and
924 diagnostic scenarios verified common-support equality, cm/254 conversion,
both source probabilities, both inverse thresholds, percentage-point deltas,
and threshold changes in mm, mm/hour and percent. Forward/inverse probabilities
matched within 1e-12. No full-support comparison had paired availability.
The checker used the canonical coefficient table directly rather than calling
the study's scenario function. Separate probes confirmed stable logistic
evaluation at -1000 and +1000 and both interior probability targets.

Final evaluation-v3 produced the same 72 comparison and 924 diagnostic rows;
both CSV files were byte-identical to the independently verified evaluation-v2
results. Component/map-unit audits were unchanged, and catchment coverage
changed only regenerated mask-file hashes. Final environment hashes matched
the reviewed helper and study script after the fixes.

Original cached USGS metadata/SAS was checked directly: `laydeph-laydepl` is
summed by component; THICK is normalized by nonmissing component percentages;
WATER component THICK is explicitly missing. There is no horizon-designation
filter. This supports extraction semantics, not bedrock inclusion or endpoint
censoring in the original surveys.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Strict material selection | L/V masters were accepted outside the declared O/A/E/B/C policy | Original `soil_thickness.py:69`; direct 30 cm L/V probes | Restrict whitelist and test both rejected masters | Resolved; `test_undeclared_materials` passes |
| COR-02 | Medium | Malformed source joins and outside-survey artifacts | MUKEY=0 polluted support rasters; null COKEY could join as valid; integer aliases could collide | Original `soil_thickness.py:110,227,248`; direct real pipeline contradiction above | Validate positive keys before grouping; normalize aliases; reject duplicate component/horizon ownership | Resolved; `_key` plus ownership checks and malformed-key regressions |
| COR-03 | Medium | Diagnostic M3 regression coverage | Tests ended at catchment S despite required downstream probability/threshold propagation | Original focused test module ended after public-subset test | Add real study scenario/round-trip coverage | Resolved; `test_diagnostic_m3_propagation_and_inverse` and independent full-table recomputation |
| COR-04 | Medium | Malformed extreme numeric source | Finite 0–1e308 cm interval at 100% weight returned `mean_cm=inf`, complete status, no reasons; Float32 output could also overflow | Direct `derive_mapunits` reproduction; weighted numerator and raster assignment | Reject nonfinite derived arithmetic and unrepresentable raster values without inventing a scientific depth threshold; add regression | Resolved; component/weighted arithmetic guards and pre-output Float32 validation; numerical regression passes |

## Residual Risk and Coverage Limits

The three-site panel is small and includes dependent nested catchments. Source
agreement is not validation against observed debris flows. Component fractions
have unknown within-map-unit locations; common support cannot eliminate that
unobserved bias. No SSURGO production source or partial-coverage policy is
approved. No major correctness finding remains in the reviewed offline scope.

The reviewer has not fault-injected every filesystem failure or raced source
replacement during a build. The executing agent owns repository-wide checks
and source-acquisition reproducibility evidence, beyond the reviewed bounded
derivation and evaluation paths.

## Verdict

- **Gate status**: `pass` for reviewed offline derivation/evaluation.
- **Unresolved findings**: High 0; Medium 0; Low 0.
- **Release recommendation**: `ship` within the authorized offline scope;
  scientific source acceptance and production integration remain deferred.
- **Reviewer sign-off**: independent Codex correctness reviewer, 2026-09-09 UTC;
  all four findings verified closed.
