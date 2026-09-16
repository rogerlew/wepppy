# M1 fine-earth Kf source and runtime amendment

Status: accepted 2026-09-16 after independent correctness and security reviews;
implementation conformance pending. ADR-0068 records rationale and evidence.
This amendment supersedes new-production M1 POLARIS/RUSLE requirements only
after its contract checkpoint. Legacy v1/v2 and offline callers retain their
existing contracts. M3 science and standalone RUSLE remain unchanged.

## Science and source identity

New production M1 uses only USGS release 10.5066/P13WAPYV (2025-02-11), item
6750c172d34ed8d3858534d8, field KFFACT from the NRCS-derived 1995 USSOILS archive.
The fixed HTTPS source is
`https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/6750c172d34ed8d3858534d8/statsgo-KFFACT.tif`.
Policy identifier: `statsgo_kffact_1995_cog2025_v1`. No fallback is supported.

The product already aggregates all recorded soil layers using thickness weights,
then map-unit components using component percentages. Missing layers/components
are excluded from their respective denominators; entirely missing map units
have value -0.1. Do not redo aggregation using current survey records or impose
surface-depth, organic-material or M3 soil-thickness restrictions.

Use `USLE_customary` units with multiplier 1. The 2025 metadata incorrectly
labels the quantity hydraulic conductivity in inches/hour. The original archive
separates KFFACT erodibility from PERM permeability, and independent raster/polygon
comparison confirms the COG contains KFFACT. Record
`units_interpretation: original_kffact_field_verified`; retain publisher metadata
without rewriting it. No conductivity or SI conversion applies to Kf.
This interpretation is supported locally; no publisher correction is claimed.

Native support is the published 30 m EPSG:5069 raster; underlying survey detail
remains coarse STATSGO map units. Nearest-neighbor alignment onto the existing
project grid preserves categorical map-unit values. Do not use bilinear
interpolation, re-delineation, smoothing, gap fill or scalar calibration.
Masked/NaN and -0.1 samples are unavailable; other negative values, infinity,
or values above the existing M1 [0,1] admission range fail explicitly. Mean S
uses float64 accumulation over common-valid M1 support. T/F/S all use that same
support under `common_valid_v1`; zero support retains `zero_valid_support`.
Coverage reports missing cells without an invented minimum-coverage threshold.

“USGS-compatible” means the fine-earth input identity and documented source
aggregation. It does not mean identical historical delineation, slope, burn
severity, raster sampling, calibration or probabilities.

## Preparation, network and artifacts

Use the normal Run M1 action and existing queue/process supervision. Missing
Kf is preparable optional state and must not disable Run when upstream required
inputs are ready. Run prepares Kf before composing predictors. State/preflight,
report and download reads perform no network acquisition or preparation.
No new queue, service, dependency, shared soil cache, or upstream rebuild.

Reuse the M3 bounded transport design, adding only the fixed KFFACT endpoint:
120-second total deadline, 30-second request deadline, 96 MiB aggregate response
budget, identity encoding, no redirects/retries, strong ETag and length pinning,
conditional ranges and final identity verification. Limit native/target windows
to 10 million cells and retain existing local raster/JSON limits. Failed transport
and native callback errors cannot produce accepted partial inputs. Explicitly
parameterizing the internal fixed-source selection must preserve THICK behavior.
Do not accept user-provided URLs, paths, SQL, or source selectors.

All records live in visible
`postfire_debris_flow/attempts/<id>/kf/`: `requests/` contains start/completion
records and received bodies, `publisher_metadata.xml` retains the approved
metadata snapshot, `native_kf.tif` retains the bounded original window,
`kf.tif` is aligned input, and `manifest.json` marks successful preparation.
Partial/failed attempts retain their files and explicit diagnostics. Normal
browse/archive/restore includes all these records; credentials are excluded.
No mutable project-wide Kf pointer is required. Each new M1 attempt owns its
preparation; accepted attempts remain immutable. This avoids another NoDb
promotion/cache contract at the cost of bounded acquisition on each new run.

`kf/manifest.json` schema 1 contains `status: complete`, `policy`, `source_id`
(the USGS item), `source_url`, `release_date`, `field: KFFACT`, `units`,
`units_interpretation`, `aggregation`, `resampling: nearest`, `retrieved_at`,
`object_identity` (ETag/length/last-modified), `native_grid`, `target_grid`,
`source_metadata_sha256`, `artifacts_sha256` for the native and aligned rasters,
and valid/missing counts. Record the source recipe as provenance, not executable
metadata. Hash every retained request record/body in the preparation inventory.
Bind target grid and protected project-input snapshot to the model attempt.

## Predictor, acceptance and freshness compatibility

New production M1 predictor manifests use schema 3, `model: M1`, existing
common-support fields, and `soil_policy: statsgo_kffact_1995_cog2025_v1`.
Replace the POLARIS-only `k_provenance` with `kf_provenance` containing the exact
preparation-manifest snapshot and hash. Include `kf/kf.tif` and `kf/manifest.json`
in the immutable predictor artifact inventory (copy from attempt preparation).
Keep the saved validity mask and existing WBT artifacts. Reader validation checks
actual common-mask Kf mean against S and provenance/grid/hashes, not just schema.
Result manifests accept schema-3 predictors additively; parquet schema 1, column
meanings and probability units remain unchanged. M3 keeps schema 2.

Retain explicit old/new dispatch based on accepted schema/source policy.
Legacy v1/v2 M1 uses recorded POLARIS readiness and fingerprints; v3 uses Kf
policy, prepared artifacts and actual M1 terrain/SBS/dNBR/rainfall dependencies.
A change to unrelated RUSLE, POLARIS or WEPP Soils cannot stale new M1 results.
A change to Kf artifacts, relevant inputs or selected source policy must stale
or invalidate them. Never relabel old manifests as Kf or bless old identities
as new. Unknown/mismatched policy/schema is explicit unsupported input.
No network probe is needed to establish saved-result currentness: the accepted
object identity remains its recorded source snapshot, not a claim about the
latest object on the server. A new Run obtains a new identity.

Before acceptance and inside the existing short lock, recheck original project
inputs, attempt ownership, eligibility, read-only status, artifact identities
and selected model/rainfall policy. Changed inputs reject the new acceptance;
failed preparation/publication preserves the previous accepted pointer and
bundle. Run artifacts propagate schema/source provenance into event/design/inverse
publication and report downloads; old artifacts remain byte-preserved.

## UI, feature registry and queue obligations

Retain the feature's preview maturity, WBT/CONUS eligibility, user role,
`disturbed` feature prerequisite, existing control position and report link.
Remove automatic POLARIS/RUSLE enabling for postfire; no longer require those
features for M1. Do not disable or delete already enabled standalone features.
M3 retains its current Soils, SBS, Climate and terrain prerequisites.

M1 source readiness displays “Kf will be prepared when you run M1” when absent,
and the recorded source when available. Expected absence is not corruption.
Malformed/hostile files fail explicitly with recovery guidance to run a new
attempt; do not silently overwrite or reuse them. Network failure explains that
Kf preparation failed and permits retry while preserving previous results.
Remove RUSLE completion/dependency edges and producer invalidations only for
new M1; update dependency catalog and validate actual job trees if wiring changes.

## Required conformance

Test absent/empty/prepared/partial/malformed/hostile state; changed source during
range reads and publication; missing/changed protected inputs; legacy bundles;
failed replacement; archive/restore; and reads without optional NoDb state.
Unmocked transport, filesystem containment, publication and archive boundaries
are required. Demonstrate new M1 without RUSLE artifacts/jobs and show RUSLE
changes do not stale it. Validate two distinct basins through generic preparation.
After prerequisite checks restart forest using its installed canonical workflow,
then rerun nervous-mesquite through normal UI/RQ. Retain prior acceptance,
protected-input before/after hashes, independently calculated probabilities,
report/curve/export/reload evidence, and correctness/security/UX dispositions.

### Concrete interfaces and advisory projection

`kf_source.acquire_kf(dem, mask, output_dir)` reserves a fresh caller-owned
attempt directory, supervises native source reading with the existing process
watchdog, aligns locally, verifies protected input hashes and returns the
prepared manifest. It writes no NoDb state. `M1Inputs` gains an optional
`soil_policy` defaulting to legacy POLARIS behavior; production M1 explicitly
selects `statsgo_kffact_1995_cog2025_v1`. Only the common-valid backend accepts
this Kf policy. Existing local callers retain their default behavior.

The accepted NoDb result records `soil_policy` additively. Advisory preflight
stores `postfire_debris_flow:soil_policy` from acceptance with model/revision.
Absent policy means legacy M1 and retains its POLARIS/RUSLE timestamp checks;
the explicit Kf policy omits those two upstream tasks. Unknown policy cannot
claim completion. M3 retains its prior task rules. This Redis projection is
advisory; detailed local artifact freshness remains authoritative. No report
read writes or reconciles the projection.

Regression acceptance must remove RUSLE from Mods while postfire is enabled:
the postfire checkbox, controller and report link remain immediately visible
and remain so after one reload and a second reload. Also test the reverse
operation: enabling postfire does not auto-enable RUSLE/POLARIS. Do not infer
success solely from a second reload recovering a transient hidden controller.
