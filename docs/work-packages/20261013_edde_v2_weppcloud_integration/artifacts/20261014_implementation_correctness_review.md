# EDDE integration implementation correctness review

**Current disposition: correctness review passes for runtime commit `d2ca5821b`; broad-suite gate remains ongoing.** Independent reviewer initially examined the uncommitted candidate over reader-floor checkpoint `85f6ae9f8` on 2026-10-14 UTC and subsequently re-reviewed fixes and actual acceptance receipts. Runtime files were not edited by this reviewer. Earlier findings and intermediate coverage limits are retained below; the final disposition supersedes their open status.

## Initial findings

1. **Medium — clear active EDDE provenance across mode changes.** The initial candidate assigned `_edde_provenance` only at successful EDDE publication. EDDE → successful non-EDDE build → select EDDE again could display the older EDDE provenance over the non-EDDE CLI, including after a failed rebuild. Affected boundaries are `ClimateInputParsingService._parse_core_inputs`, `Climate.climate_mode`, `_apply_climate_selection_pair` in `wepppy/weppcloud/routes/nodb_api/climate_bp.py`, and the EDDE report guard. **Code disposition:** the implementer has added clearing and rollback coverage fields at all three mutation boundaries during this review. **Evidence pending:** successful switching, failed parser rollback, reselection, failed rebuild, durable reload and unchanged retained attempt evidence.

2. **Medium — report the published auxiliary station.** `wepppy/weppcloud/templates/reports/climate.htm` says EDDE auxiliary fields were generated from “the selected CLIGEN station below,” while `report_climate` supplies current `climate.climatestation_meta`. Changing station after a successful build, or failing a rebuild after changing it, produces incorrect source attribution. Use the published station in `edde_provenance['station']` for published-output claims; distinguish pending selection when both are shown. Require a station-change/failed-rebuild report regression.

3. **Medium — retain and establish the PRISM normal period and units.** `wepppy/nodb/core/climate_edde_build.py:_normals` validates shape, masks, finite/order/precipitation bounds and retains raster hashes, but writes no period and only labels the units. Its comment that shared rasters imply matching periods is insufficient for the three separately acquired products. Establish the period and units from the owned service's authoritative product metadata/contract, retain that identity with each raster, and validate agreement. Do not invent a period or silently accept a differently parameterized endpoint. Existing all-point spatial checks are appropriate; the gap is source interpretation/provenance.

4. **Medium — failed attempts lose the reason and early location context.** `run_edde_build` writes only generic `state=failed` in its final status. Eligibility failure happens before `eligibility.json` exists, leaving no requested coordinates or native-cell failure reason in the retained attempt. Inventory/data/normal failures likewise lose their category and message when transient RQ error state expires. Persist captured request locations before acquisition and preserve the originating exception category/message in the attempt while propagating the failure. Verify ineligible-cell, missing-record, transport and invalid-normal outcomes remain distinguishable after archive/restore.

5. **Medium — controller discovery still describes EDDE as observed climate.** In `wepppy/microservices/rq_engine/schema_defaults_routes.py`, `_controller_defaults` recognizes future mode 3 only; mode 17 receives observed 1990–2020 defaults. `_controller_schema` omits `edde_projection`, and collected runtime state omits its saved selection/year values. The build-operation schema adds the projection field, but controller discovery/current-state reload remains inconsistent. Expose the required EDDE field and actual saved future values, preserving explicit unselected state without introducing projection/year defaults. Test both fresh unselected and saved EDDE states.

6. **Medium — bind query grids to preflight eligibility.** `run_edde_build` uses preflight `grid_record`/`cells` for all-location eligibility and final provenance, then each annual `EddeClient.query` independently fetches its grid. No comparison binds the returned query grid/cell to the preflight generation. `normalize_daily` compares yearly locations with each other, not with preflight. A changed static grid between preflight and the first query can therefore publish a different watershed cell while claiming hillslope eligibility against the old grid. Compare grid identity and watershed selection before accepting each annual result; fail explicitly on change. Test a query manifest whose grid/cell differs from the preflight record.

## Boundaries that appear sound in source review

- Source selection stays within enumerated model/scenario/period combinations, with local AnnualMonthlies rejection and strict integer-year parsing.
- Acquisition uses private yearly caches, annual footprint preflight, real client validation and retained object attempt metadata rather than a shared mutable mirror.
- The builder uses the existing native daily PRISM/scaling functions. Shape/mask/finite/temperature-order checks precede native PRISM revision, and final selected CLI dates and values are checked after scaling.
- Scaling completes inside the stage and the router skips duplicate scaling for EDDE. Finalization hydrates durable climate state, compares captured settings/geometry and scale-map identity, and applies a bounded derived-field set within the existing publication rollback primitive.
- New EDDE attempts are retained across router cleanup; existing generated formats and normal WEPP climate preparation remain the consumer boundary.

## Missing evidence and remaining gates

The initial test module exercises real replay/native publication and reload using fixture source acquisition, plus scaling/supersession/replace failures and input validation. It does not alone prove actual remote eligibility, Canadian geometry, Multiple PRISM, controller discovery, report switching, archive/download, authenticated live worker execution or fresh WEPP acceptance. Those are active implementation gates, not a failure of the accepted scientific policy.

Retain targeted coverage for blank and explicit consumed CLIGEN seed arguments; real PRISM-normal coverage gaps and negative/zero/masked inputs; supported scaling modes and final active hashes; changed seed/projection/geometry/scale-map inputs; mode switching and published station attribution; current/old capability identities; and both completed and failed browser/archive payloads. Update the additive mode/properties in `wepppy/nodb/core/climate.pyi` and run the appropriate stub checks.

No final correctness approval, environment-validation claim, full-suite result or deployment approval is made by this preliminary review. Re-review the final candidate and actual acceptance receipts after the findings and outstanding gates are dispositioned.

## Candidate re-review: original findings resolved

Re-reviewed current runtime source and retained receipts on 2026-10-14 UTC. The original six medium findings are resolved in code:

| Finding | Resolution |
| --- | --- |
| 1. Active provenance | Parser, facade setter and paired catalog/mode route clear active EDDE attribution when switching away; parser/route snapshots include rollback. The focused regression checks durable clearing and retained attempts. |
| 2. Published station | The report takes station metadata from the published EDDE provenance before rendering its station description and source attribution. |
| 3. Normal identity | Acquisition `.meta` records must identify the requested `prism/ppt`, `prism/tmin` and `prism/tmax` products. The manifest records hashes, original metadata, normal values and the authoritative 1991–2020 millimeter/Celsius product interpretation. Original provider XMLs under `prism-source-metadata/` establish that interpretation, and the canonical contract explicitly discloses that Wmesque does not provide a period field in every response. This is acceptable product-contract validation, not a claim of per-response period discovery. |
| 4. Failure context | Attempt status now records requested locations/station/seed before acquisition and retains exception type/message while propagating the error. |
| 5. Controller discovery | Runtime state and EDDE defaults now retain actual projection/future fields, including unselected values; controller schema exposes the projection. Older mode defaults remain unchanged. |
| 6. Grid consistency | Each query manifest is retained and its grid source/hash and watershed cell must equal preflight identities before that year's values are accepted. |

Also reviewed numeric `climate_mode=17` parsing: an omitted catalog now requires resolving `future_edde_v2` through the saved capability authority before accepting the selection. This closes the ordinary parser's raw-mode bypass of older stored graph choices. The public stub contains the additive mode and properties.

## Remaining concrete finding

**Medium — EDDE validation errors lose actionable input information.** `artifacts/hostile-http-no-mutation.json` demonstrates that invalid projection, a 2024 start and AnnualMonthlies return only “Invalid climate field values.” The 2100 response uses the older CMIP5 2006–2099 envelope. `wepppy/microservices/rq_engine/climate_routes.py:_build_climate_validation_errors` discards the EDDE validator's useful message; generic future-year mapping does not represent Nor's 2079 limit. Preserve the existing response envelope while mapping EDDE projection, period and incompatible-scaling failures to their actual corrective action. Test missing/invalid projection, years below 2025, Nor years above 2079 and AnnualMonthlies without changing older-mode responses. This finding was sent to the implementer during re-review.

## Evidence checked and remaining acceptance limits

Read the acceptance scripts and parsed the retained receipts rather than inferring completion from job status:

- `artifact-readback.json`: Canadian Single has 53 prepared CLI hashes and 53 parsed WEPP water-balance outputs, each covering 366 days in 2060 with precipitation matching the consumed CLI. US Multiple PRISM has 83 prepared climate hashes; its receipt has zero parsed WEPP consumers while source-project soil setup is being completed.
- `browser-readback.json`: actual project/control and report requests return 200 for Canadian and US projects, with the saved projection visible. This does not alone establish exact downloaded payload bytes.
- `hostile-http-no-mutation.json`: five invalid/hostile submissions return 400 and preserve climate-state/CLI bytes; an unauthenticated submission returns 401. This supports mutation containment but exposes the remaining error-message finding.
- `reader-floor-reopen.json` and its script: eight US/Canada ordinary/single-input and representation cases reopen using the committed reader-floor graph class/catalog with unchanged stored configuration bytes. Current runtime dependencies remain in the harness; the receipt establishes the registered graph read boundary, not a full rolled-back deployment.
- `ca-archive-job.json` shows a finished canonical archive job. Content readback/restore still needs its own byte/mode receipt; archive job success is not that proof.

The full Python suite, fresh US WEPP consumption, completed/failed archive and download readback, negative live eligibility disposition and final candidate/identity receipt remain open at this review checkpoint. The implementer's active acceptance work may subsequently close them. No code finding is raised merely because those runs are still in progress, and this review does not mark them passed prematurely. Targeted changed-grid and published-station report regressions would directly protect the source fixes; record their actual coverage when available.

## Final correctness disposition for `d2ca5821b`

**Pass: no open medium/high correctness findings.** Reviewed the committed runtime candidate and updated receipts on 2026-10-14 UTC. The remaining actionable-error finding is resolved: `EddeSelectionError` carries a safe field/message and the RQ boundary maps it to `invalid_edde_selection` within the existing error envelope before generic CMIP5 handling. The regression covers missing projection, MPI's 2025 lower bound, Nor's 2079 upper bound and AnnualMonthlies. Updated live hostile-request receipts show the actual EDDE range/scaling messages, HTTP 400 and unchanged durable climate/CLI bytes.

The candidate also includes direct regressions proving that a changed query-grid identity rejects before replay and preserves prior publication, and that the report uses the published station instead of a pending selection. The six original source findings remain resolved.

Updated acceptance evidence closes the earlier specific consumer/artifact gaps:

- `artifact-readback.json` now records **53 Canadian Single and 83 US Multiple PRISM** prepared climates with corresponding fresh WEPP water-balance consumers. Every consumer contains 366 finite daily records for 2060, and its precipitation matches its exact prepared CLI. Soil setup is complete for both projects; earlier failed US preparation attempts remain recorded.
- Twelve `browser-download-hashes.json` receipts return HTTP 200 and match local SHA-256/byte counts for published CLI/provenance, completed and failed attempt status, and canonical archive downloads.
- `archive-before-restore.json` and `archive-after-restore.json` are equal. The validation script checks every archived climate member against project bytes and all directory modes for both the successful Canadian project and its PRISM-rejected clone, including the retained failed reason. Finished archive/restore jobs are supported by actual payload verification.
- The Canadian Multiple request fails explicitly because PRISM normals are missing; the previous Single climate remains published, and the failure is browser/download/archive visible. This validates PRISM-negative eligibility without introducing a fallback.
- `runtime-environment.json` identifies the forest development Compose service identities, NFS run mount, bind-mounted source, worker umask, private attempt-directory mode, native extension hash and existing RQ timeout. These are development-environment receipts, not a production deployment claim.

**Residual risks and coverage limits:** the broad repository Python suite was still running at final review; this disposition does not call that gate passing or close the package on its behalf. Live consumer evidence samples MPI SSP3-7.0 for 2060 at the stated US/Canadian projects; broader source/period eligibility relies on the retained feasibility and validation coverage, not an assertion that every combination was live-tested. PRISM period interpretation remains bound to the documented owned product contract rather than an absent per-response period field. Existing public-source availability, interrupted-worker and multi-file publication crash-window risks remain unchanged. No production deployment is approved by this review.
