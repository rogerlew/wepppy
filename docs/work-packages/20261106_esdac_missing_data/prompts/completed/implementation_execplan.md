# Build ESDAC soils from sufficient physical data


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective throughout execution.

## Purpose / Big Picture


A user with valid physical soil data must be able to build a WEPP soil despite missing descriptive labels. Demonstrate this by rebuilding all 35 rejected coordinates from `preservative-coercion` and measuring actual build availability at 1,000 or more spatially distributed ESDAC locations. This is a wired production-code correction, with generated-output acceptance; deployment is separate.

## Progress


- [x] 2026-11-06 UTC: Confirmed all incident failures arise from blank FAO labels in the actual raster attribute table; retained original report.
- [x] 2026-11-06 UTC: Scaffolded package and selected this active plan.
- [x] 2026-11-06 UTC: Recorded source contract and ADR-0139 before implementation.
- [x] 2026-11-06 UTC: Corrected metadata admission and component normalization; preserved legacy raster-table consumer; added source, serializer and retry regression matrix.
- [x] 2026-11-06 18:21 UTC: Final incident replay, paired 1,000-location study, numerical parity and independent artifact verification passed.
- [x] 2026-11-06 18:24 UTC: 123 distinct focused tests, 99 native matrix tests, independent review and durable documentation completed.
- [x] 2026-11-06 UTC: Broad partitions and continuation complete: 13,289 distinct passed, 424 skipped, one proven pre-existing template failure; local package closed with explicit gate disposition.

## Surprises & Discoveries


The current validator treats `fao90lev1`, `dgh`, `dimp`, and `dr` as mandatory even though they do not drive physical calculations. `usedom` already has a warning for code 0, but absent/malformed data also trigger an error before that warning. The local rq-worker container has the ESDAC rasters even though the host path is absent.

## Decision Log


2026-11-06, operator/Codex: missing descriptive metadata is degraded, not rejected. Physical sufficiency remains the acceptance condition. Preserve populated-input numerical behavior and existing landuse defaults. Measure availability with at least 1,000 deterministic locations; report denominator and exclusions rather than implying universal coverage.

## Outcomes & Retrospective


Final candidate builds 733/1,000 sampled locations versus 446 previously:
287 recovered, zero regressions, all 446 prior successes numerically identical.
Seventy-six newly usable profiles emit one material to the known mapped soil
boundary. Incident replay accepts all 35 hillslopes, two unique base soils and
35 disturbed artifacts; retries preserve bytes. The actual-data study was
essential: metadata repair alone exposed batch identity and unused-subsoil
assumptions that fixture-only validation would not have closed. Independent
review passes. Broad partitions and continuation passed 13,289 distinct tests
with 424 skipped and one pre-existing Runs-template assertion failure, reproduced
in isolation against unchanged HEAD files. The broad gate is not fully green;
ESDAC code and artifact acceptance are complete. No production deployment or
original-run mutation occurred.

## Context and Orientation


`wepppy/eu/soils/esdac/esdac.py` samples categorical ESDB rasters, continuous STU rasters and HydroGrids conductivity, derives horizons, and writes WEPP `.sol` files. `quality.py` classifies valid, degraded (usable with warnings), and rejected profiles. `wepppy/eu/soils/soil_build.py` builds locations in staging directories and publishes only an accepted batch with `soil_quality.json`. `esdac/downstream.py` validates disturbed transformations. TopoAZ IDs identify hillslopes. FAO is a soil-group name, STU supplies numerical soil properties, and CEC is cation exchange capacity. Existing unit source fixtures and integration tests live in `tests/eu/soils/`. The original incident report is in this package's artifacts directory.

## Plan of Work


Milestone 1 defines the field policy in `docs/schemas/esdac-soil-source-contract.md` and ADR-0139, with raw-data preservation and compatibility rules. Audit every categorical consumer before deciding optional status.

Milestone 2 modifies source validation and the actual builder so absent, empty and malformed optional fields are observable and safe to serialize. Required depth classes, CEC and physical inputs for emitted materials, output water contents, depth order and conductivity remain validated. Bound top material by the existing mapped impermeable depth; omit nonexistent subsoil and diagnose that decision. Add matrix tests proving valid populated inputs retain physical rows, missing metadata builds, and physical defects still fail. Exercise downstream parsing and batch warnings.

Milestone 3 uses installed rasters in the development worker. Reuse `tools/eu_invalid_soil_search.py` sampling rather than adding dependencies. Retain a seeded coordinate manifest, build every sampled location (not only suspicious ones), parse generated files and record outcomes/reasons and spatial strata. Build all 35 incident coordinates separately and test actual batch output. Bound concurrency to avoid disrupting other work. Retain candidate source hashes and runtime identity. Availability is a sampled data-coverage measurement, not a universal geographic guarantee.

Milestone 4 runs focused tests, broad regression and documentation checks. An independent correctness reviewer checks the field policy, valid-state matrix, generated artifacts and failure-class coverage. Resolve medium/high findings. Update tracker/package/root board with exact status, separating local code delivery from deployment and production recovery.

## Concrete Steps


From `/home/workdir/wepppy`, use `wctl run-pytest tests/eu/soils tests/nodb/mods/disturbed/test_esdac_runtime_gate.py`, then `wctl run-pytest tests --maxfail=1`. Use `wctl exec rq-worker python ...` for the actual-data study. Run `wctl doc-lint --path <changed-document>`, `python3 tools/check_adr_dates.py`, and changed broad-exception checks. Record exact study commands and artifacts as implemented.

## Validation and Acceptance


Missing metadata must produce usable parsed files with warning diagnostics. Existing valid fixture physical content must remain equal. Missing required numerical information must remain rejected with clear field-qualified reasons. The incident set must build or expose a separately evidenced physical insufficiency, which must be investigated before closure. The 1,000-location manifest must have a result for every location, including failures. Report acceptance proportions for the declared sampling frame and reasons for unavailable locations. Directly parse base and downstream soil artifacts; no mocked writer can satisfy this gate.

## Idempotence and Recovery


Use isolated output directories per study run/location and retain original production artifacts. No branch change, deployment, or production mutation is included. Do not overwrite accepted study evidence; version reruns. Batch publication rollback behavior remains intact. Revert code if previously accepted profiles regress; retain reports for diagnosis.

## Artifacts and Notes


Original production report: `artifacts/incident_soil_quality.json`, 35 rejected, zero accepted, each `source.categorical.empty` on `fao90lev1` with raw value `["24", "", "No information"]`. First location is longitude 6.878030223381789, latitude 47.943332184393924.

## Interfaces and Dependencies


Keep `ESDAC.build_wepp_soil` and `build_esdac_soils` signatures and report schema intact. Reuse installed raster interpolation and `WeppSoilUtil`; add no dependency. Canonical policy belongs outside this package. Reviewers must not treat previous tests that enforced metadata rejection as behavioral authority.

Revision: 2026-11-06 UTC, initial plan includes operator-requested large availability study.

Revision: 2026-11-06 UTC, actual incident replay exposed timestamp-only and distinct-content legacy key collisions. Added deterministic content suffixes, equivalent-artifact retry, synchronized quality identities, and valid/degraded historical-file compatibility. Partial metadata must preserve an available forest class. Final direct-study provenance is bound to its consumed source modules separately from batch replay provenance.

Revision: 2026-11-06 UTC, the complete first availability checkpoint exposed
72 depth-order rejections with sufficient mapped top-material depth. Extend
milestone 2 to bound top material by the existing impermeable depth, omit the
nonexistent subsoil interval and condition subsoil CEC/STU requirements on actual
consumption. Keep historical fixtures immutable and update current expectations;
add shallow/equal/deeper, missing-subsoil-provider, invalid-top and disturbed
readback tests. Rerun the paired availability study on the identical manifest.
The initial broad run was interrupted at 532 passed/28 skipped because the
candidate changed. Final broad coverage is split into the 99-test native
disturbed matrix and the remaining tests, both using the final source.

Completion: 2026-11-06 UTC. Final evidence and baseline failure disposition are in
`artifacts/validation.md`; code-delivery scope is complete. Deployment and original-run
recovery remain separate operational follow-ups.
