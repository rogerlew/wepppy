# Correctness review: project-grid area-weighted kslast

## Metadata

- Package: `docs/work-packages/20260909_kslast_area_weighted/`.
- Reviewer: independent `correctness_review` agent.
- Date: 2026-09-09 UTC.
- Reviewed worktrees: WEPPpy `master`, ancestor `febd8f2d3`; wepppyo3 `main`, ancestor `072aed83`. Final implementation commits: WEPPpy `9e1c48f4d`, native source `125edc1`, release artifact `d6641ab`.
- Scope: native `raster_characteristics/src/area_mean.rs`, release wrapper/export, `raster_stacker`, `kslast_map.py`, ordinary/MOFE prep integration, and corresponding tests.
- Authority: [kslast contract](../../../schemas/kslast-map-contract.md), sections Grid and artifacts, Generic native boundary, WEPP preparation and provenance, Directory-only runtime boundary; native `docs/area-weighted-raster-mean.md`.
- Related [security review](20260909_security_review.md) includes real Redis contention and valid/escaping directory-alias evidence. The final integration disposition below uses completed run artifacts and a live RQ cross-check, in addition to source review.

## User outcome

The user needs a hillslope mean over the aligned project grid, with conductivity defaults used only for missing area, and the result applied to every eligible OFE. The run must retain the aligned map and coverage provenance, and ordinary/MOFE prep must share this policy.

Expected failures are explicit invalid default, unreadable configured source, unusable grid, missing coverage without a default, missing expected hillslope keys, unavailable soils directory, and writer-lock contention. These must precede worker submission. No-map prep remains optional and must not consume an earlier generated map.

Staging protects prior artifacts from failures before publication. Publication currently replaces the map and then its hash-bearing summary; these are two operations, not a transaction. Failed second replacement must raise, and readers must verify the map hash before interpreting a summary as current. Fault-injection evidence and this reader requirement remain part of the review follow-up.

## Valid-state matrix

| Stored/filesystem state | Valid? | Required behavior | Evidence reviewed |
| --- | --- | --- | --- |
| No configured map | Yes | Preserve scalar/no-override behavior and ignore derived artifacts | `test_no_map_ignores_stale_artifacts_and_bad_scalar`; source inspection of both callers |
| Configured source absent/corrupt | No | Hard I/O failure; no new soil worker inputs | `test_bad_map_and_missing_keys_fail` covers corrupt source; native missing-file fixture |
| Eligible key grid empty | Yes | Empty generic result | `test_key_masks_nodata_channels_empty` |
| Populated aligned map | Yes | Means and counts over all eligible cells | Native tiny-raster tests and `test_map_rebuild_default_source_grid_and_diagnostics` |
| Partial/all missing hillslope area | Yes with default | Default only missing cells; retain nodata in raster | `test_partial_and_all_missing`; collaborator tests |
| Prior map/summary present and inputs change | Yes | Recompute source/grid/default-sensitive results | `test_map_rebuild_default_source_grid_and_diagnostics` |
| Archive-only soils | Unsupported by current contract | Fail before publication | `test_archive_only_rejected_mixed_directory_authoritative` |
| Mixed directory/archive soils | Yes | Directory authoritative; archive untouched | Same test with real filesystem artifacts |
| Malformed grid/default | No | Explicit bounded error | Native shape/CRS/affine/band tests; bad-default fixtures |
| Writer lock held | Expected contention | Preserve prior state and submit no workers | Independent security review's real Redis probe; `test_lock_contention_and_failed_validation_leave_previous_pair` |
| Validation fails with prior artifacts present | Expected failure | Preserve both prior files and clean staging | Same regression fixture |
| Publication interrupted between replacements | Exceptional failure | Raise; detect map/summary hash mismatch before treating output as current | Source inspection; second-rename fault injection remains unrun |

Input combinations were reviewed separately: missing/finite/NaN nodata, explicit masks, zero/negative/positive generic values and defaults, channel inclusion/exclusion, empty ignored-key sets, parameter band bounds, complete/missing coverage, and changed source/grid/default. These are representative dimensions, not an exhaustive cross-product.

## User-reachable error policy

| Condition | Classification | Result and justification |
| --- | --- | --- |
| No map configured | Expected optional absence | Return without reading derived map; scalar path preserved |
| Any missing parameter area without default | Expected validation failure | Bounded `ValueError` identifies up to ten affected keys and missing/total counts |
| Nonfinite/nonpositive mapped default | Expected validation failure | `ValueError`; positivity belongs to WEPPpy, while native finite zero/negative defaults remain valid |
| Missing/corrupt source | Exceptional input failure | I/O error; no silent scalar fallback |
| Mismatched/geographic/singular grid | Expected validation failure | Explicit Python error instead of computing invalid area weights |
| Destination nodata collision | Expected validation failure | Must fail before creating output; current validation gaps are COR-02 |
| Soils directory absent | Unsupported runtime state | `FileNotFoundError` under the current directory-only contract |
| Maintenance lock unavailable | Expected contention | Existing runtime-path lock error; retry after the active writer completes |
| Source/grid changes during scan | Exceptional concurrent change | `RuntimeError` requires retry; content hashes checked before publication |

## Findings

| ID | Severity | Surface | Finding | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Generic signed raster mean | Initial scaled Kahan accumulation returns `0.3700743415417188` for `[1e16, 1, -1e16]`, rather than `1/3`. A finite result alone does not establish stable cancellation. | Use a cancellation-stable accumulator, rebuild/install the export, and preserve a real-raster regression plus extreme finite-value tests. | Resolved: scaled Neumaier accumulation; installed export regression passed independently |
| COR-02 | Medium | Generic stacker nodata/dtype/resampling | Validation can silently turn valid data into nodata after destination conversion or resampling. Initial underflow and truncation gaps were reproduced; the first conversion fix still missed GDAL rounding and newly interpolated sentinel values. | Validate representability and actual conversion semantics; reject unsafe finite-sentinel combinations before creating output or validate values against independent warped validity. Keep omitted-kwargs behavior compatible. | Resolved: Float64/NaN staging, independent validity and GDAL output conversion checked before output creation; explicit and inherited sentinel regressions passed independently |
| COR-03 | Medium | Ordinary/MOFE soil propagation and failure ordering | Initial new tests stopped at the shared collaborator. Existing MOFE orchestration tests used no map; full local integration exercises MOFE only. No direct mapped ordinary soil-worker propagation evidence existed. | Add both-mode orchestration tests, actual worker soil-file propagation including developed exemptions and all OFEs, and missing-default rejection before any worker submission. | Resolved: both orchestrator fixtures and four actual worker/developed/OFE combinations passed independently |

### Confirmed runtime reproductions

All following probes ran with `wctl run-python -`, real GeoTIFFs, and the installed native release. Rasters used EPSG:32610 and a common `from_origin(500000, 5000000, 30, 30)` grid unless specified otherwise. No raster reader, warp, or native reducer was mocked.

1. COR-01: three cells with key 11 and values `[1e16, 1, -1e16]`. Native mean was `0.3700743415417188`; independent `math.fsum(values) / 3` was `0.3333333333333333`.
2. COR-02 initial: valid source `[0, 2]`, explicit `dst_nodata=1e-300`, `dst_dtype='float32'`. Output declared nodata `0.0`, values `[[0.0, 2.0]]`, masks `[[0, 255]]`. A valid zero disappeared because the sentinel underflowed.
3. COR-02 initial: valid source `[0.1, 2]`, explicit `dst_nodata=0`, `dst_dtype='int16'`. Output values `[[0, 2]]`, masks `[[0, 255]]`.
4. COR-02 after the first source fix: valid source `[0.6, 2]`, explicit `dst_nodata=1`, `dst_dtype='int16'`. NumPy's pre-check truncates `0.6`, but GDAL rounds it to 1. Output values `[[1, 2]]`, masks `[[0, 255]]`.
5. COR-02 after the first source fix: valid source `[-1, 1]`, reference grid one 60-by-30-meter cell, `resample='average'`, `dst_nodata=0`, `dst_dtype='float64'`. The valid average zero becomes output nodata: values `[[0.0]]`, masks `[[0]]`.

The kslast caller uses Float64 NaN during warp and positive conductivity after normalization, so COR-01/02 primarily affected the newly promised generic surface. The fixes cover these reproduced failures without importing soil positivity into the native API.

### Independent revalidation

- `wctl run-python -m pytest /workdir/wepppyo3/tests/raster_characteristics/test_area_weighted_mean.py -q`: **25 passed**, including cancellation and extreme finite values, in the restarted runtime. One pytest cache-write warning for `/workdir/.pytest_cache`; assertions completed successfully.
- `wctl run-pytest tests/nodb/test_kslast_map.py -q`: initial recheck **24 passed, 4 failed**. All map, stacker, containment, lock, and orchestration assertions passed. The four newly added worker fixtures incorrectly set `nsol=2`; the soil writer reads `ntemp`, so the fixture serialized only one OFE. This was a fixture error, not evidence of a production OFE-loss regression.
- After correcting the fixture, `wctl run-pytest tests/nodb/test_kslast_map.py::test_real_soil_workers_propagate_mean_to_every_ofe -q`: **4 passed**. These call actual ordinary/MOFE workers, serialize/read actual two-OFE soil files, and exercise ordinary/developed soils. Together with the separately passing orchestrator fixtures, they close COR-03. Two dependency deprecation warnings were emitted.
- `wctl doc-lint --path docs/work-packages/20260909_kslast_area_weighted/artifacts/20260909_correctness_review.md`: **1 file validated, 0 errors, 0 warnings** at the initial artifact checkpoint.

## Review checks and residual coverage

- [x] Canonical user intent and domain/native ownership are named.
- [x] Absent, empty, populated, supported legacy, and malformed states are distinguished.
- [x] State dimensions are reviewed separately from input combinations.
- [x] Direct unmocked probes exercise the new native and warp boundaries.
- [x] Real contention and pre-publication failure preserve prior artifacts; second-rename fault injection is explicitly unrun.
- [x] Both prep modes have direct generated-soil propagation evidence.
- [x] Pre-publication failure cleanup and source/grid/default retries have been exercised; interrupted two-file publication remains a stated limit.
- [x] Error policy preserves optional no-map absence and explicit coverage failures.
- [x] No claim of exhaustive combination coverage is made.

Other unproven dimensions include equivalent CRS encodings, all individual affine-coefficient mismatch cases, a valid non-first parameter band, and sidecar mask/projection identity during concurrent input changes. These are residual coverage limits, not all independently confirmed defects. The implementation checks all six affine coefficients and does not zip mismatched grids. The full-model evidence missing at initial review is now closed below.

## Final integration disposition

**Pass.** Reviewed [final job tree](integration-jobs.json), [final output verification](integration-verification.json), [release manifest](release_manifest.json), [restart identities](restart.json), and the executable verification logic in [integration runner](run_seductive_sabra_integration.py).

- The normal `run_wepp_rq` parent `90431b48-4138-4f28-89f6-90a5b3806f7e` and all 14 recorded descendants finished. The tree includes MOFE/climate/remaining preparation, hillslope execution, watershed preparation/execution, interchange, water balance, return-period analysis, GeoPackage export, and `_log_complete_rq`. The final job ended at **2026-09-09 23:56:19.621385 UTC**. No failed-job exception is present.
- The verifier calls the full-tree poll before accepting outputs. Its independent `math.fsum` oracle compares every eligible project-cell mean and coverage count without calling the native reducer, then checks actual serialized restrictive-layer values in every generated OFE. Final evidence records **505 hillslopes and 1259 OFEs**, with aggregation relative/absolute tolerances `1e-12` and soil tolerance `1e-12`.
- The configured source/grid identities match the baseline; map metadata matches the actual project grid, and the summary binds the saved map SHA256. The model remains `wepp_260430`, with the original **46-year** simulation. No shortened or no-prep run substitutes for this evidence.
- All **25** discovered interchange Parquet tables were newer than submission, parsed in batches, and checked for finite non-null floating fields. The evidence includes row counts and content hashes. This real run had no missing-area default cases or developed exemptions; those policies are covered by the synthetic native/collaborator and actual worker fixtures above.
- The installed native SHA256 is `587bb3371c282296291f233d6674d4bcad65f950d966f7cd71c0162cdb279b54`. The reviewer independently matched the current library and native source hashes to the manifest. Fresh web, rq-engine, default-worker, and batch-worker entries use the canonical mounted py312 release path, matching hash, and UID/GID 1000/993. Their container IDs changed, and their recorded start times precede the new job submission.
- An additional independent read-only `wctl run-python -` probe fetched all 15 jobs from live Redis and confirmed finished status with no exceptions, checked that summary keys equal the current watershed's **505** expected hillslope keys, verified the actual map hash, and matched the actual `loss_pw0.hill.parquet` hash to final evidence. It did not resubmit or alter the run.

The fresh full-model/install integration requirement is satisfied. Final [validation](validation.md) and the retained `/tmp/kslast-area-weighted-20260909/full-pytest.log` record `wctl run-pytest tests --maxfail=1`: **8174 passed, 72 skipped, 3110 warnings in 900.45 seconds**. The reviewer inspected the final log summary. The owner's separate QA disposition is recorded in the same validation artifact. Remote-push/tip verification remains a publication receipt to be appended by the package owner; it is not a correctness blocker.

## Verdict

- Code correctness findings: **pass**, all three medium findings resolved and independently rechecked.
- Final install/full-model integration: **pass**, completed artifact review and independent live-job/hash cross-check.
- Package correctness/release validation gate: **pass**; required broad-suite and owner QA evidence are recorded. Repository push/tip receipts remain the owner's publication step.
- Unresolved findings: High 0; Medium 0; Low 0.
- Release recommendation: **ship**; complete the authorized repository pushes and record matching remote tips.
- Reviewer sign-off: independent correctness review, 2026-09-09; corrective implementation, actual generated-soil tests, final installed identities, and the completed full model workflow are verified within the explicit evidence limits above.
