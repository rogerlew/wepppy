# Correctness and User-Experience Review - Staley M3 WBT Terrain

## Metadata

- **Package**: `docs/work-packages/20260908_staley_m3_wbt_terrain/`.
- **Reviewer**: Independent Codex `reviewer` agent.
- **Date**: 2026-09-08, America/Los_Angeles.
- **Scope reviewed**: `/workdir/weppcloud-wbt/`
  `whitebox-tools-app/src/tools/hydro_analysis/d8_upstream_relief.rs`,
  registration, both Python bindings, affected GeoTIFF reader/writer boundaries,
  `tests/test_d8_upstream_relief.py`, and
  `tools/staley_m3_resolution_study.py`; generated `study-v1` outputs.
- **Commit/branch context**: Uncommitted changes on `master`, WBT base
  `0af47c38356ab12967e209f5b2fde3a8d802348b`.
- **Initial study binary SHA-256**:
  `1a4d8a3c3aaebb1d5259bc7a36fbcc36e81dfa738ababd47dc10041ed3098940`,
  recorded in `study-v1/environment.json`. Independent initial failure probes
  preceded the rebuild; an independent hash was captured only after the fix.
- **Final independently hashed binary SHA-256**:
  `d4adb49d0e856a587ff996cf695bb71fbacf5669b90e4b526de403aac91d4718`.
- **Canonical contracts**: [Terrain contract](terrain_contract.md), sections
  "Accepted engineering decision" and "Input and boundary semantics";
  [study protocol](study_protocol.md), including "Frozen execution details
  before terrain outcomes". User ratification selects maximum upstream raw
  elevation minus outlet elevation; pfdf defect parity is not required.
- **Related artifacts**: [Security review](20260908_security_review.md),
  [validation](validation.md), [reference evidence](reference_parity.md).

## User Outcome

- **User goal**: Obtain aligned upstream relief/area from authoritative supplied
  routing, then assess controlled and native 10 m/30 m terrain sensitivity.
- **Success presented as**: New readable H/A rasters, optional propagated
  coverage, explicit provenance, and reproducible per-outlet study results.
- **Failures that may reach the user**: Invalid arguments, absent inputs,
  unsupported raster metadata, mismatched grids/masks, invalid pointers,
  cycles, arithmetic overflow, existing outputs, and filesystem I/O errors.
- **Partial-state behavior**: Semantic validation precedes output publication.
  Each output is published independently without replacement. An I/O failure
  may leave earlier outputs; discard the set and retry using fresh names.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Coverage output omitted | Yes | Produce H/A and record coverage count | Source output loop; independent no-coverage CLI probes |
| Required input absent | No | Explicit file error before output publication | Canonicalization path; missing-value CLI test |
| Empty valid-data domain | No | Explicit `No valid terrain cells` error | Source `run()` empty-domain check |
| Populated multirow grid | Yes | Exact upstream maxima/counts and aligned masks | Eight independent path-walk cases; 24 study pairs |
| Single row or single cell | Yes | Same analytical contract as other shapes | COR-01 repaired; all six original shape probes pass |
| Flat/rising raw elevations under supplied routing | Yes | Preserve raw elevations and combine all upstream maxima | Rust/CLI analytical cases; independent random elevations |
| Finite or NaN NoData | Yes | Matching masks, no sentinel arithmetic, propagated contact flag | Eight independent compressed CLI cases |
| Non-square projected cells | Yes | Area uses dx times dy | Independent 10 m by 20 m cases |
| Other tools' legacy assumed-spacing inputs | Yes, outside strict terrain contract | Preserve the existing assumed-grid output | COR-05 repaired; independent D8Pointer output retains EPSG:32611 and the 1 m affine |
| Point pixels, multiband, zero source spacing | No | Explicit rejection before publication | COR-02 repaired; direct tagged-input regression tests |
| Invalid pointer, cycle, unequal masks, unsupported units/CRS | No | Explicit validation failure without output | Existing direct CLI tests and source validation |
| Output exists or aliases another output/input | No | Preserve existing bytes and fail | Existing CLI test; security publication tests |
| Study outlet cannot be matched | Diagnostic unavailable | Record exclusion and continue independent comparisons | COR-04 repaired; direct empty/distant candidate checks |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Optional coverage absent | Expected | Successful H/A | Explicit optional argument |
| Input invalid or unsupported | Expected | Nonzero CLI result naming invalid input | Bounded interface; silent conversion is prohibited |
| Existing output | Expected | Failure preserving original bytes | New-file contract |
| Output I/O or cleanup failure | Exceptional | Nonzero result and partial-set recovery | Individual publication is deliberately nontransactional |
| Supplied domain contact | Expected | Valid within-domain H/A plus coverage warning | Conservative coverage rule |
| No study match within 90 m | Expected diagnostic absence | Explicit unavailable record | Predeclared protocol; not a terrain algorithm failure |

## Review Checks

- [x] Canonical intent is named independently of implementation and tests.
- [x] Absent, empty, populated, legacy, and unsupported states are distinguished;
  direct coverage gaps are named instead of claiming exhaustive validation.
- [x] Optional flags and filesystem/grid states are separate dimensions.
- [x] Unmocked CLI probes exercise decoding, serialization, and both bindings;
  security review directly exercises the publication boundary.
- [x] No mocks replace the changed raster or publication boundaries.
- [x] Final security controls preserve the tested valid terrain/output states.
- [x] Partial success, readiness, retry, and cleanup semantics are explicit.
- [x] Expected validation errors identify the relevant contract.
- [x] Shared GeoTIFF changes pass targeted regression validation; parent Rust
  tool/raster regression logs were also examined.
- [x] Numerical coverage claims name their tested dimensions.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Valid one-row/single-cell GeoTIFF outputs | Writer encoded scalar StripOffsets and StripByteCounts as offsets into auxiliary data rather than inline values. Command returned success with corrupted H/A/coverage. | `whitebox-raster/src/geotiff/mod.rs`, `write_geotiff()` tags 273/279; 1x3 input 130,120,100 produced H approximately 6.79e-313,0,10 instead of 0,10,30. | Correct scalar strip entries for compressed/uncompressed output; exercise single-cell/single-row H/A/coverage through real TIFF readback. | Resolved: scalar fields repaired; expanded CLI suite and all six original independent shape probes pass. |
| COR-02 | Medium | Unsupported source metadata accepted as valid terrain | `validate_grid()` trusted decoder defaults for bands/pixel type and normalized spacing. Reader did not populate sample count/pixel-area fields and rewrote zero x spacing to 1 m. Point and multiband rasters succeeded; explicit zero spacing produced 1 m2 cells. | `d8_upstream_relief.rs`, `validate_grid()`; GeoTIFF reader source tags 277, 1025, 33550; direct CLI probes below. | Preserve/validate original metadata, reject unsupported inputs before writes, and add direct tagged-input regressions. | Resolved: sample count, raw pixel type, and separately retained original spacing are checked; direct tagged-input regressions pass. |
| COR-03 | Medium | Missing required output provenance | `add_metadata_entry()` populated memory, but original TIFF writer emitted none of those entries. Output lacked source paths, formula, units declaration, coverage count, and timing despite success. | Generated TIFF tags and strings; original `write_geotiff()` lacked ImageDescription/tool metadata serialization. | Serialize the promised metadata into the TIFF and assert it from generated outputs. | Resolved: standard ImageDescription now contains all promised fields; direct independent readback confirms complete provenance. |
| COR-04 | Low | Unavailable study match | `snap()` called `argmin` on an empty candidate list or raised on a distant match, aborting the panel before CSV publication instead of recording unavailable. No supplied-panel pair triggered this. | `tools/staley_m3_resolution_study.py`, `snap()` and `execute()` matching loops. | Record a specific unavailable status and continue independent comparisons. | Resolved: explicit `None` handling, unavailable records, and loop continuation; direct no-candidate/distant/exact-match checks pass. |
| COR-05 | Medium | Legacy tool georeferencing regression from COR-02 repair | Retaining zero in the shared `model_pixel_scale` field prevented the existing writer from emitting scale for a legacy assumed-spacing input with a tiepoint. `D8Pointer` still succeeded but output lost its georeferencing. | `whitebox-raster/src/geotiff/mod.rs`, source-scale preservation and writer ModelPixelScale branch; `/tmp/staley-correctness-legacy-ma5uducz/pointer.tif` read as identity transform with no CRS. | Preserve original source metadata separately from the legacy effective-scale field and verify both strict rejection and existing-tool output georeferencing. | Resolved: new `RasterConfigs.source_pixel_scale` preserves original tags separately; the legacy effective scale is restored. Existing-tool and strict-tool regression checks both pass. |

## Validation Evidence

Initial direct probes preceded the metadata/header corrections. Temporary reproduction data:

- `/tmp/staley-correctness-probe-xnvlm46x/`: plain 1x3, point-pixel,
  two-band, and NaN-tagged analytical chains.
- `/tmp/staley-correctness-grid-probe-dt_ryo_z/`: 1x1, 1x5, 2x3, 3x1,
  3x3, and 5x7 generated-output checks. One-row shapes fail; multirow shapes
  return analytical H/A/coverage.
- `/tmp/staley-correctness-zero-spacing-qd7jfj91/`: explicit source
  ModelPixelScale x value zero; original command returns success with area 1.
- `/tmp/staley-correctness-random-eyi4k_0z/`: eight independently generated
  9x11 acyclic routing fields with fixed NumPy seed 9137. A source-by-source
  downstream path walk, independently of Kahn traversal, accumulates counts,
  maxima, and boundary-contact flags. Every WBT direction is exercised.
  Compressed input/output, 10 m by 20 m cells, finite/NaN NoData, all H/A/
  coverage values, and valid masks pass 1e-9 arithmetic tolerances.

Study review read saved `study-v1` catchment masks and raw DEMs directly,
without importing the study helper. All 24 paired outlet cell counts, maximum
minus outlet values, and independently computed boundary/NoData contact flags
agree with CSVs. All 864 probability scenarios pass independent odds-ratio
propagation and inverse-coefficient threshold checks. Twelve controlled and
twelve native comparisons have zero coverage-ineligible pairs and two primary
screen failures each. This verifies saved results, not calibration equivalence.

Source review confirms coefficients, meter/square-meter conversion, rainfall
accumulation versus intensity, fixed F/S scenarios, non-saturated reference
probabilities, and maximum per-outlet screens match the frozen protocol.
Every supplied fine grid is exactly 10 m, so the overlap helper's 100 m2 pixel
area is valid for this panel. Native boundary IoU is an approximate nearest-
neighbor overlay on the fine grid and must be described that way in reports.

The first corrected binary passed the reviewer-run command
`/workdir/wepppy/.venv/bin/python -m unittest discover -s tests -p
test_d8_upstream_relief.py`: 11 tests, including both real bindings,
compressed/uncompressed single-row outputs, metadata, NaN/BigTIFF inputs,
and point/multisample/zero-scale rejection. All six original independent shape
probes then produced correct H/A/coverage with full provenance. Three direct
`snap()` calls verify no candidate, distant candidate, and exact candidate.
`study-v2` produces exactly the same 24 comparison records and 864 sensitivity
records as the independently checked `study-v1`; no unavailable matches occur.

Final binary verification:

- Reviewer executed `/workdir/wepppy/.venv/bin/python -m unittest discover
  -s tests -p 'test*.py'`: all 15 tests passed, including direct legacy
  assumed-spacing and strict terrain rejection checks.
- Independently repeated the original legacy failure outside the suite.
  `/tmp/staley-correctness-legacy-fixed-j2wkso06/pointer.tif` retains
  EPSG:32611 and affine `(1, 0, 500000, 0, -1, 5200000)`. The same original
  zero-spacing inputs are still rejected by D8UpstreamRelief before outputs.
- Final `study-v3` comparison and sensitivity CSVs exactly equal all 24 and
  864 independently checked `study-v1` records. Its environment records the
  final binary hash above and its unavailable-match list is empty.
- Examined parent-run `/tmp/staley-m3-final-cargo-test.log`: 152 tool tests
  passed; `/tmp/staley-m3-raster-tests.log` reports all raster test groups and
  its documentation test passing. Full package closeout gates remain the
  package owner's responsibility in [validation](validation.md).

## Residual Risk and Coverage Gaps

- [Resolution decision](resolution_decision.md) now distinguishes requested
  projected/geographic records, native workflow differences, approximate
  boundary overlap, alternative screens, and the benchmark environment.
  Reproduction/provenance and complete package gates remain documented in the
  owner's final validation artifact.
- Reference defects and user-selected semantics leave original Staley calibration
  preprocessing equivalence unproven. A 10 m recommendation cannot establish
  that the model itself is calibrated for these new terrain inputs.
- The limited three-site panel does not support a general CONUS availability
  rule. Coverage zero establishes absence of the specified contact condition,
  not independent correctness of routing or elevation acquisition.
- Adversarial TIFF decoding, quotas, crash durability, and hostile replacement
  of parent directories remain outside this local CLI scope; see security
  review. No production integration/deployment is authorized by this package.

## Verdict

- **Gate status**: `pass` for the reviewed implementation and study arithmetic.
- **Unresolved findings**: High 0; Medium 0; Low 0.
- **Release recommendation**: `ship-with-conditions`: complete the independent
  security/documentation/package gates; deployment and production integration
  remain outside this review.
- **Reviewer sign-off**: Independent Codex `reviewer`, 2026-09-08;
  all five findings are closed with source and direct regression evidence.
